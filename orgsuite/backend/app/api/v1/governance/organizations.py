"""
Organization endpoints for OrgSuite Governance module - v1 API.

This provides the new /api/v1/organizations/* endpoints that follow
the same patterns as the membership and finance modules.
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.schemas.organization_v1 import (
    OrganizationV1Create, OrganizationV1Update, OrganizationV1Response,
    OrganizationV1ListResponse
)

router = APIRouter()


def org_to_response(org: Organization, membership: Optional[OrgMembership] = None) -> OrganizationV1Response:
    """Convert Organization model to OrganizationV1Response schema."""
    return OrganizationV1Response(
        id=org.id,
        name=org.name,
        description=org.description,
        logo=org.logo,
        settings=org.settings,
        owner_id=org.owner_id,
        created=org.created,
        updated=org.updated,
        user_role=membership.role.value if membership else None,
    )


async def get_user_org_membership(
    org_id: str,
    user: User,
    db: AsyncSession
) -> Optional[OrgMembership]:
    """Get user's membership in an organization."""
    result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.organization_id == org_id,
            OrgMembership.user_id == user.id,
            OrgMembership.is_active == True
        )
    )
    return result.scalar_one_or_none()


async def check_org_access(
    org_id: str,
    user: User,
    db: AsyncSession,
    require_admin: bool = False
) -> bool:
    """Check if user has access to the organization."""
    membership = await get_user_org_membership(org_id, user, db)

    if membership is None:
        # Check if user is owner
        result = await db.execute(
            select(Organization).where(
                Organization.id == org_id,
                Organization.owner_id == user.id
            )
        )
        if result.scalar_one_or_none():
            return True
        return False

    if require_admin:
        return membership.role in [OrgMembershipRole.OWNER, OrgMembershipRole.ADMIN]

    return True


@router.get("", response_model=OrganizationV1ListResponse)
async def list_organizations(
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List organizations the user has access to.
    Returns organizations where user is owner or member.
    """
    # Get orgs where user is member or owner
    member_subquery = select(OrgMembership.organization_id).where(
        OrgMembership.user_id == current_user.id,
        OrgMembership.is_active == True
    )

    query = select(Organization).where(
        or_(
            Organization.owner_id == current_user.id,
            Organization.id.in_(member_subquery)
        )
    )

    # Apply search filter
    if search:
        query = query.where(
            Organization.name.ilike(f"%{search}%") |
            Organization.description.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and sorting
    query = query.order_by(Organization.created.desc())
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    organizations = result.scalars().all()

    # Get memberships for each org to include user_role
    items = []
    for org in organizations:
        membership = await get_user_org_membership(org.id, current_user, db)
        # If no membership but user is owner, create a virtual owner membership
        if not membership and org.owner_id == current_user.id:
            items.append(OrganizationV1Response(
                id=org.id,
                name=org.name,
                description=org.description,
                logo=org.logo,
                settings=org.settings,
                owner_id=org.owner_id,
                created=org.created,
                updated=org.updated,
                user_role="owner",
            ))
        else:
            items.append(org_to_response(org, membership))

    return OrganizationV1ListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("", response_model=OrganizationV1Response, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationV1Create,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new organization.
    The current user becomes the owner.
    """
    # Check if name exists
    result = await db.execute(
        select(Organization).where(Organization.name == org_data.name)
    )
    existing_org = result.scalar_one_or_none()

    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name already exists"
        )

    # Create organization
    org = Organization(
        name=org_data.name,
        description=org_data.description,
        settings=org_data.settings,
        owner_id=current_user.id,
    )

    db.add(org)
    await db.flush()

    # Create owner membership
    membership = OrgMembership(
        organization_id=org.id,
        user_id=current_user.id,
        role=OrgMembershipRole.OWNER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db.add(membership)
    await db.flush()

    return org_to_response(org, membership)


@router.get("/{org_id}", response_model=OrganizationV1Response)
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get organization by ID.
    Requires org membership or ownership.
    """
    result = await db.execute(
        select(Organization)
        .options(selectinload(Organization.owner))
        .where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check access
    if not await check_org_access(org_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    membership = await get_user_org_membership(org_id, current_user, db)

    # Handle owner without explicit membership
    if not membership and org.owner_id == current_user.id:
        return OrganizationV1Response(
            id=org.id,
            name=org.name,
            description=org.description,
            logo=org.logo,
            settings=org.settings,
            owner_id=org.owner_id,
            created=org.created,
            updated=org.updated,
            user_role="owner",
        )

    return org_to_response(org, membership)


@router.patch("/{org_id}", response_model=OrganizationV1Response)
async def update_organization(
    org_id: str,
    org_data: OrganizationV1Update,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update organization.
    Requires org admin/owner access.
    """
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check admin access
    if not await check_org_access(org_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this organization"
        )

    # Update fields
    if org_data.name is not None:
        # Check if new name exists
        if org_data.name != org.name:
            name_result = await db.execute(
                select(Organization).where(Organization.name == org_data.name)
            )
            if name_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization name already exists"
                )
        org.name = org_data.name

    if org_data.description is not None:
        org.description = org_data.description
    if org_data.settings is not None:
        org.settings = org_data.settings
    if org_data.logo is not None:
        org.logo = org_data.logo

    org.updated = datetime.now(timezone.utc)
    await db.flush()

    membership = await get_user_org_membership(org_id, current_user, db)
    return org_to_response(org, membership)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete organization.
    Only the owner can delete an organization.
    """
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Only owner can delete
    if org.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete an organization"
        )

    await db.delete(org)
    await db.flush()

    return None
