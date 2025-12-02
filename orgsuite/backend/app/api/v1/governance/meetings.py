"""
Meeting endpoints for OrgSuite Governance module - v1 API.

This provides the new /api/v1/governance/meetings/* endpoints that follow
the same patterns as the membership and finance modules.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.meeting import Meeting, MeetingStatus, MeetingType
from app.models.participant import Participant, ParticipantRole, AttendanceStatus
from app.models.committee import Committee
from app.schemas.governance_v1 import (
    MeetingV1Create, MeetingV1Update, MeetingV1Response,
    MeetingV1ListResponse
)

router = APIRouter()


def generate_jitsi_room() -> str:
    """Generate a unique Jitsi room name."""
    return f"orgmeet-{uuid.uuid4().hex[:12]}"


def meeting_to_response(meeting: Meeting) -> MeetingV1Response:
    """Convert Meeting model to MeetingV1Response schema."""
    return MeetingV1Response(
        id=meeting.id,
        title=meeting.title,
        description=meeting.description,
        start_time=meeting.start_time,
        end_time=meeting.end_time,
        status=meeting.status.value if isinstance(meeting.status, MeetingStatus) else meeting.status,
        jitsi_room=meeting.jitsi_room,
        settings=meeting.settings,
        created_by_id=meeting.created_by_id,
        committee_id=meeting.committee_id,
        meeting_type=meeting.meeting_type.value if isinstance(meeting.meeting_type, MeetingType) else meeting.meeting_type,
        quorum_required=meeting.quorum_required,
        quorum_met=meeting.quorum_met,
        minutes_generated=meeting.minutes_generated,
        created=meeting.created,
        updated=meeting.updated,
    )


@router.get("", response_model=MeetingV1ListResponse)
async def list_meetings(
    committee_id: Optional[str] = Query(None, description="Filter by committee ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List meetings the user has access to.
    Returns meetings where user is creator or participant.
    """
    # Get meetings user created or is participant of
    participant_subquery = select(Participant.meeting_id).where(
        Participant.user_id == current_user.id
    )

    query = select(Meeting).where(
        or_(
            Meeting.created_by_id == current_user.id,
            Meeting.id.in_(participant_subquery)
        )
    )

    # Apply committee filter
    if committee_id:
        query = query.where(Meeting.committee_id == committee_id)

    # Apply status filter
    if status_filter:
        try:
            status_enum = MeetingStatus(status_filter)
            query = query.where(Meeting.status == status_enum)
        except ValueError:
            pass

    # Apply search filter
    if search:
        query = query.where(
            Meeting.title.ilike(f"%{search}%") |
            Meeting.description.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and sorting
    query = query.order_by(Meeting.start_time.desc())
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    meetings = result.scalars().all()

    items = [meeting_to_response(m) for m in meetings]

    return MeetingV1ListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("", response_model=MeetingV1Response, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    meeting_data: MeetingV1Create,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new meeting.
    The current user becomes the creator and admin participant.
    """
    # Validate required fields
    if not meeting_data.title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title is required"
        )

    # If committee_id provided, verify it exists
    if meeting_data.committee_id:
        committee_result = await db.execute(
            select(Committee).where(Committee.id == meeting_data.committee_id)
        )
        if not committee_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Committee not found"
            )

    # Parse status
    try:
        status_enum = MeetingStatus(meeting_data.status)
    except ValueError:
        status_enum = MeetingStatus.SCHEDULED

    # Parse meeting type
    meeting_type_enum = None
    if meeting_data.meeting_type:
        try:
            meeting_type_enum = MeetingType(meeting_data.meeting_type)
        except ValueError:
            meeting_type_enum = MeetingType.GENERAL

    # Create meeting
    meeting = Meeting(
        title=meeting_data.title,
        description=meeting_data.description,
        start_time=meeting_data.start_time,
        end_time=meeting_data.end_time,
        status=status_enum,
        meeting_type=meeting_type_enum,
        committee_id=meeting_data.committee_id,
        quorum_required=meeting_data.quorum_required or 0,
        settings=meeting_data.settings,
        created_by_id=current_user.id,
        jitsi_room=generate_jitsi_room(),
    )

    db.add(meeting)
    await db.flush()

    # Add creator as admin participant
    participant = Participant(
        meeting_id=meeting.id,
        user_id=current_user.id,
        role=ParticipantRole.ADMIN,
        is_present=False,
        attendance_status=AttendanceStatus.INVITED,
        can_vote=True,
        vote_weight=1,
    )
    db.add(participant)
    await db.flush()

    return meeting_to_response(meeting)


@router.get("/{meeting_id}", response_model=MeetingV1Response)
async def get_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get meeting by ID.
    Requires being creator or participant.
    """
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.created_by))
        .where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Check access - user must be creator or participant
    if meeting.created_by_id != current_user.id:
        participant_result = await db.execute(
            select(Participant).where(
                Participant.meeting_id == meeting_id,
                Participant.user_id == current_user.id
            )
        )
        if not participant_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this meeting"
            )

    return meeting_to_response(meeting)


