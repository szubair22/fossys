"""
Agenda item endpoints - compatible with PocketBase SDK.
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.meeting import Meeting
from app.models.agenda_item import AgendaItem, AgendaItemType, AgendaItemStatus
from app.schemas.agenda_item import AgendaItemCreate, AgendaItemUpdate, AgendaItemResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()


def agenda_item_to_response(item: AgendaItem, expand: Optional[dict] = None) -> AgendaItemResponse:
    """Convert AgendaItem model to AgendaItemResponse schema."""
    return AgendaItemResponse(
        id=item.id,
        meeting=item.meeting_id,
        title=item.title,
        description=item.description,
        order=item.order,
        duration_minutes=item.duration_minutes,
        item_type=item.item_type.value if isinstance(item.item_type, AgendaItemType) else item.item_type,
        status=item.status.value if isinstance(item.status, AgendaItemStatus) else item.status,
        created=item.created,
        updated=item.updated,
        expand=expand,
    )


@router.get("/records", response_model=PaginatedResponse[AgendaItemResponse])
async def list_agenda_items(
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    filter: Optional[str] = None,
    sort: Optional[str] = None,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    List agenda items.
    PocketBase SDK: pb.collection('agenda_items').getList()
    """
    query = select(AgendaItem)

    # Parse simple filters if provided
    if filter:
        if "meeting=" in filter:
            meeting_id = filter.split("meeting=")[1].split("'")[1] if "'" in filter else filter.split("meeting=")[1].split()[0]
            query = query.where(AgendaItem.meeting_id == meeting_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply sorting
    if sort:
        if sort.startswith("-"):
            field_name = sort[1:]
            if hasattr(AgendaItem, field_name):
                query = query.order_by(getattr(AgendaItem, field_name).desc())
        else:
            if hasattr(AgendaItem, sort):
                query = query.order_by(getattr(AgendaItem, sort).asc())
    else:
        query = query.order_by(AgendaItem.order.asc())

    # Apply pagination
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    items = result.scalars().all()

    # Build response
    response_items = [agenda_item_to_response(item) for item in items]

    return PaginatedResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=response_items
    )


@router.post("/records", response_model=AgendaItemResponse, status_code=status.HTTP_200_OK)
async def create_agenda_item(
    item_data: AgendaItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create agenda item.
    PocketBase SDK: pb.collection('agenda_items').create()
    """
    # Check meeting exists
    meeting_result = await db.execute(
        select(Meeting).where(Meeting.id == item_data.meeting)
    )
    meeting = meeting_result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

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
                AgendaItem.meeting_id == item_data.meeting
            )
        )
        max_order = max_order_result.scalar() or 0
        order = max_order + 1
    else:
        order = item_data.order

    # Create item
    item = AgendaItem(
        meeting_id=item_data.meeting,
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


@router.get("/records/{item_id}", response_model=AgendaItemResponse)
async def get_agenda_item(
    item_id: str,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get agenda item by ID.
    PocketBase SDK: pb.collection('agenda_items').getOne()
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

    return agenda_item_to_response(item)


@router.patch("/records/{item_id}", response_model=AgendaItemResponse)
async def update_agenda_item(
    item_id: str,
    item_data: AgendaItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update agenda item.
    PocketBase SDK: pb.collection('agenda_items').update()
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


@router.delete("/records/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agenda_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete agenda item.
    PocketBase SDK: pb.collection('agenda_items').delete()
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

    await db.delete(item)
    await db.flush()

    return None
