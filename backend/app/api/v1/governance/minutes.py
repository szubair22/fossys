"""
Meeting minutes endpoints for OrgSuite Governance module.

Migrated from PocketBase to FastAPI.
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.meeting import Meeting
from app.core.permissions import require_min_role, OrgMembershipRole, resolve_meeting_org_id
from app.models.meeting_minutes import MeetingMinutes, MinutesStatus
from app.models.participant import Participant, ParticipantRole
from app.schemas.meeting_minutes import (
    MeetingMinutesCreate,
    MeetingMinutesUpdate,
    MeetingMinutesResponse,
    MeetingMinutesListResponse,
)

router = APIRouter()


def minutes_to_response(minutes: MeetingMinutes) -> MeetingMinutesResponse:
    """Convert MeetingMinutes model to response schema."""
    return MeetingMinutesResponse(
        id=minutes.id,
        meeting_id=minutes.meeting_id,
        content=minutes.content,
        summary=minutes.summary,
        decisions=minutes.decisions,
        attendance_snapshot=minutes.attendance_snapshot,
        generated_at=minutes.generated_at,
        generated_by_id=minutes.generated_by_id,
        status=minutes.status.value if isinstance(minutes.status, MinutesStatus) else minutes.status,
        approved_by_id=minutes.approved_by_id,
        approved_at=minutes.approved_at,
        created=minutes.created,
        updated=minutes.updated,
    )


async def check_meeting_access(
    meeting_id: str,
    user: User,
    db: AsyncSession,
    require_admin: bool = False
) -> bool:
    """Check if user has access to the meeting."""
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


@router.get("", response_model=MeetingMinutesListResponse)
async def list_minutes(
    meeting_id: Optional[str] = Query(None, description="Filter by meeting ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1),
    perPage: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List meeting minutes.
    If meeting_id is provided, returns minutes for that meeting.
    Otherwise returns minutes for all meetings user has access to.
    """
    # Build query
    query = select(MeetingMinutes)

    if meeting_id:
        # Check meeting access
        if not await check_meeting_access(meeting_id, current_user, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this meeting"
            )
        query = query.where(MeetingMinutes.meeting_id == meeting_id)
    else:
        # Get minutes for meetings user has access to
        # Get meetings where user is creator or participant
        participant_subquery = select(Participant.meeting_id).where(
            Participant.user_id == current_user.id
        )
        creator_subquery = select(Meeting.id).where(
            Meeting.created_by_id == current_user.id
        )
        query = query.where(
            MeetingMinutes.meeting_id.in_(participant_subquery) |
            MeetingMinutes.meeting_id.in_(creator_subquery)
        )

    # Apply status filter
    if status_filter:
        try:
            status_enum = MinutesStatus(status_filter)
            query = query.where(MeetingMinutes.status == status_enum)
        except ValueError:
            pass

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and sorting
    query = query.order_by(MeetingMinutes.created.desc())
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    minutes_list = result.scalars().all()

    items = [minutes_to_response(m) for m in minutes_list]

    return MeetingMinutesListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.get("/by-meeting/{meeting_id}", response_model=MeetingMinutesResponse)
async def get_minutes_by_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get meeting minutes by meeting ID.
    Returns the minutes document for a specific meeting.
    """
    # Check meeting access
    if not await check_meeting_access(meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this meeting"
        )

    result = await db.execute(
        select(MeetingMinutes).where(MeetingMinutes.meeting_id == meeting_id)
    )
    minutes = result.scalar_one_or_none()

    if minutes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Minutes not found for this meeting"
        )

    return minutes_to_response(minutes)


@router.get("/{minutes_id}", response_model=MeetingMinutesResponse)
async def get_minutes(
    minutes_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get meeting minutes by ID.
    """
    result = await db.execute(
        select(MeetingMinutes).where(MeetingMinutes.id == minutes_id)
    )
    minutes = result.scalar_one_or_none()

    if minutes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Minutes not found"
        )

    # Check meeting access
    if not await check_meeting_access(minutes.meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access these minutes"
        )

    return minutes_to_response(minutes)


