"""Recording endpoints - PocketBase compatible."""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.recording import Recording as RecordingModel, RecordingProvider, RecordingStatus, RecordingVisibility
from app.schemas.recording import RecordingCreate, RecordingUpdate, RecordingResponse
from app.core.permissions import require_min_role, OrgMembershipRole
from app.schemas.common import PaginatedResponse
from app.models.meeting import Meeting
from app.models.committee import Committee

router = APIRouter()


def recording_to_response(r: RecordingModel) -> RecordingResponse:
    return RecordingResponse(
        id=r.id,
        meeting=r.meeting_id,
        title=r.title,
        description=r.description,
        provider=r.provider.value if r.provider else None,
        url=r.url,
        file=r.file,
        thumbnail=r.thumbnail,
        recording_date=r.recording_date,
        duration_seconds=r.duration_seconds,
        file_size=r.file_size,
        status=r.status.value if r.status else RecordingStatus.READY.value,
        visibility=r.visibility.value if r.visibility else None,
        created_by=r.created_by_id,
        created=r.created,
        updated=r.updated,
        expand=None,
    )


@router.get("/records", response_model=PaginatedResponse[RecordingResponse])
async def list_recordings(
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    filter: Optional[str] = None,
    sort: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    query = select(RecordingModel)
    if filter and "meeting=" in filter:
        meeting_id = filter.split("meeting=")[1].split("\"")[1] if '"' in filter else filter.split("meeting=")[1].split()[0]
        query = query.where(RecordingModel.meeting_id == meeting_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_items = (await db.execute(count_query)).scalar() or 0

    if sort:
        if sort.startswith("-"):
            field = sort[1:]
            if hasattr(RecordingModel, field):
                query = query.order_by(getattr(RecordingModel, field).desc())
        else:
            if hasattr(RecordingModel, sort):
                query = query.order_by(getattr(RecordingModel, sort).asc())
    else:
        query = query.order_by(RecordingModel.created.desc())

    query = query.offset((page - 1) * perPage).limit(perPage)
    result = await db.execute(query)
    recs = result.scalars().all()
    items = [recording_to_response(r) for r in recs]
    return PaginatedResponse(page=page, perPage=perPage, totalItems=total_items, totalPages=ceil(total_items / perPage) if total_items else 1, items=items)


@router.post("/records", response_model=RecordingResponse, status_code=status.HTTP_200_OK)
async def create_recording(
    data: RecordingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meeting_result = await db.execute(select(Meeting).where(Meeting.id == data.meeting))
    meeting = meeting_result.scalar_one_or_none()
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Role enforcement: member or higher can create recordings (exclude viewers)
    if meeting.organization_id:
        await require_min_role(db, current_user.id, meeting.organization_id, OrgMembershipRole.MEMBER)
    elif meeting.committee_id:
        committee_result = await db.execute(select(Committee).where(Committee.id == meeting.committee_id))
        committee = committee_result.scalar_one_or_none()
        if committee:
            await require_min_role(db, current_user.id, committee.organization_id, OrgMembershipRole.MEMBER)

    provider_enum = None
    if data.provider:
        try:
            provider_enum = RecordingProvider(data.provider)
        except ValueError:
            provider_enum = RecordingProvider.OTHER

    visibility_enum = None
    if data.visibility:
        try:
            visibility_enum = RecordingVisibility(data.visibility)
        except ValueError:
            visibility_enum = RecordingVisibility.MEMBERS

    rec = RecordingModel(
        meeting_id=data.meeting,
        title=data.title,
        description=data.description,
        provider=provider_enum or RecordingProvider.LOCAL,
        url=data.url,
        visibility=visibility_enum,
        status=RecordingStatus.READY,
        created_by_id=current_user.id,
    )
    db.add(rec)
    await db.flush()
    return recording_to_response(rec)


@router.get("/records/{recording_id}", response_model=RecordingResponse)
async def get_recording(recording_id: str, db: AsyncSession = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    result = await db.execute(select(RecordingModel).where(RecordingModel.id == recording_id))
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording_to_response(rec)


@router.patch("/records/{recording_id}", response_model=RecordingResponse)
async def update_recording(recording_id: str, data: RecordingUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(RecordingModel).where(RecordingModel.id == recording_id))
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recording not found")

    meeting_result = await db.execute(select(Meeting).where(Meeting.id == rec.meeting_id))
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

    if data.title is not None:
        rec.title = data.title
    if data.description is not None:
        rec.description = data.description
    if data.provider is not None:
        try:
            rec.provider = RecordingProvider(data.provider)
        except ValueError:
            pass
    if data.url is not None:
        rec.url = data.url
    if data.visibility is not None:
        try:
            rec.visibility = RecordingVisibility(data.visibility)
        except ValueError:
            pass
    if data.status is not None:
        try:
            rec.status = RecordingStatus(data.status)
        except ValueError:
            pass

    rec.updated = datetime.now(timezone.utc)
    await db.flush()
    return recording_to_response(rec)


@router.delete("/records/{recording_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recording(recording_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(RecordingModel).where(RecordingModel.id == recording_id))
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    meeting_result = await db.execute(select(Meeting).where(Meeting.id == rec.meeting_id))
    meeting = meeting_result.scalar_one_or_none()
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    # Require admin or owner to delete (if organization context resolvable)
    if meeting.organization_id:
        await require_min_role(db, current_user.id, meeting.organization_id, OrgMembershipRole.ADMIN)
    elif meeting.committee_id:
        committee_result = await db.execute(select(Committee).where(Committee.id == meeting.committee_id))
        committee = committee_result.scalar_one_or_none()
        if committee:
            await require_min_role(db, current_user.id, committee.organization_id, OrgMembershipRole.ADMIN)
    await db.delete(rec)
    await db.flush()
    return None
