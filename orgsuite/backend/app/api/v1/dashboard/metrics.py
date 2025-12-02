"""
Dashboard metrics endpoints for OrgSuite.

Provides CRUD operations for organization metrics and metric values.
"""
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user
from app.core.permissions import get_membership
from app.models.user import User
from app.models.organization import Organization
from app.models.org_membership import OrgMembershipRole
from app.models.metric import Metric, MetricValueType, MetricFrequency
from app.models.metric_value import MetricValue
from app.schemas.metric import (
    MetricCreate, MetricUpdate, MetricResponse, MetricListResponse,
    MetricValueCreate, MetricValueResponse, MetricValueListResponse,
    MetricSetupRequest, MetricSetupResponse, DEFAULT_METRIC_TEMPLATES, MetricTemplate
)

router = APIRouter()


async def require_admin(db: AsyncSession, user_id: str, org_id: str, organization: Organization) -> None:
    """Verify user is admin or owner of the organization."""
    membership = await get_membership(db, user_id, org_id)

    # Allow org owner even without explicit membership record
    if organization.owner_id == user_id:
        return

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    if membership.role not in [OrgMembershipRole.ADMIN, OrgMembershipRole.OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or owner role required"
        )


async def get_org_or_404(db: AsyncSession, org_id: str) -> Organization:
    """Get organization or raise 404."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    return org


def build_metric_response(metric: Metric, limit_history: int = 5) -> MetricResponse:
    """Build MetricResponse from a Metric model with values loaded."""
    latest_val = None
    recent_hist = []

    if metric.values:
        latest_val = MetricValueResponse(
            id=metric.values[0].id,
            metric_id=metric.values[0].metric_id,
            value=metric.values[0].value,
            effective_date=metric.values[0].effective_date,
            notes=metric.values[0].notes,
            created_by_id=metric.values[0].created_by_id,
            created=metric.values[0].created,
            updated=metric.values[0].updated
        )
        recent_hist = [
            MetricValueResponse(
                id=v.id,
                metric_id=v.metric_id,
                value=v.value,
                effective_date=v.effective_date,
                notes=v.notes,
                created_by_id=v.created_by_id,
                created=v.created,
                updated=v.updated
            )
            for v in metric.values[:limit_history]
        ]

    return MetricResponse(
        id=metric.id,
        organization_id=metric.organization_id,
        name=metric.name,
        description=metric.description,
        value_type=metric.value_type,
        frequency=metric.frequency,
        currency=metric.currency,
        is_automatic=metric.is_automatic,
        auto_source=metric.auto_source,
        target_value=metric.target_value,
        sort_order=metric.sort_order,
        is_archived=metric.is_archived,
        created_by_id=metric.created_by_id,
        updated_by_id=metric.updated_by_id,
        created=metric.created,
        updated=metric.updated,
        latest_value=latest_val,
        recent_history=recent_hist
    )


# ============================================================================
# METRIC ENDPOINTS
# ============================================================================

@router.get("/metrics", response_model=MetricListResponse)
async def list_metrics(
    organization_id: str = Query(..., description="Organization ID"),
    include_archived: bool = Query(False, description="Include archived metrics"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all metrics for an organization.

    Returns metrics with their latest values and recent history.
    Requires org membership.
    """
    org = await get_org_or_404(db, organization_id)

    # Check user membership
    membership = await get_membership(db, current_user.id, organization_id)
    if not membership and org.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    # Build query
    query = select(Metric).where(
        Metric.organization_id == organization_id
    ).options(
        selectinload(Metric.values)
    ).order_by(Metric.sort_order, Metric.name)

    if not include_archived:
        query = query.where(Metric.is_archived == False)

    result = await db.execute(query)
    metrics = result.scalars().all()

    # Get total count
    count_query = select(func.count(Metric.id)).where(
        Metric.organization_id == organization_id
    )
    if not include_archived:
        count_query = count_query.where(Metric.is_archived == False)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return MetricListResponse(
        items=[build_metric_response(m) for m in metrics],
        total=total
    )


@router.post("/metrics", response_model=MetricResponse, status_code=status.HTTP_201_CREATED)
async def create_metric(
    data: MetricCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new metric.

    Requires admin or owner role.
    """
    org = await get_org_or_404(db, data.organization_id)
    await require_admin(db, current_user.id, data.organization_id, org)

    # Get next sort order
    max_order_query = select(func.coalesce(func.max(Metric.sort_order), 0)).where(
        Metric.organization_id == data.organization_id
    )
    max_order_result = await db.execute(max_order_query)
    next_order = (max_order_result.scalar() or 0) + 1

    metric = Metric(
        organization_id=data.organization_id,
        name=data.name,
        description=data.description,
        value_type=data.value_type,
        frequency=data.frequency,
        currency=data.currency,
        is_automatic=data.is_automatic,
        auto_source=data.auto_source,
        target_value=data.target_value,
        sort_order=data.sort_order if data.sort_order > 0 else next_order,
        created_by_id=current_user.id,
        updated_by_id=current_user.id
    )

    db.add(metric)
    await db.commit()
    await db.refresh(metric, ["values"])

    return build_metric_response(metric)


@router.get("/metrics/{metric_id}", response_model=MetricResponse)
async def get_metric(
    metric_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single metric by ID."""
    org = await get_org_or_404(db, organization_id)

    # Check user membership
    membership = await get_membership(db, current_user.id, organization_id)
    if not membership and org.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    result = await db.execute(
        select(Metric).where(
            Metric.id == metric_id,
            Metric.organization_id == organization_id
        ).options(selectinload(Metric.values))
    )
    metric = result.scalar_one_or_none()

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found"
        )

    return build_metric_response(metric)