@router.post("", response_model=MeetingMinutesResponse, status_code=status.HTTP_201_CREATED)
async def create_minutes(
    minutes_data: MeetingMinutesCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create meeting minutes.
    Requires meeting admin access.
    """
    # Check meeting exists
    meeting_result = await db.execute(
        select(Meeting).where(Meeting.id == minutes_data.meeting_id)
    )
    meeting = meeting_result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Legacy participant admin check
    if not await check_meeting_access(minutes_data.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(status_code=403, detail="Not authorized (meeting role)")
    # Organization membership enforcement: require ADMIN
    org_id = await resolve_meeting_org_id(db, meeting)
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.ADMIN)

    # Check if minutes already exist
    existing_result = await db.execute(
        select(MeetingMinutes).where(MeetingMinutes.meeting_id == minutes_data.meeting_id)
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minutes already exist for this meeting. Use PATCH to update."
        )

    # Parse status
    try:
        status_enum = MinutesStatus(minutes_data.status)
    except ValueError:
        status_enum = MinutesStatus.DRAFT

    # Create minutes
    minutes = MeetingMinutes(
        meeting_id=minutes_data.meeting_id,
        content=minutes_data.content,
        summary=minutes_data.summary,
        decisions=minutes_data.decisions,
        attendance_snapshot=minutes_data.attendance_snapshot,
        status=status_enum,
        generated_by_id=current_user.id,
        generated_at=datetime.now(timezone.utc),
    )

    db.add(minutes)
    await db.flush()

    # Update meeting to indicate minutes were generated
    meeting.minutes_generated = True
    await db.flush()

    return minutes_to_response(minutes)


@router.patch("/{minutes_id}", response_model=MeetingMinutesResponse)
async def update_minutes(
    minutes_id: str,
    minutes_data: MeetingMinutesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update meeting minutes.
    Requires meeting admin access.
    """
    result = await db.execute(
        select(MeetingMinutes).where(MeetingMinutes.id == minutes_id)
    )
    minutes = result.scalar_one_or_none()

    if minutes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Minutes not found"
        )

    if not await check_meeting_access(minutes.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(status_code=403, detail="Not authorized (meeting role)")
    org_id_result = await db.execute(select(Meeting).where(Meeting.id == minutes.meeting_id))
    parent_meeting = org_id_result.scalar_one_or_none()
    org_id = await resolve_meeting_org_id(db, parent_meeting) if parent_meeting else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.ADMIN)

    # Update fields
    if minutes_data.content is not None:
        minutes.content = minutes_data.content
    if minutes_data.summary is not None:
        minutes.summary = minutes_data.summary
    if minutes_data.decisions is not None:
        minutes.decisions = minutes_data.decisions
    if minutes_data.attendance_snapshot is not None:
        minutes.attendance_snapshot = minutes_data.attendance_snapshot
    if minutes_data.status is not None:
        try:
            minutes.status = MinutesStatus(minutes_data.status)
        except ValueError:
            pass

    minutes.updated = datetime.now(timezone.utc)
    await db.flush()

    return minutes_to_response(minutes)


@router.post("/{minutes_id}/approve", response_model=MeetingMinutesResponse)
async def approve_minutes(
    minutes_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve meeting minutes.
    Requires meeting admin access.
    """
    result = await db.execute(
        select(MeetingMinutes).where(MeetingMinutes.id == minutes_id)
    )
    minutes = result.scalar_one_or_none()

    if minutes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Minutes not found"
        )

    if not await check_meeting_access(minutes.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(status_code=403, detail="Not authorized (meeting role)")
    org_id_result = await db.execute(select(Meeting).where(Meeting.id == minutes.meeting_id))
    parent_meeting = org_id_result.scalar_one_or_none()
    org_id = await resolve_meeting_org_id(db, parent_meeting) if parent_meeting else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.ADMIN)

    # Minutes must be finalized before approval
    if minutes.status == MinutesStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minutes must be finalized before approval"
        )

    minutes.status = MinutesStatus.APPROVED
    minutes.approved_by_id = current_user.id
    minutes.approved_at = datetime.now(timezone.utc)
    minutes.updated = datetime.now(timezone.utc)
    await db.flush()

    return minutes_to_response(minutes)


@router.post("/{minutes_id}/finalize", response_model=MeetingMinutesResponse)
async def finalize_minutes(
    minutes_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Finalize meeting minutes (change from draft to final).
    Requires meeting admin access.
    """
    result = await db.execute(
        select(MeetingMinutes).where(MeetingMinutes.id == minutes_id)
    )
    minutes = result.scalar_one_or_none()

    if minutes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Minutes not found"
        )

    if not await check_meeting_access(minutes.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(status_code=403, detail="Not authorized (meeting role)")
    org_id_result = await db.execute(select(Meeting).where(Meeting.id == minutes.meeting_id))
    parent_meeting = org_id_result.scalar_one_or_none()
    org_id = await resolve_meeting_org_id(db, parent_meeting) if parent_meeting else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.ADMIN)

    if minutes.status != MinutesStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft minutes can be finalized"
        )

    minutes.status = MinutesStatus.FINAL
    minutes.updated = datetime.now(timezone.utc)
    await db.flush()

    return minutes_to_response(minutes)


