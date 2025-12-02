"""
Committee endpoints for OrgSuite Governance module - v1 API.

This provides the new /api/v1/governance/committees/* endpoints that follow
the same patterns as the membership and finance modules.
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.committee import Committee
from app.models.organization import Organization
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.schemas.governance_v1 import (
    CommitteeV1Create, CommitteeV1Update, CommitteeV1Response,
    CommitteeV1ListResponse
)

router = APIRouter()


def committee_to_response(committee: Committee) -> CommitteeV1Response:
    """Convert Committee model to CommitteeV1Response schema."""
    return CommitteeV1Response(
        id=committee.id,
        organization_id=committee.organization_id,
        name=committee.name,
        description=committee.description,
        admin_ids=[admin.id for admin in committee.admins] if committee.admins else [],
        created=committee.created,
        updated=committee.updated,
    )


async def check_org_access(
    org_id: str,
    user: User,
    db: AsyncSession,
    require_admin: bool = False
) -> bool:
    """Check if user has access to the organization."""
    # Check if user is owner
    result = await db.execute(
        select(Organization).where(
            Organization.id == org_id,
            Organization.owner_id == user.id
        )
    )
    if result.scalar_one_or_none():
        return True

    # Check membership
    result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.organization_id == org_id,
            OrgMembership.user_id == user.id,
            OrgMembership.is_active == True
        )
    )
    membership = result.scalar_one_or_none()

    if membership is None:
        return False

    if require_admin:
        return membership.role in [OrgMembershipRole.OWNER, OrgMembershipRole.ADMIN]

    return True


@router.get("", response_model=CommitteeV1ListResponse)
async def list_committees(
    organization_id: str = Query(..., description="Organization ID"),
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List committees for an organization.
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    query = select(Committee).options(selectinload(Committee.admins)).where(
        Committee.organization_id == organization_id
    )

    # Apply search filter
    if search:
        query = query.where(
            Committee.name.ilike(f"%{search}%") |
            Committee.description.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and sorting
    query = query.order_by(Committee.name.asc())
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    committees = result.unique().scalars().all()

    items = [committee_to_response(c) for c in committees]

    return CommitteeV1ListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("", response_model=CommitteeV1Response, status_code=status.HTTP_201_CREATED)
async def create_committee(
    committee_data: CommitteeV1Create,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new committee.
    Requires org admin access.
    """
    # Check organization exists
    org_result = await db.execute(
        select(Organization).where(Organization.id == committee_data.organization_id)
    )
    org = org_result.scalar_one_or_none()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check admin access
    if not await check_org_access(committee_data.organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create committees in this organization"
        )

    # Create committee
    committee = Committee(
        organization_id=committee_data.organization_id,
        name=committee_data.name,
        description=committee_data.description,
    )
    committee.admins = [current_user]

    db.add(committee)
    await db.flush()

    return committee_to_response(committee)


@router.get("/{committee_id}", response_model=CommitteeV1Response)
async def get_committee(
    committee_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get committee by ID.
    Requires org membership.
    """
    result = await db.execute(
        select(Committee)
        .options(selectinload(Committee.admins))
        .where(Committee.id == committee_id)
    )
    committee = result.scalar_one_or_none()

    if committee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Committee not found"
        )

    # Check access
    if not await check_org_access(committee.organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this committee"
        )

    return committee_to_response(committee)


@router.patch("/{committee_id}", response_model=CommitteeV1Response)
async def update_committee(
    committee_id: str,
    committee_data: CommitteeV1Update,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update committee.
    Requires committee admin or org admin access.
    """
    result = await db.execute(
        select(Committee)
        .options(selectinload(Committee.admins))
        .where(Committee.id == committee_id)
    )
    committee = result.scalar_one_or_none()

    if committee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Committee not found"
        )

    # Check permission - must be committee admin or org owner/admin
    is_committee_admin = any(admin.id == current_user.id for admin in committee.admins)

    if not is_committee_admin:
        if not await check_org_access(committee.organization_id, current_user, db, require_admin=True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this committee"
            )

    # Update fields
    if committee_data.name is not None:
        committee.name = committee_data.name
    if committee_data.description is not None:
        committee.description = committee_data.description

    committee.updated = datetime.now(timezone.utc)
    await db.flush()

    return committee_to_response(committee)


@router.delete("/{committee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_committee(
    committee_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete committee.
    Requires org admin access.
    """
    result = await db.execute(
        select(Committee)
        .options(selectinload(Committee.admins))
        .where(Committee.id == committee_id)
    )
    committee = result.scalar_one_or_none()

    if committee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Committee not found"
        )

    # Check org admin access
    if not await check_org_access(committee.organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this committee"
        )

    await db.delete(committee)
    await db.flush()

    return None
