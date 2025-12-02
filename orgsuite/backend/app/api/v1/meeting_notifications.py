"""Meeting notification endpoints - PocketBase compatible."""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.meeting_notification import MeetingNotification as MNModel, NotificationType, NotificationStatus, DeliveryMethod
from app.models.meeting import Meeting
from app.schemas.meeting_notification import MeetingNotificationCreate, MeetingNotificationUpdate, MeetingNotificationResponse
from app.core.permissions import require_min_role, OrgMembershipRole
from app.schemas.common import PaginatedResponse
from app.models.committee import Committee

router = APIRouter()


def mn_to_response(n: MNModel) -> MeetingNotificationResponse:
    return MeetingNotificationResponse(
        id=n.id,
        meeting=n.meeting_id,
        recipient_user=n.recipient_user_id,
        notification_type=n.notification_type.value if n.notification_type else None,
        status=n.status.value if n.status else NotificationStatus.PENDING.value,
        scheduled_at=n.scheduled_at,
        sent_at=n.sent_at,
        error_message=n.error_message,
        email_subject=n.email_subject,
        email_body=n.email_body,
        include_ics=n.include_ics,
        delivery_method=n.delivery_method.value if n.delivery_method else None,
        notification_metadata=n.notification_metadata,
        created=n.created,
        updated=n.updated,
        expand=None,
    )


@router.get("/records", response_model=PaginatedResponse[MeetingNotificationResponse])
async def list_notifications(page: int = Query(1, ge=1), perPage: int = Query(100, ge=1, le=500), filter: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    query = select(MNModel)
    if filter and "meeting=" in filter:
        meeting_id = filter.split("meeting=")[1].split("\"")[1] if '"' in filter else filter.split("meeting=")[1].split()[0]
        query = query.where(MNModel.meeting_id == meeting_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_items = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(MNModel.created.desc())
    query = query.offset((page - 1) * perPage).limit(perPage)
    result = await db.execute(query)
    items = [mn_to_response(n) for n in result.scalars().all()]
    return PaginatedResponse(page=page, perPage=perPage, totalItems=total_items, totalPages=ceil(total_items / perPage) if total_items else 1, items=items)


@router.post("/records", response_model=MeetingNotificationResponse, status_code=status.HTTP_200_OK)
async def create_notification(data: MeetingNotificationCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    meeting_result = await db.execute(select(Meeting).where(Meeting.id == data.meeting))
    meeting = meeting_result.scalar_one_or_none()
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Member and above can create notifications; viewers excluded
    if meeting.organization_id:
        await require_min_role(db, current_user.id, meeting.organization_id, OrgMembershipRole.MEMBER)
    elif meeting.committee_id:
        committee_result = await db.execute(select(Committee).where(Committee.id == meeting.committee_id))
        committee = committee_result.scalar_one_or_none()
        if committee:
            await require_min_role(db, current_user.id, committee.organization_id, OrgMembershipRole.MEMBER)

    try:
        type_enum = NotificationType(data.notification_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification type")

    status_enum = NotificationStatus.PENDING
    if data.status:
        try:
            status_enum = NotificationStatus(data.status)
        except ValueError:
            pass

    delivery_enum = None
    if data.delivery_method:
        try:
            delivery_enum = DeliveryMethod(data.delivery_method)
        except ValueError:
            delivery_enum = DeliveryMethod.BOTH

    n = MNModel(
        meeting_id=data.meeting,
        recipient_user_id=data.recipient_user,
        notification_type=type_enum,
        status=status_enum,
        scheduled_at=data.scheduled_at or datetime.now(timezone.utc),
        delivery_method=delivery_enum,
        email_subject=data.email_subject,
        email_body=data.email_body,
        include_ics=data.include_ics if data.include_ics is not None else True,
        notification_metadata=data.notification_metadata,
    )
    db.add(n)
    await db.flush()
    return mn_to_response(n)


@router.get("/records/{notification_id}", response_model=MeetingNotificationResponse)
async def get_notification(notification_id: str, db: AsyncSession = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    result = await db.execute(select(MNModel).where(MNModel.id == notification_id))
    n = result.scalar_one_or_none()
    if n is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return mn_to_response(n)


@router.patch("/records/{notification_id}", response_model=MeetingNotificationResponse)
async def update_notification(notification_id: str, data: MeetingNotificationUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(MNModel).where(MNModel.id == notification_id))
    n = result.scalar_one_or_none()
    if n is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    meeting_result = await db.execute(select(Meeting).where(Meeting.id == n.meeting_id))
    meeting = meeting_result.scalar_one_or_none()
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.organization_id:
        await require_min_role(db, current_user.id, meeting.organization_id, OrgMembershipRole.MEMBER)
    elif meeting.committee_id:
        committee_result = await db.execute(select(Committee).where(Committee.id == meeting.committee_id))
        committee = committee_result.scalar_one_or_none()
        if committee:
            await require_min_role(db, current_user.id, committee.organization_id, OrgMembershipRole.MEMBER)

    if data.status is not None:
        try:
            n.status = NotificationStatus(data.status)
        except ValueError:
            pass
    if data.scheduled_at is not None:
        n.scheduled_at = data.scheduled_at
    if data.sent_at is not None:
        n.sent_at = data.sent_at
    if data.error_message is not None:
        n.error_message = data.error_message
    if data.email_subject is not None:
        n.email_subject = data.email_subject
    if data.email_body is not None:
        n.email_body = data.email_body
    if data.include_ics is not None:
        n.include_ics = data.include_ics
    if data.delivery_method is not None:
        try:
            n.delivery_method = DeliveryMethod(data.delivery_method)
        except ValueError:
            pass
    if data.notification_metadata is not None:
        n.notification_metadata = data.notification_metadata

    n.updated = datetime.now(timezone.utc)
    await db.flush()
    return mn_to_response(n)


@router.delete("/records/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(notification_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(MNModel).where(MNModel.id == notification_id))
    n = result.scalar_one_or_none()
    if n is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    meeting_result = await db.execute(select(Meeting).where(Meeting.id == n.meeting_id))
    meeting = meeting_result.scalar_one_or_none()
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    # Admin or owner for delete (if organization context resolvable)
    if meeting.organization_id:
        await require_min_role(db, current_user.id, meeting.organization_id, OrgMembershipRole.ADMIN)
    elif meeting.committee_id:
        committee_result = await db.execute(select(Committee).where(Committee.id == meeting.committee_id))
        committee = committee_result.scalar_one_or_none()
        if committee:
            await require_min_role(db, current_user.id, committee.organization_id, OrgMembershipRole.ADMIN)
    await db.delete(n)
    await db.flush()
    return None