@router.delete("/{minutes_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_minutes(
    minutes_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete meeting minutes.
    Requires meeting admin access. Only draft minutes can be deleted.
    """
    result = await db.execute(
        select(MeetingMinutes).where(MeetingMinutes.id == minutes_id)
    )
    minutes = result.scalar_one_or_none()

    if minutes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Minutes not found"
        )

    if not await check_meeting_access(minutes.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(status_code=403, detail="Not authorized (meeting role)")
    org_id_result = await db.execute(select(Meeting).where(Meeting.id == minutes.meeting_id))
    parent_meeting = org_id_result.scalar_one_or_none()
    org_id = await resolve_meeting_org_id(db, parent_meeting) if parent_meeting else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.ADMIN)

    # Only draft minutes can be deleted
    if minutes.status != MinutesStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft minutes can be deleted"
        )

    # Get the meeting to update minutes_generated flag
    meeting_result = await db.execute(
        select(Meeting).where(Meeting.id == minutes.meeting_id)
    )
    meeting = meeting_result.scalar_one_or_none()

    await db.delete(minutes)

    # Update meeting to indicate no minutes
    if meeting:
        meeting.minutes_generated = False

    await db.flush()

    return None


@router.post("/upsert", response_model=MeetingMinutesResponse)
async def upsert_minutes(
    minutes_data: MeetingMinutesCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create or update meeting minutes.
    If minutes exist for the meeting, updates them. Otherwise creates new minutes.
    Requires meeting admin access.
    """
    # Check meeting exists
    meeting_result = await db.execute(
        select(Meeting).where(Meeting.id == minutes_data.meeting_id)
    )
    meeting = meeting_result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    if not await check_meeting_access(minutes_data.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(status_code=403, detail="Not authorized (meeting role)")
    org_id = await resolve_meeting_org_id(db, meeting)
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.ADMIN)

    # Check if minutes already exist
    existing_result = await db.execute(
        select(MeetingMinutes).where(MeetingMinutes.meeting_id == minutes_data.meeting_id)
    )
    existing_minutes = existing_result.scalar_one_or_none()

    if existing_minutes:
        # Update existing
        if minutes_data.content is not None:
            existing_minutes.content = minutes_data.content
        if minutes_data.summary is not None:
            existing_minutes.summary = minutes_data.summary
        if minutes_data.decisions is not None:
            existing_minutes.decisions = minutes_data.decisions
        if minutes_data.attendance_snapshot is not None:
            existing_minutes.attendance_snapshot = minutes_data.attendance_snapshot
        if minutes_data.status:
            try:
                existing_minutes.status = MinutesStatus(minutes_data.status)
            except ValueError:
                pass

        existing_minutes.updated = datetime.now(timezone.utc)
        await db.flush()
        return minutes_to_response(existing_minutes)
    else:
        # Create new
        try:
            status_enum = MinutesStatus(minutes_data.status)
        except ValueError:
            status_enum = MinutesStatus.DRAFT

        minutes = MeetingMinutes(
            meeting_id=minutes_data.meeting_id,
            content=minutes_data.content,
            summary=minutes_data.summary,
            decisions=minutes_data.decisions,
            attendance_snapshot=minutes_data.attendance_snapshot,
            status=status_enum,
            generated_by_id=current_user.id,
            generated_at=datetime.now(timezone.utc),
        )

        db.add(minutes)
        await db.flush()

        # Update meeting to indicate minutes were generated
        meeting.minutes_generated = True
        await db.flush()

        return minutes_to_response(minutes)
