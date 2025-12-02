"""
Activity endpoints for CRM module.

Permissions:
- List/Get: requires 'viewer' role in organization
- Create: requires 'member' role in organization
- Update/Delete: requires creator or 'admin' role
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_min_role, is_admin_or_owner
from app.models.user import User
from app.models.activity import Activity, ActivityType
from app.models.opportunity import Opportunity
from app.models.org_membership import OrgMembershipRole
from app.schemas.crm import (
    ActivityCreate, ActivityUpdate, ActivityResponse, ActivityListResponse
)

router = APIRouter()


async def activity_to_response(activity: Activity, db: AsyncSession) -> ActivityResponse:
    """Convert Activity model to response schema with expanded fields."""
    creator_name = None

    if activity.created_by_user_id:
        result = await db.execute(
            select(User.name).where(User.id == activity.created_by_user_id)
        )
        creator_name = result.scalar_one_or_none()

    return ActivityResponse(
        id=activity.id,
        organization_id=activity.organization_id,
        opportunity_id=activity.opportunity_id,
        contact_id=activity.contact_id,
        type=activity.type.value if isinstance(activity.type, ActivityType) else activity.type,
        subject=activity.subject,
        description=activity.description,
        due_date=activity.due_date,
        completed_at=activity.completed_at,
        created_by_user_id=activity.created_by_user_id,
        created=activity.created,
        updated=activity.updated,
        created_by_name=creator_name,
    )


@router.get("/activities", response_model=ActivityListResponse)
async def list_activities(
    organization_id: str = Query(..., description="Organization ID"),
    opportunity_id: Optional[str] = Query(None, description="Filter by opportunity"),
    type: Optional[str] = Query(None, description="Filter by activity type"),
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List activities for an organization."""
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.VIEWER)

    query = select(Activity).where(Activity.organization_id == organization_id)

    # Apply filters
    if opportunity_id:
        query = query.where(Activity.opportunity_id == opportunity_id)

    if type:
        try:
            type_enum = ActivityType(type)
            query = query.where(Activity.type == type_enum)
        except ValueError:
            pass

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_items = (await db.execute(count_query)).scalar() or 0

    # Order by created desc (most recent first)
    query = query.order_by(Activity.created.desc())

    # Pagination
    query = query.offset((page - 1) * perPage).limit(perPage)
    result = await db.execute(query)
    activities = result.scalars().all()

    items = [await activity_to_response(a, db) for a in activities]
    return ActivityListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    activity_data: ActivityCreate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new activity."""
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.MEMBER)

    # Verify opportunity exists and belongs to this org
    opp_result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == activity_data.opportunity_id,
            Opportunity.organization_id == organization_id
        )
    )
    opportunity = opp_result.scalar_one_or_none()
    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )

    # Validate type
    try:
        type_enum = ActivityType(activity_data.type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid activity type: {activity_data.type}. Valid types: call, email, meeting, note, task"
        )

    activity = Activity(
        organization_id=organization_id,
        opportunity_id=activity_data.opportunity_id,
        contact_id=activity_data.contact_id,
        type=type_enum,
        subject=activity_data.subject,
        description=activity_data.description,
        due_date=activity_data.due_date,
        created_by_user_id=current_user.id,
    )

    db.add(activity)
    await db.flush()
    await db.refresh(activity)

    return await activity_to_response(activity, db)


@router.get("/activities/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get an activity by ID."""
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.VIEWER)

    result = await db.execute(
        select(Activity).where(
            Activity.id == activity_id,
            Activity.organization_id == organization_id
        )
    )
    activity = result.scalar_one_or_none()

    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )

    return await activity_to_response(activity, db)


@router.patch("/activities/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: str,
    activity_data: ActivityUpdate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an activity. Only creator or admin can update."""
    membership = await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.MEMBER)

    result = await db.execute(
        select(Activity).where(
            Activity.id == activity_id,
            Activity.organization_id == organization_id
        )
    )
    activity = result.scalar_one_or_none()

    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )

    # Only creator or admin can update
    if not is_admin_or_owner(membership) and activity.created_by_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update activities you created"
        )

    # Update fields
    if activity_data.contact_id is not None:
        activity.contact_id = activity_data.contact_id or None
    if activity_data.type is not None:
        try:
            activity.type = ActivityType(activity_data.type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid activity type: {activity_data.type}"
            )
    if activity_data.subject is not None:
        activity.subject = activity_data.subject
    if activity_data.description is not None:
        activity.description = activity_data.description
    if activity_data.due_date is not None:
        activity.due_date = activity_data.due_date
    if activity_data.completed_at is not None:
        activity.completed_at = activity_data.completed_at

    activity.updated = datetime.now(timezone.utc)
    await db.flush()

    return await activity_to_response(activity, db)


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(
    activity_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an activity. Only creator or admin can delete."""
    membership = await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.MEMBER)

    result = await db.execute(
        select(Activity).where(
            Activity.id == activity_id,
            Activity.organization_id == organization_id
        )
    )
    activity = result.scalar_one_or_none()

    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )

    # Only creator or admin can delete
    if not is_admin_or_owner(membership) and activity.created_by_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete activities you created"
        )

    await db.delete(activity)
    await db.flush()

    return None


@router.post("/activities/{activity_id}/complete", response_model=ActivityResponse)
async def complete_activity(
    activity_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark an activity (especially tasks) as completed."""
    membership = await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.MEMBER)

    result = await db.execute(
        select(Activity).where(
            Activity.id == activity_id,
            Activity.organization_id == organization_id
        )
    )
    activity = result.scalar_one_or_none()

    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )

    # Only creator or admin can complete
    if not is_admin_or_owner(membership) and activity.created_by_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only complete activities you created"
        )

    activity.completed_at = datetime.now(timezone.utc)
    activity.updated = datetime.now(timezone.utc)
    await db.flush()

    return await activity_to_response(activity, db)
