"""
Agenda Item endpoints for OrgSuite Governance module - v1 API.

This provides the new /api/v1/governance/agenda-items/* endpoints that follow
the same patterns as the membership and finance modules.
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
from app.models.participant import Participant, ParticipantRole
from app.models.agenda_item import AgendaItem, AgendaItemType, AgendaItemStatus
from app.schemas.governance_v1 import (
    AgendaItemV1Create, AgendaItemV1Update, AgendaItemV1Response,
    AgendaItemV1ListResponse
)

router = APIRouter()


def agenda_item_to_response(item: AgendaItem) -> AgendaItemV1Response:
    """Convert AgendaItem model to AgendaItemV1Response schema."""
    return AgendaItemV1Response(
        id=item.id,
        meeting_id=item.meeting_id,
        title=item.title,
        description=item.description,
        order=item.order,
        duration_minutes=item.duration_minutes,
        item_type=item.item_type.value if isinstance(item.item_type, AgendaItemType) else item.item_type,
        status=item.status.value if isinstance(item.status, AgendaItemStatus) else item.status,
        created=item.created,
        updated=item.updated,
    )


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


@router.get("", response_model=AgendaItemV1ListResponse)
async def list_agenda_items(
    meeting_id: str = Query(..., description="Meeting ID"),
    page: int = Query(1, ge=1),
    perPage: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List agenda items for a meeting.
    Requires meeting access.
    """
    # Check access
    if not await check_meeting_access(meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this meeting"
        )

    query = select(AgendaItem).where(AgendaItem.meeting_id == meeting_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and sorting (by order)
    query = query.order_by(AgendaItem.order.asc())
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    items = result.scalars().all()

    response_items = [agenda_item_to_response(item) for item in items]

    return AgendaItemV1ListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=response_items
    )


