"""
Organization endpoints - compatible with PocketBase SDK.
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.organization import Organization
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationListResponse, OrgMembershipResponse
)

router = APIRouter()


def org_to_response(org: Organization, expand: Optional[dict] = None) -> OrganizationResponse:
    """Convert Organization model to OrganizationResponse schema."""
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        description=org.description,
        logo=org.logo,
        settings=org.settings,
        owner=org.owner_id,
        created=org.created,
        updated=org.updated,
        expand=expand,
    )


def membership_to_response(membership: OrgMembership, expand: Optional[dict] = None) -> OrgMembershipResponse:
    """Convert OrgMembership model to OrgMembershipResponse schema."""
    return OrgMembershipResponse(
        id=membership.id,
        organization=membership.organization_id,
        user=membership.user_id,
        role=membership.role.value,
        is_active=membership.is_active,
        invited_by=membership.invited_by_id,
        invited_at=membership.invited_at,
        joined_at=membership.joined_at,
        permissions=membership.permissions,
        created=membership.created,
        updated=membership.updated,
        expand=expand,
    )


@router.get("/records", response_model=OrganizationListResponse)
async def list_organizations(
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    filter: Optional[str] = None,
    sort: Optional[str] = None,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    List organizations.
    PocketBase SDK: pb.collection('organizations').getList()
    """
    # Base query - get organizations user is member of, or all if no auth
    query = select(Organization)

    if current_user:
        # Get orgs where user is member or owner
        member_subquery = select(OrgMembership.organization_id).where(
            OrgMembership.user_id == current_user.id,
            OrgMembership.is_active == True
        )
        query = query.where(
            or_(
                Organization.owner_id == current_user.id,
                Organization.id.in_(member_subquery)
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Apply sorting
    if sort:
        if sort.startswith("-"):
            query = query.order_by(getattr(Organization, sort[1:]).desc())
        else:
            query = query.order_by(getattr(Organization, sort).asc())
    else:
        query = query.order_by(Organization.created.desc())

    # Execute query
    result = await db.execute(query)
    organizations = result.scalars().all()

    # Build response
    items = [org_to_response(org) for org in organizations]

    return OrganizationListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/records", response_model=OrganizationResponse, status_code=status.HTTP_200_OK)
async def create_organization(
    org_data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new organization.
    PocketBase SDK: pb.collection('organizations').create()
    """
    # Check if name exists
    result = await db.execute(select(Organization).where(Organization.name == org_data.name))
    existing_org = result.scalar_one_or_none()

    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"name": {"message": "Organization name already exists"}}
        )

    # Create organization
    org = Organization(
        name=org_data.name,
        description=org_data.description,
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

    return org_to_response(org)


@router.get("/records/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get organization by ID.
    PocketBase SDK: pb.collection('organizations').getOne()
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

    # Build expand data if requested
    expand_data = None
    if expand and "owner" in expand and org.owner:
        expand_data = {
            "owner": {
                "id": org.owner.id,
                "email": org.owner.email,
                "name": org.owner.name,
            }
        }

    return org_to_response(org, expand=expand_data)


@router.patch("/records/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    org_data: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update organization.
    PocketBase SDK: pb.collection('organizations').update()
    """
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check if user is owner or admin
    membership_result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.organization_id == org_id,
            OrgMembership.user_id == current_user.id,
            OrgMembership.is_active == True
        )
    )
    membership = membership_result.scalar_one_or_none()

    if org.owner_id != current_user.id and (
        membership is None or membership.role not in [OrgMembershipRole.OWNER, OrgMembershipRole.ADMIN]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this organization"
        )

    # Update fields
    if org_data.name is not None:
        # Check if new name exists
        if org_data.name != org.name:
            name_result = await db.execute(select(Organization).where(Organization.name == org_data.name))
            if name_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"name": {"message": "Organization name already exists"}}
                )
        org.name = org_data.name

    if org_data.description is not None:
        org.description = org_data.description
    if org_data.settings is not None:
        org.settings = org_data.settings

    org.updated = datetime.now(timezone.utc)
    await db.flush()

    return org_to_response(org)


@router.delete("/records/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete organization.
    PocketBase SDK: pb.collection('organizations').delete()
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