@router.patch("/{meeting_id}", response_model=MeetingV1Response)
async def update_meeting(
    meeting_id: str,
    meeting_data: MeetingV1Update,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update meeting.
    Requires being creator or admin/moderator participant.
    """
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Check if user is creator or admin participant
    if meeting.created_by_id != current_user.id:
        participant_result = await db.execute(
            select(Participant).where(
                Participant.meeting_id == meeting_id,
                Participant.user_id == current_user.id,
                Participant.role.in_([ParticipantRole.ADMIN, ParticipantRole.MODERATOR])
            )
        )
        if not participant_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this meeting"
            )

    # Update fields
    if meeting_data.title is not None:
        meeting.title = meeting_data.title
    if meeting_data.description is not None:
        meeting.description = meeting_data.description
    if meeting_data.start_time is not None:
        meeting.start_time = meeting_data.start_time
    if meeting_data.end_time is not None:
        meeting.end_time = meeting_data.end_time
    if meeting_data.status is not None:
        try:
            meeting.status = MeetingStatus(meeting_data.status)
        except ValueError:
            pass
    if meeting_data.meeting_type is not None:
        try:
            meeting.meeting_type = MeetingType(meeting_data.meeting_type)
        except ValueError:
            pass
    if meeting_data.quorum_required is not None:
        meeting.quorum_required = meeting_data.quorum_required
    if meeting_data.quorum_met is not None:
        meeting.quorum_met = meeting_data.quorum_met
    if meeting_data.settings is not None:
        meeting.settings = meeting_data.settings

    meeting.updated = datetime.now(timezone.utc)
    await db.flush()

    return meeting_to_response(meeting)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete meeting.
    Only the creator can delete a meeting.
    """
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Only creator can delete
    if meeting.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can delete a meeting"
        )

    await db.delete(meeting)
    await db.flush()

    return None


@router.post("/{meeting_id}/close", response_model=MeetingV1Response)
async def close_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Close a meeting (set status to completed).
    Requires being creator or admin participant.
    """
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Check permission
    if meeting.created_by_id != current_user.id:
        participant_result = await db.execute(
            select(Participant).where(
                Participant.meeting_id == meeting_id,
                Participant.user_id == current_user.id,
                Participant.role == ParticipantRole.ADMIN
            )
        )
        if not participant_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to close this meeting"
            )

    meeting.status = MeetingStatus.COMPLETED
    meeting.end_time = meeting.end_time or datetime.now(timezone.utc)
    meeting.updated = datetime.now(timezone.utc)
    await db.flush()

    return meeting_to_response(meeting)


@router.post("/{meeting_id}/reopen", response_model=MeetingV1Response)
async def reopen_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reopen a completed meeting (set status to in_progress).
    Requires being creator or admin participant.
    """
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Check permission
    if meeting.created_by_id != current_user.id:
        participant_result = await db.execute(
            select(Participant).where(
                Participant.meeting_id == meeting_id,
                Participant.user_id == current_user.id,
                Participant.role == ParticipantRole.ADMIN
            )
        )
        if not participant_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to reopen this meeting"
            )

    if meeting.status != MeetingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed meetings can be reopened"
        )

    meeting.status = MeetingStatus.IN_PROGRESS
    meeting.updated = datetime.now(timezone.utc)
    await db.flush()

    return meeting_to_response(meeting)
