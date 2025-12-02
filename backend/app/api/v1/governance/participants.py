"""
Participant (Attendance) endpoints for OrgSuite Governance module - v1 API.

This provides the new /api/v1/governance/participants/* endpoints that follow
the same patterns as the membership and finance modules.
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.meeting import Meeting
from app.models.participant import Participant, ParticipantRole, AttendanceStatus
from app.schemas.governance_v1 import (
    ParticipantV1Create, ParticipantV1Update, ParticipantV1Response,
    ParticipantV1ListResponse
)

router = APIRouter()


def participant_to_response(participant: Participant) -> ParticipantV1Response:
    """Convert Participant model to ParticipantV1Response schema."""
    response = ParticipantV1Response(
        id=participant.id,
        meeting_id=participant.meeting_id,
        user_id=participant.user_id,
        role=participant.role.value if isinstance(participant.role, ParticipantRole) else participant.role,
        is_present=participant.is_present,
        attendance_status=participant.attendance_status.value if isinstance(participant.attendance_status, AttendanceStatus) else participant.attendance_status,
        can_vote=participant.can_vote,
        vote_weight=participant.vote_weight,
        joined_at=participant.joined_at,
        left_at=participant.left_at,
        created=participant.created,
        updated=participant.updated,
    )

    # Add expanded user info if available
    if participant.user:
        response.user_name = participant.user.name or participant.user.display_name
        response.user_email = participant.user.email

    return response


async def check_meeting_access(
    meeting_id: str,
    user: User,
    db: AsyncSession,
    require_admin: bool = False
) -> bool:
    """Check if user has access to the meeting."""
    # Get meeting
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()

    if meeting is None:
        return False

    # Creator has full access
    if meeting.created_by_id == user.id:
        return True

    # Check if user is participant
    participant_result = await db.execute(
        select(Participant).where(
            Participant.meeting_id == meeting_id,
            Participant.user_id == user.id
        )
    )
    participant = participant_result.scalar_one_or_none()

    if participant is None:
        return False

    if require_admin:
        return participant.role in [ParticipantRole.ADMIN, ParticipantRole.MODERATOR]

    return True


@router.get("", response_model=ParticipantV1ListResponse)
async def list_participants(
    meeting_id: str = Query(..., description="Meeting ID"),
    page: int = Query(1, ge=1),
    perPage: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List participants for a meeting.
    Requires meeting access.
    """
    # Check access
    if not await check_meeting_access(meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this meeting"
        )

    query = select(Participant).options(selectinload(Participant.user)).where(
        Participant.meeting_id == meeting_id
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and sorting
    query = query.order_by(Participant.created.asc())
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    participants = result.unique().scalars().all()

    items = [participant_to_response(p) for p in participants]

    return ParticipantV1ListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("", response_model=ParticipantV1Response, status_code=status.HTTP_201_CREATED)
async def create_participant(
    participant_data: ParticipantV1Create,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a participant to a meeting.
    Requires meeting admin access.
    """
    # Check meeting exists
    meeting_result = await db.execute(
        select(Meeting).where(Meeting.id == participant_data.meeting_id)
    )
    meeting = meeting_result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Check admin access
    if not await check_meeting_access(participant_data.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add participants to this meeting"
        )

    # Check if user is already a participant
    existing_result = await db.execute(
        select(Participant).where(
            Participant.meeting_id == participant_data.meeting_id,
            Participant.user_id == participant_data.user_id
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a participant"
        )

    # Verify the user exists
    user_result = await db.execute(
        select(User).where(User.id == participant_data.user_id)
    )
    if not user_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Parse role
    try:
        role_enum = ParticipantRole(participant_data.role)
    except ValueError:
        role_enum = ParticipantRole.MEMBER

    # Create participant
    participant = Participant(
        meeting_id=participant_data.meeting_id,
        user_id=participant_data.user_id,
        role=role_enum,
        can_vote=participant_data.can_vote,
        vote_weight=participant_data.vote_weight,
        is_present=False,
        attendance_status=AttendanceStatus.INVITED,
    )

    db.add(participant)
    await db.flush()

    # Reload with user
    await db.refresh(participant)
    result = await db.execute(
        select(Participant)
        .options(selectinload(Participant.user))
        .where(Participant.id == participant.id)
    )
    participant = result.scalar_one()

    return participant_to_response(participant)


@router.get("/{participant_id}", response_model=ParticipantV1Response)
async def get_participant(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get participant by ID.
    Requires meeting access.
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

    # Check access
    if not await check_meeting_access(participant.meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this participant"
        )

    return participant_to_response(participant)


@router.patch("/{participant_id}", response_model=ParticipantV1Response)
async def update_participant(
    participant_id: str,
    participant_data: ParticipantV1Update,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update participant (attendance status, role, etc.).
    Requires meeting admin access or self-update for attendance.
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

    # Check permission - admin can update all, user can update their own attendance
    is_self = participant.user_id == current_user.id
    is_admin = await check_meeting_access(participant.meeting_id, current_user, db, require_admin=True)

    if not is_self and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this participant"
        )

    # Self-update restrictions - can only update attendance, not role
    if is_self and not is_admin:
        if participant_data.role is not None or participant_data.can_vote is not None or participant_data.vote_weight is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update role or voting rights - only attendance"
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
            new_status = AttendanceStatus(participant_data.attendance_status)
            participant.attendance_status = new_status
            # Sync is_present with attendance_status
            participant.is_present = new_status == AttendanceStatus.PRESENT
            if participant.is_present and participant.joined_at is None:
                participant.joined_at = datetime.now(timezone.utc)
        except ValueError:
            pass
    if participant_data.can_vote is not None:
        participant.can_vote = participant_data.can_vote
    if participant_data.vote_weight is not None:
        participant.vote_weight = participant_data.vote_weight

    participant.updated = datetime.now(timezone.utc)
    await db.flush()

    return participant_to_response(participant)


@router.delete("/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_participant(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove participant from meeting.
    Requires meeting admin access.
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

    # Check admin access
    if not await check_meeting_access(participant.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to remove participants"
        )

    await db.delete(participant)
    await db.flush()

    return None


@router.post("/{participant_id}/mark-present", response_model=ParticipantV1Response)
async def mark_present(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark participant as present.
    Allows self-marking or admin marking.
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

    # Check permission - admin or self
    is_self = participant.user_id == current_user.id
    is_admin = await check_meeting_access(participant.meeting_id, current_user, db, require_admin=True)

    if not is_self and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to mark attendance"
        )

    participant.is_present = True
    participant.attendance_status = AttendanceStatus.PRESENT
    if participant.joined_at is None:
        participant.joined_at = datetime.now(timezone.utc)
    participant.updated = datetime.now(timezone.utc)
    await db.flush()

    return participant_to_response(participant)


@router.post("/{participant_id}/mark-absent", response_model=ParticipantV1Response)
async def mark_absent(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark participant as absent.
    Allows self-marking or admin marking.
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

    # Check permission - admin or self
    is_self = participant.user_id == current_user.id
    is_admin = await check_meeting_access(participant.meeting_id, current_user, db, require_admin=True)

    if not is_self and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to mark attendance"
        )

    participant.is_present = False
    participant.attendance_status = AttendanceStatus.ABSENT
    participant.left_at = datetime.now(timezone.utc) if participant.joined_at else None
    participant.updated = datetime.now(timezone.utc)
    await db.flush()

    return participant_to_response(participant)
