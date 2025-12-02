"""
Organization membership endpoints for OrgSuite Governance module.

Migrated from PocketBase to FastAPI.
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
from app.models.organization import Organization
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.schemas.org_membership import (
    OrgMembershipCreate,
    OrgMembershipUpdate,
    OrgMembershipResponse,
    OrgMembershipListResponse,
    AddMemberByEmailRequest,
    UserInfo,
    OrganizationInfo,
)

router = APIRouter()


def membership_to_response(
    membership: OrgMembership,
    include_user: bool = False,
    include_org: bool = False
) -> OrgMembershipResponse:
    """Convert OrgMembership model to response schema."""
    user_info = None
    org_info = None

    if include_user and membership.user:
        user_info = UserInfo(
            id=membership.user.id,
            email=membership.user.email,
            name=membership.user.name,
            avatar=membership.user.avatar
        )

    if include_org and membership.organization:
        org_info = OrganizationInfo(
            id=membership.organization.id,
            name=membership.organization.name,
            description=membership.organization.description,
            logo=membership.organization.logo
        )

    return OrgMembershipResponse(
        id=membership.id,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        role=membership.role.value if isinstance(membership.role, OrgMembershipRole) else membership.role,
        is_active=membership.is_active,
        invited_by_id=membership.invited_by_id,
        invited_at=membership.invited_at,
        joined_at=membership.joined_at,
        permissions=membership.permissions,
        created=membership.created,
        updated=membership.updated,
        user=user_info,
        organization=org_info,
    )


async def check_org_admin_access(
    organization_id: str,
    user: User,
    db: AsyncSession
) -> bool:
    """Check if user has admin/owner access to the organization."""
    # Check if user is org owner
    org_result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    org = org_result.scalar_one_or_none()
    if org and org.owner_id == user.id:
        return True

    # Check membership
    result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.organization_id == organization_id,
            OrgMembership.user_id == user.id,
            OrgMembership.is_active == True
        )
    )
    membership = result.scalar_one_or_none()

    if membership is None:
        return False

    return membership.role in [OrgMembershipRole.OWNER, OrgMembershipRole.ADMIN]


@router.get("/my", response_model=OrgMembershipListResponse)
async def get_my_memberships(
    page: int = Query(1, ge=1),
    perPage: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all memberships for the current user.
    Returns organizations the user belongs to.
    """
    query = select(OrgMembership).options(
        selectinload(OrgMembership.organization)
    ).where(
        OrgMembership.user_id == current_user.id,
        OrgMembership.is_active == True
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(OrgMembership.created.desc())
    query = query.offset((page - 1) * perPage).limit(perPage)

    result = await db.execute(query)
    memberships = result.scalars().all()

    items = [membership_to_response(m, include_user=False, include_org=True) for m in memberships]

    return OrgMembershipListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.get("/org/{organization_id}", response_model=OrgMembershipListResponse)
async def get_org_members(
    organization_id: str,
    role: Optional[str] = Query(None, description="Filter by role"),
    page: int = Query(1, ge=1),
    perPage: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all members of an organization.
    Requires membership in the organization.
    """
    # Check user has access to this org
    user_membership = await db.execute(
        select(OrgMembership).where(
            OrgMembership.organization_id == organization_id,
            OrgMembership.user_id == current_user.id,
            OrgMembership.is_active == True
        )
    )
    if not user_membership.scalar_one_or_none():
        # Also check if user is org owner
        org_result = await db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = org_result.scalar_one_or_none()
        if not org or org.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this organization's members"
            )

    # Build query
    query = select(OrgMembership).options(
        selectinload(OrgMembership.user)
    ).where(
        OrgMembership.organization_id == organization_id,
        OrgMembership.is_active == True
    )

    # Filter by role
    if role:
        try:
            role_enum = OrgMembershipRole(role)
            query = query.where(OrgMembership.role == role_enum)
        except ValueError:
            pass

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and sorting
    query = query.order_by(OrgMembership.role, OrgMembership.created.desc())
    query = query.offset((page - 1) * perPage).limit(perPage)

    result = await db.execute(query)
    memberships = result.scalars().all()

    items = [membership_to_response(m, include_user=True, include_org=False) for m in memberships]

    return OrgMembershipListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.get("/check/{organization_id}", response_model=OrgMembershipResponse)
async def get_my_org_membership(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's membership in an organization.
    Returns 404 if not a member.
    """
    result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.organization_id == organization_id,
            OrgMembership.user_id == current_user.id,
            OrgMembership.is_active == True
        )
    )
    membership = result.scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not a member of this organization"
        )

    return membership_to_response(membership)


