"""
Meeting endpoints - compatible with PocketBase SDK.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.core.config import settings
from app.models.user import User
from app.models.meeting import Meeting, MeetingStatus, MeetingType
from app.models.committee import Committee
from app.core.permissions import require_min_role, OrgMembershipRole, resolve_meeting_org_id
from app.models.participant import Participant, ParticipantRole, AttendanceStatus
from app.models.org_membership import OrgMembership
from app.schemas.meeting import (
    MeetingCreate, MeetingUpdate, MeetingResponse, MeetingListResponse
)

router = APIRouter()


def generate_jitsi_room() -> str:
    """Generate a unique Jitsi room name."""
    return f"orgmeet-{uuid.uuid4().hex[:12]}"


def meeting_to_response(meeting: Meeting, expand: Optional[dict] = None) -> MeetingResponse:
    """Convert Meeting model to MeetingResponse schema."""
    return MeetingResponse(
        id=meeting.id,
        title=meeting.title,
        description=meeting.description,
        start_time=meeting.start_time,
        end_time=meeting.end_time,
        status=meeting.status.value if isinstance(meeting.status, MeetingStatus) else meeting.status,
        jitsi_room=meeting.jitsi_room,
        settings=meeting.settings,
        created_by=meeting.created_by_id,
        committee=meeting.committee_id,
        meeting_type=meeting.meeting_type.value if isinstance(meeting.meeting_type, MeetingType) else meeting.meeting_type,
        quorum_required=meeting.quorum_required,
        quorum_met=meeting.quorum_met,
        minutes_generated=meeting.minutes_generated,
        created=meeting.created,
        updated=meeting.updated,
        expand=expand,
    )


@router.get("/records", response_model=MeetingListResponse)
async def list_meetings(
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    filter: Optional[str] = None,
    sort: Optional[str] = None,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    List meetings.
    PocketBase SDK: pb.collection('meetings').getList()
    """
    query = select(Meeting)

    if current_user:
        # Get meetings user created or is participant of
        participant_subquery = select(Participant.meeting_id).where(
            Participant.user_id == current_user.id
        )
        query = query.where(
            or_(
                Meeting.created_by_id == current_user.id,
                Meeting.id.in_(participant_subquery)
            )
        )

    # Parse simple filters if provided
    if filter:
        # Simple status filter: status='scheduled'
        if "status=" in filter:
            status_value = filter.split("status=")[1].split("'")[1] if "'" in filter else filter.split("status=")[1].split()[0]
            try:
                status_enum = MeetingStatus(status_value)
                query = query.where(Meeting.status == status_enum)
            except ValueError:
                pass

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply sorting
    if sort:
        sort_fields = sort.split(",")
        for sort_field in sort_fields:
            if sort_field.startswith("-"):
                field_name = sort_field[1:]
                if hasattr(Meeting, field_name):
                    query = query.order_by(getattr(Meeting, field_name).desc())
            else:
                if hasattr(Meeting, sort_field):
                    query = query.order_by(getattr(Meeting, sort_field).asc())
    else:
        query = query.order_by(Meeting.start_time.desc())

    # Apply pagination
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    meetings = result.scalars().all()

    # Build response
    items = [meeting_to_response(m) for m in meetings]

    return MeetingListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/records", response_model=MeetingResponse, status_code=status.HTTP_200_OK)
async def create_meeting(
    meeting_data: MeetingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new meeting.
    PocketBase SDK: pb.collection('meetings').create()
    """
    # Validate required fields
    if not meeting_data.title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"title": {"message": "Title is required"}}
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
    # Determine organization_id: explicit, or derive from committee
    organization_id = meeting_data.organization
    if not organization_id and meeting_data.committee:
        committee_result = await db.execute(select(Committee).where(Committee.id == meeting_data.committee))
        committee = committee_result.scalar_one_or_none()
        if committee:
            organization_id = committee.organization_id

    meeting = Meeting(
        title=meeting_data.title,
        description=meeting_data.description,
        start_time=meeting_data.start_time,
        end_time=meeting_data.end_time,
        status=status_enum,
        meeting_type=meeting_type_enum,
        committee_id=meeting_data.committee,
        organization_id=organization_id,
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


@router.get("/records/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get meeting by ID.
    PocketBase SDK: pb.collection('meetings').getOne()
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

    # Build expand data if requested
    expand_data = None
    if expand and "created_by" in expand and meeting.created_by:
        expand_data = {
            "created_by": {
                "id": meeting.created_by.id,
                "email": meeting.created_by.email,
                "name": meeting.created_by.name,
            }
        }

    return meeting_to_response(meeting, expand=expand_data)


@router.patch("/records/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: str,
    meeting_data: MeetingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update meeting.
    PocketBase SDK: pb.collection('meetings').update()
    """
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Role enforcement: require member or higher if organization context exists
    if meeting.organization_id:
        try:
            await require_min_role(db, current_user.id, meeting.organization_id, OrgMembershipRole.MEMBER)
        except HTTPException:
            # Fallback to legacy participant/creator rule if membership insufficient
            pass

    # Check if user is creator or admin participant
    participant_result = await db.execute(
        select(Participant).where(
            Participant.meeting_id == meeting_id,
            Participant.user_id == current_user.id,
            Participant.role.in_([ParticipantRole.ADMIN, ParticipantRole.MODERATOR])
        )
    )
    participant = participant_result.scalar_one_or_none()

    if meeting.created_by_id != current_user.id and participant is None:
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


@router.delete("/records/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete meeting.
    PocketBase SDK: pb.collection('meetings').delete()
    """
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Role enforcement: require admin for delete if organization context
    if meeting.organization_id:
        try:
            await require_min_role(db, current_user.id, meeting.organization_id, OrgMembershipRole.ADMIN)
        except HTTPException:
            # Will fallback to creator rule below
            pass

    # Only creator can delete (legacy rule retained)
    if meeting.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can delete a meeting"
        )

    await db.delete(meeting)
    await db.flush()

    return None
