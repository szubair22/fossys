"""
Participant endpoints - compatible with PocketBase SDK.
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.meeting import Meeting
from app.models.participant import Participant, ParticipantRole, AttendanceStatus
from app.schemas.participant import ParticipantCreate, ParticipantUpdate, ParticipantResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()


def participant_to_response(participant: Participant, expand: Optional[dict] = None) -> ParticipantResponse:
    """Convert Participant model to ParticipantResponse schema."""
    return ParticipantResponse(
        id=participant.id,
        meeting=participant.meeting_id,
        user=participant.user_id,
        role=participant.role.value if isinstance(participant.role, ParticipantRole) else participant.role,
        is_present=participant.is_present,
        attendance_status=participant.attendance_status.value if isinstance(participant.attendance_status, AttendanceStatus) else participant.attendance_status,
        can_vote=participant.can_vote,
        vote_weight=participant.vote_weight,
        joined_at=participant.joined_at,
        left_at=participant.left_at,
        created=participant.created,
        updated=participant.updated,
        expand=expand,
    )


@router.get("/records", response_model=PaginatedResponse[ParticipantResponse])
async def list_participants(
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    filter: Optional[str] = None,
    sort: Optional[str] = None,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    List participants.
    PocketBase SDK: pb.collection('participants').getList()
    """
    query = select(Participant).options(selectinload(Participant.user))

    # Parse simple filters if provided
    if filter:
        if "meeting=" in filter:
            meeting_id = filter.split("meeting=")[1].split("'")[1] if "'" in filter else filter.split("meeting=")[1].split()[0]
            query = query.where(Participant.meeting_id == meeting_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply sorting
    if sort:
        if sort.startswith("-"):
            field_name = sort[1:]
            if hasattr(Participant, field_name):
                query = query.order_by(getattr(Participant, field_name).desc())
        else:
            if hasattr(Participant, sort):
                query = query.order_by(getattr(Participant, sort).asc())
    else:
        query = query.order_by(Participant.created.asc())

    # Apply pagination
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    participants = result.unique().scalars().all()

    # Build response with expand if requested
    items = []
    for p in participants:
        expand_data = None
        if expand and "user" in expand and p.user:
            expand_data = {
                "user": {
                    "id": p.user.id,
                    "email": p.user.email,
                    "name": p.user.name,
                }
            }
        items.append(participant_to_response(p, expand=expand_data))

    return PaginatedResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/records", response_model=ParticipantResponse, status_code=status.HTTP_200_OK)
async def create_participant(
    participant_data: ParticipantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a participant to a meeting.
    PocketBase SDK: pb.collection('participants').create()
    """
    # Check meeting exists
    meeting_result = await db.execute(
        select(Meeting).where(Meeting.id == participant_data.meeting)
    )
    meeting = meeting_result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Check if already a participant
    existing_result = await db.execute(
        select(Participant).where(
            Participant.meeting_id == participant_data.meeting,
            Participant.user_id == participant_data.user
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a participant"
        )

    # Parse role
    try:
        role_enum = ParticipantRole(participant_data.role)
    except ValueError:
        role_enum = ParticipantRole.MEMBER

    # Create participant
    participant = Participant(
        meeting_id=participant_data.meeting,
        user_id=participant_data.user,
        role=role_enum,
        can_vote=participant_data.can_vote,
        vote_weight=participant_data.vote_weight,
        is_present=False,
        attendance_status=AttendanceStatus.INVITED,
    )

    db.add(participant)
    await db.flush()

    return participant_to_response(participant)


@router.get("/records/{participant_id}", response_model=ParticipantResponse)
async def get_participant(
    participant_id: str,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get participant by ID.
    PocketBase SDK: pb.collection('participants').getOne()
    """
    result = await db.execute(
        select(Participant)
        .options(selectinload(Participant.user))
        .where(Participant.id == participant_id)
    )
    participant = result.scalar_one_or_none()

    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    expand_data = None
    if expand and "user" in expand and participant.user:
        expand_data = {
            "user": {
                "id": participant.user.id,
                "email": participant.user.email,
                "name": participant.user.name,
            }
        }

    return participant_to_response(participant, expand=expand_data)


@router.patch("/records/{participant_id}", response_model=ParticipantResponse)
async def update_participant(
    participant_id: str,
    participant_data: ParticipantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update participant.
    PocketBase SDK: pb.collection('participants').update()
    """
    result = await db.execute(
        select(Participant).where(Participant.id == participant_id)
    )
    participant = result.scalar_one_or_none()

    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    # Update fields
    if participant_data.role is not None:
        try:
            participant.role = ParticipantRole(participant_data.role)
        except ValueError:
            pass
    if participant_data.is_present is not None:
        participant.is_present = participant_data.is_present
        if participant_data.is_present and participant.joined_at is None:
            participant.joined_at = datetime.now(timezone.utc)
    if participant_data.attendance_status is not None:
        try:
            participant.attendance_status = AttendanceStatus(participant_data.attendance_status)
        except ValueError:
            pass
    if participant_data.can_vote is not None:
        participant.can_vote = participant_data.can_vote
    if participant_data.vote_weight is not None:
        participant.vote_weight = participant_data.vote_weight

    participant.updated = datetime.now(timezone.utc)
    await db.flush()

    return participant_to_response(participant)


@router.delete("/records/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_participant(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove participant from meeting.
    PocketBase SDK: pb.collection('participants').delete()
    """
    result = await db.execute(
        select(Participant).where(Participant.id == participant_id)
    )
    participant = result.scalar_one_or_none()

    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    await db.delete(participant)
    await db.flush()

    return None