@router.put("/metrics/{metric_id}", response_model=MetricResponse)
async def update_metric(
    metric_id: str,
    data: MetricUpdate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a metric.

    Requires admin or owner role.
    """
    org = await get_org_or_404(db, organization_id)
    await require_admin(db, current_user.id, organization_id, org)

    result = await db.execute(
        select(Metric).where(
            Metric.id == metric_id,
            Metric.organization_id == organization_id
        ).options(selectinload(Metric.values))
    )
    metric = result.scalar_one_or_none()

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found"
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(metric, field, value)
    metric.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(metric, ["values"])

    return build_metric_response(metric)


@router.delete("/metrics/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_metric(
    metric_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a metric and all its values.

    Requires admin or owner role.
    """
    org = await get_org_or_404(db, organization_id)
    await require_admin(db, current_user.id, organization_id, org)

    result = await db.execute(
        select(Metric).where(
            Metric.id == metric_id,
            Metric.organization_id == organization_id
        )
    )
    metric = result.scalar_one_or_none()

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found"
        )

    await db.delete(metric)
    await db.commit()


# ============================================================================
# METRIC VALUE ENDPOINTS
# ============================================================================

@router.get("/metrics/{metric_id}/values", response_model=MetricValueListResponse)
async def list_metric_values(
    metric_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all values for a metric (history)."""
    org = await get_org_or_404(db, organization_id)

    # Check user membership
    membership = await get_membership(db, current_user.id, organization_id)
    if not membership and org.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    # Verify metric exists and belongs to org
    metric_result = await db.execute(
        select(Metric).where(
            Metric.id == metric_id,
            Metric.organization_id == organization_id
        )
    )
    metric = metric_result.scalar_one_or_none()
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found"
        )

    # Get values
    values_result = await db.execute(
        select(MetricValue).where(
            MetricValue.metric_id == metric_id
        ).order_by(MetricValue.effective_date.desc()).limit(limit)
    )
    values = values_result.scalars().all()

    # Get total count
    count_result = await db.execute(
        select(func.count(MetricValue.id)).where(MetricValue.metric_id == metric_id)
    )
    total = count_result.scalar() or 0

    return MetricValueListResponse(
        items=[
            MetricValueResponse(
                id=v.id,
                metric_id=v.metric_id,
                value=v.value,
                effective_date=v.effective_date,
                notes=v.notes,
                created_by_id=v.created_by_id,
                created=v.created,
                updated=v.updated
            )
            for v in values
        ],
        total=total
    )


@router.post("/metrics/{metric_id}/values", response_model=MetricValueResponse, status_code=status.HTTP_201_CREATED)
async def add_metric_value(
    metric_id: str,
    data: MetricValueCreate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a new value to a metric.

    Requires admin or owner role.
    """
    org = await get_org_or_404(db, organization_id)
    await require_admin(db, current_user.id, organization_id, org)

    # Verify metric exists and belongs to org
    metric_result = await db.execute(
        select(Metric).where(
            Metric.id == metric_id,
            Metric.organization_id == organization_id
        )
    )
    metric = metric_result.scalar_one_or_none()
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metric not found"
        )

    value = MetricValue(
        metric_id=metric_id,
        value=data.value,
        effective_date=data.effective_date or date.today(),
        notes=data.notes,
        created_by_id=current_user.id
    )

    db.add(value)
    await db.commit()
    await db.refresh(value)

    return MetricValueResponse(
        id=value.id,
        metric_id=value.metric_id,
        value=value.value,
        effective_date=value.effective_date,
        notes=value.notes,
        created_by_id=value.created_by_id,
        created=value.created,
        updated=value.updated
    )


# ============================================================================
# SETUP / WIZARD ENDPOINTS
# ============================================================================

@router.get("/metrics/templates", response_model=List[MetricTemplate])
async def get_metric_templates(
    current_user: User = Depends(get_current_user)
):
    """Get suggested metric templates for setup wizard."""
    return DEFAULT_METRIC_TEMPLATES


@router.post("/metrics/setup", response_model=MetricSetupResponse)
async def setup_metrics(
    data: MetricSetupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create multiple metrics at once (for setup wizard).

    Requires admin or owner role.
    """
    org = await get_org_or_404(db, data.organization_id)
    await require_admin(db, current_user.id, data.organization_id, org)

    created_metrics = []
    for i, metric_data in enumerate(data.metrics):
        metric = Metric(
            organization_id=data.organization_id,
            name=metric_data.name,
            description=metric_data.description,
            value_type=metric_data.value_type,
            frequency=metric_data.frequency,
            currency=metric_data.currency,
            is_automatic=metric_data.is_automatic,
            auto_source=metric_data.auto_source,
            target_value=metric_data.target_value,
            sort_order=i + 1,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        db.add(metric)
        created_metrics.append(metric)

    await db.commit()

    # Refresh all metrics
    for metric in created_metrics:
        await db.refresh(metric, ["values"])

    return MetricSetupResponse(
        metrics_created=len(created_metrics),
        metrics=[build_metric_response(m) for m in created_metrics]
    )