@router.post("", response_model=AgendaItemV1Response, status_code=status.HTTP_201_CREATED)
async def create_agenda_item(
    item_data: AgendaItemV1Create,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create an agenda item.
    Requires meeting admin access.
    """
    # Check meeting exists
    meeting_result = await db.execute(
        select(Meeting).where(Meeting.id == item_data.meeting_id)
    )
    meeting = meeting_result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Check meeting admin access (legacy participant rule)
    if not await check_meeting_access(item_data.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(status_code=403, detail="Not authorized (meeting participant role)")

    # Organization membership enforcement: require member
    org_id = await resolve_meeting_org_id(db, meeting)
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.MEMBER)

    # Parse enums
    try:
        item_type_enum = AgendaItemType(item_data.item_type)
    except ValueError:
        item_type_enum = AgendaItemType.TOPIC

    try:
        status_enum = AgendaItemStatus(item_data.status)
    except ValueError:
        status_enum = AgendaItemStatus.PENDING

    # Get next order number if not provided
    if item_data.order == 0:
        max_order_result = await db.execute(
            select(func.max(AgendaItem.order)).where(
                AgendaItem.meeting_id == item_data.meeting_id
            )
        )
        max_order = max_order_result.scalar() or 0
        order = max_order + 1
    else:
        order = item_data.order

    # Create item
    item = AgendaItem(
        meeting_id=item_data.meeting_id,
        title=item_data.title,
        description=item_data.description,
        order=order,
        duration_minutes=item_data.duration_minutes or 0,
        item_type=item_type_enum,
        status=status_enum,
    )

    db.add(item)
    await db.flush()

    return agenda_item_to_response(item)


@router.get("/{item_id}", response_model=AgendaItemV1Response)
async def get_agenda_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get agenda item by ID.
    Requires meeting access.
    """
    result = await db.execute(
        select(AgendaItem).where(AgendaItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agenda item not found"
        )

    # Check access
    if not await check_meeting_access(item.meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this agenda item"
        )

    return agenda_item_to_response(item)


@router.patch("/{item_id}", response_model=AgendaItemV1Response)
async def update_agenda_item(
    item_id: str,
    item_data: AgendaItemV1Update,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update agenda item.
    Requires meeting admin access.
    """
    result = await db.execute(
        select(AgendaItem).where(AgendaItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agenda item not found"
        )

    # Check meeting admin access
    if not await check_meeting_access(item.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(status_code=403, detail="Not authorized (meeting participant role)")

    # Organization membership enforcement: require member
    org_id = await resolve_meeting_org_id(db, meeting)
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.MEMBER)

    # Update fields
    if item_data.title is not None:
        item.title = item_data.title
    if item_data.description is not None:
        item.description = item_data.description
    if item_data.order is not None:
        item.order = item_data.order
    if item_data.duration_minutes is not None:
        item.duration_minutes = item_data.duration_minutes
    if item_data.item_type is not None:
        try:
            item.item_type = AgendaItemType(item_data.item_type)
        except ValueError:
            pass
    if item_data.status is not None:
        try:
            item.status = AgendaItemStatus(item_data.status)
        except ValueError:
            pass

    item.updated = datetime.now(timezone.utc)
    await db.flush()

    return agenda_item_to_response(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agenda_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete agenda item.
    Requires meeting admin access.
    """
    result = await db.execute(
        select(AgendaItem).where(AgendaItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agenda item not found"
        )

    # Check meeting admin access
    if not await check_meeting_access(item.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(status_code=403, detail="Not authorized (meeting participant role)")

    # Organization membership enforcement: require admin for delete
    org_id_result = await db.execute(select(Meeting).where(Meeting.id == item.meeting_id))
    meeting_parent = org_id_result.scalar_one_or_none()
    org_id = await resolve_meeting_org_id(db, meeting_parent) if meeting_parent else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.ADMIN)

    await db.delete(item)
    await db.flush()

    return None


@router.post("/{item_id}/start", response_model=AgendaItemV1Response)
async def start_agenda_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start an agenda item (set status to in_progress).
    Requires meeting admin access.
    """
    result = await db.execute(
        select(AgendaItem).where(AgendaItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agenda item not found"
        )

    if not await check_meeting_access(item.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(status_code=403, detail="Not authorized (meeting participant role)")
    org_id_result = await db.execute(select(Meeting).where(Meeting.id == item.meeting_id))
    meeting_parent = org_id_result.scalar_one_or_none()
    org_id = await resolve_meeting_org_id(db, meeting_parent) if meeting_parent else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.MEMBER)

    item.status = AgendaItemStatus.IN_PROGRESS
    item.updated = datetime.now(timezone.utc)
    await db.flush()

    return agenda_item_to_response(item)


@router.post("/{item_id}/complete", response_model=AgendaItemV1Response)
async def complete_agenda_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Complete an agenda item (set status to completed).
    Requires meeting admin access.
    """
    result = await db.execute(
        select(AgendaItem).where(AgendaItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agenda item not found"
        )

    if not await check_meeting_access(item.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(status_code=403, detail="Not authorized (meeting participant role)")
    org_id_result = await db.execute(select(Meeting).where(Meeting.id == item.meeting_id))
    meeting_parent = org_id_result.scalar_one_or_none()
    org_id = await resolve_meeting_org_id(db, meeting_parent) if meeting_parent else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.MEMBER)

    item.status = AgendaItemStatus.COMPLETED
    item.updated = datetime.now(timezone.utc)
    await db.flush()

    return agenda_item_to_response(item)


@router.post("/{item_id}/skip", response_model=AgendaItemV1Response)
async def skip_agenda_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Skip an agenda item (set status to skipped).
    Requires meeting admin access.
    """
    result = await db.execute(
        select(AgendaItem).where(AgendaItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agenda item not found"
        )

    if not await check_meeting_access(item.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(status_code=403, detail="Not authorized (meeting participant role)")
    org_id_result = await db.execute(select(Meeting).where(Meeting.id == item.meeting_id))
    meeting_parent = org_id_result.scalar_one_or_none()
    org_id = await resolve_meeting_org_id(db, meeting_parent) if meeting_parent else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.MEMBER)

    item.status = AgendaItemStatus.SKIPPED
    item.updated = datetime.now(timezone.utc)
    await db.flush()

    return agenda_item_to_response(item)