@router.get("/{membership_id}", response_model=OrgMembershipResponse)
async def get_membership(
    membership_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific membership by ID.
    """
    result = await db.execute(
        select(OrgMembership).options(
            selectinload(OrgMembership.user),
            selectinload(OrgMembership.organization)
        ).where(OrgMembership.id == membership_id)
    )
    membership = result.scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found"
        )

    # Check access - must be the user or org admin
    if membership.user_id != current_user.id:
        if not await check_org_admin_access(membership.organization_id, current_user, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this membership"
            )

    return membership_to_response(membership, include_user=True, include_org=True)


@router.post("/org/{organization_id}/add-by-email", response_model=OrgMembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_member_by_email(
    organization_id: str,
    request: AddMemberByEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a member to an organization by email.
    Requires admin access.
    """
    # Check admin access
    if not await check_org_admin_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add members to this organization"
        )

    # Find user by email
    user_result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = user_result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found with that email"
        )

    # Check if already a member
    existing_result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.organization_id == organization_id,
            OrgMembership.user_id == user.id
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization"
            )
        else:
            # Reactivate membership
            existing.is_active = True
            try:
                existing.role = OrgMembershipRole(request.role)
            except ValueError:
                existing.role = OrgMembershipRole.MEMBER
            existing.updated = datetime.now(timezone.utc)
            await db.flush()
            return membership_to_response(existing)

    # Parse role
    try:
        role_enum = OrgMembershipRole(request.role)
    except ValueError:
        role_enum = OrgMembershipRole.MEMBER

    # Create membership
    membership = OrgMembership(
        organization_id=organization_id,
        user_id=user.id,
        role=role_enum,
        is_active=True,
        invited_by_id=current_user.id,
        invited_at=datetime.now(timezone.utc),
        joined_at=datetime.now(timezone.utc),
    )

    db.add(membership)
    await db.flush()

    return membership_to_response(membership)


@router.post("", response_model=OrgMembershipResponse, status_code=status.HTTP_201_CREATED)
async def create_membership(
    membership_data: OrgMembershipCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new organization membership.
    Requires admin access to the organization.
    """
    # Check admin access
    if not await check_org_admin_access(membership_data.organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add members to this organization"
        )

    # Get user ID
    user_id = membership_data.user_id
    if not user_id and membership_data.user_email:
        user_result = await db.execute(
            select(User).where(User.email == membership_data.user_email)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        user_id = user.id

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or user_email is required"
        )

    # Check if already a member
    existing_result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.organization_id == membership_data.organization_id,
            OrgMembership.user_id == user_id
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing and existing.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization"
        )

    # Parse role
    try:
        role_enum = OrgMembershipRole(membership_data.role)
    except ValueError:
        role_enum = OrgMembershipRole.MEMBER

    if existing:
        # Reactivate
        existing.is_active = True
        existing.role = role_enum
        existing.updated = datetime.now(timezone.utc)
        await db.flush()
        return membership_to_response(existing)

    # Create new membership
    membership = OrgMembership(
        organization_id=membership_data.organization_id,
        user_id=user_id,
        role=role_enum,
        is_active=True,
        invited_by_id=current_user.id,
        invited_at=datetime.now(timezone.utc),
        joined_at=datetime.now(timezone.utc),
        permissions=membership_data.permissions,
    )

    db.add(membership)
    await db.flush()

    return membership_to_response(membership)


@router.patch("/{membership_id}", response_model=OrgMembershipResponse)
async def update_membership(
    membership_id: str,
    membership_data: OrgMembershipUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an organization membership.
    Requires admin access.
    """
    result = await db.execute(
        select(OrgMembership).where(OrgMembership.id == membership_id)
    )
    membership = result.scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found"
        )

    # Check admin access
    if not await check_org_admin_access(membership.organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this membership"
        )

    # Prevent demoting/removing the last owner
    if membership_data.role and membership.role == OrgMembershipRole.OWNER:
        if membership_data.role != "owner":
            # Count other owners
            owner_count = await db.execute(
                select(func.count()).select_from(OrgMembership).where(
                    OrgMembership.organization_id == membership.organization_id,
                    OrgMembership.role == OrgMembershipRole.OWNER,
                    OrgMembership.is_active == True,
                    OrgMembership.id != membership_id
                )
            )
            if owner_count.scalar() == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote the last owner"
                )

    # Update fields
    if membership_data.role is not None:
        try:
            membership.role = OrgMembershipRole(membership_data.role)
        except ValueError:
            pass

    if membership_data.is_active is not None:
        # Prevent deactivating the last owner
        if not membership_data.is_active and membership.role == OrgMembershipRole.OWNER:
            owner_count = await db.execute(
                select(func.count()).select_from(OrgMembership).where(
                    OrgMembership.organization_id == membership.organization_id,
                    OrgMembership.role == OrgMembershipRole.OWNER,
                    OrgMembership.is_active == True,
                    OrgMembership.id != membership_id
                )
            )
            if owner_count.scalar() == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the last owner"
                )
        membership.is_active = membership_data.is_active

    if membership_data.permissions is not None:
        membership.permissions = membership_data.permissions

    membership.updated = datetime.now(timezone.utc)
    await db.flush()

    return membership_to_response(membership)


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_membership(
    membership_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a member from an organization.
    Requires admin access or being the member themselves.
    """
    result = await db.execute(
        select(OrgMembership).where(OrgMembership.id == membership_id)
    )
    membership = result.scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found"
        )

    # Check access - admin or self
    is_self = membership.user_id == current_user.id
    is_admin = await check_org_admin_access(membership.organization_id, current_user, db)

    if not is_self and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to remove this membership"
        )

    # Prevent removing the last owner
    if membership.role == OrgMembershipRole.OWNER:
        owner_count = await db.execute(
            select(func.count()).select_from(OrgMembership).where(
                OrgMembership.organization_id == membership.organization_id,
                OrgMembership.role == OrgMembershipRole.OWNER,
                OrgMembership.is_active == True,
                OrgMembership.id != membership_id
            )
        )
        if owner_count.scalar() == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner"
            )

    await db.delete(membership)
    await db.flush()

    return None
