"""
Motion endpoints - compatible with PocketBase SDK.
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
from app.core.permissions import require_min_role, OrgMembershipRole, resolve_meeting_org_id
from app.models.motion import Motion, MotionWorkflowState
from app.schemas.motion import MotionCreate, MotionUpdate, MotionResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()


def motion_to_response(motion: Motion, expand: Optional[dict] = None) -> MotionResponse:
    """Convert Motion model to MotionResponse schema."""
    return MotionResponse(
        id=motion.id,
        meeting=motion.meeting_id,
        agenda_item=motion.agenda_item_id,
        number=motion.number,
        title=motion.title,
        text=motion.text,
        reason=motion.reason,
        submitter=motion.submitter_id,
        supporters=[s.id for s in motion.supporters] if motion.supporters else [],
        workflow_state=motion.workflow_state.value if isinstance(motion.workflow_state, MotionWorkflowState) else motion.workflow_state,
        category=motion.category,
        vote_result=motion.vote_result,
        final_notes=motion.final_notes,
        attachments=motion.attachments,
        created=motion.created,
        updated=motion.updated,
        expand=expand,
    )


@router.get("/records", response_model=PaginatedResponse[MotionResponse])
async def list_motions(
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    filter: Optional[str] = None,
    sort: Optional[str] = None,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    List motions.
    PocketBase SDK: pb.collection('motions').getList()
    """
    query = select(Motion).options(selectinload(Motion.supporters))

    # Parse simple filters if provided
    if filter:
        if "meeting=" in filter:
            meeting_id = filter.split("meeting=")[1].split("'")[1] if "'" in filter else filter.split("meeting=")[1].split()[0]
            query = query.where(Motion.meeting_id == meeting_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply sorting
    if sort:
        if sort.startswith("-"):
            field_name = sort[1:]
            if hasattr(Motion, field_name):
                query = query.order_by(getattr(Motion, field_name).desc())
        else:
            if hasattr(Motion, sort):
                query = query.order_by(getattr(Motion, sort).asc())
    else:
        query = query.order_by(Motion.created.desc())

    # Apply pagination
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    motions = result.unique().scalars().all()

    # Build response
    items = [motion_to_response(m) for m in motions]

    return PaginatedResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/records", response_model=MotionResponse, status_code=status.HTTP_200_OK)
async def create_motion(
    motion_data: MotionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create motion.
    PocketBase SDK: pb.collection('motions').create()
    """
    # Check meeting exists
    meeting_result = await db.execute(
        select(Meeting).where(Meeting.id == motion_data.meeting)
    )
    meeting = meeting_result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Organization membership: require MEMBER level if org context present
    org_id = await resolve_meeting_org_id(db, meeting) if meeting else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.MEMBER)

    # Generate motion number if not provided
    number = motion_data.number
    if not number:
        count_result = await db.execute(
            select(func.count()).where(Motion.meeting_id == motion_data.meeting)
        )
        count = count_result.scalar() or 0
        number = f"M-{count + 1:03d}"

    # Create motion
    motion = Motion(
        meeting_id=motion_data.meeting,
        agenda_item_id=motion_data.agenda_item,
        number=number,
        title=motion_data.title,
        text=motion_data.text,
        reason=motion_data.reason,
        category=motion_data.category,
        submitter_id=current_user.id,
        workflow_state=MotionWorkflowState.DRAFT,
    )

    db.add(motion)
    await db.flush()

    # Reload with supporters
    await db.refresh(motion)
    motion.supporters = []

    return motion_to_response(motion)


@router.get("/records/{motion_id}", response_model=MotionResponse)
async def get_motion(
    motion_id: str,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get motion by ID.
    PocketBase SDK: pb.collection('motions').getOne()
    """
    result = await db.execute(
        select(Motion)
        .options(selectinload(Motion.supporters))
        .where(Motion.id == motion_id)
    )
    motion = result.scalar_one_or_none()

    if motion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Motion not found"
        )

    return motion_to_response(motion)


@router.patch("/records/{motion_id}", response_model=MotionResponse)
async def update_motion(
    motion_id: str,
    motion_data: MotionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update motion.
    PocketBase SDK: pb.collection('motions').update()
    """
    result = await db.execute(
        select(Motion)
        .options(selectinload(Motion.supporters))
        .where(Motion.id == motion_id)
    )
    motion = result.scalar_one_or_none()

    if motion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Motion not found"
        )

    # Enforce role: require MEMBER if org context
    meeting_result = await db.execute(select(Meeting).where(Meeting.id == motion.meeting_id))
    parent_meeting = meeting_result.scalar_one_or_none()
    org_id = await resolve_meeting_org_id(db, parent_meeting) if parent_meeting else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.MEMBER)

    # Update fields
    if motion_data.title is not None:
        motion.title = motion_data.title
    if motion_data.text is not None:
        motion.text = motion_data.text
    if motion_data.reason is not None:
        motion.reason = motion_data.reason
    if motion_data.category is not None:
        motion.category = motion_data.category
    if motion_data.workflow_state is not None:
        try:
            motion.workflow_state = MotionWorkflowState(motion_data.workflow_state)
        except ValueError:
            pass
    if motion_data.vote_result is not None:
        motion.vote_result = motion_data.vote_result
    if motion_data.final_notes is not None:
        motion.final_notes = motion_data.final_notes

    motion.updated = datetime.now(timezone.utc)
    await db.flush()

    return motion_to_response(motion)


@router.delete("/records/{motion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_motion(
    motion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete motion.
    PocketBase SDK: pb.collection('motions').delete()
    """
    result = await db.execute(select(Motion).where(Motion.id == motion_id))
    motion = result.scalar_one_or_none()

    if motion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Motion not found"
        )

    # Require ADMIN for delete if org context
    meeting_result = await db.execute(select(Meeting).where(Meeting.id == motion.meeting_id))
    parent_meeting = meeting_result.scalar_one_or_none()
    org_id = await resolve_meeting_org_id(db, parent_meeting) if parent_meeting else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.ADMIN)

    await db.delete(motion)
    await db.flush()

    return None
