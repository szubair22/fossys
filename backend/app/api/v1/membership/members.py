"""
Member endpoints for OrgSuite Membership module.

Now includes validation against organization settings for:
- Member types (configurable per-org)
- Member statuses (configurable per-org)
- Required fields (phone, email)
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.member import Member, MemberStatus, MemberType
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.schemas.member import (
    MemberCreate, MemberUpdate, MemberResponse, MemberListResponse
)
from app.services.settings import (
    get_membership_config,
    validate_member_type,
    validate_member_status,
)

router = APIRouter()


def member_to_response(member: Member) -> MemberResponse:
    """Convert Member model to MemberResponse schema."""
    return MemberResponse(
        id=member.id,
        organization_id=member.organization_id,
        user_id=member.user_id,
        name=member.name,
        email=member.email,
        phone=member.phone,
        address=member.address,
        city=member.city,
        state=member.state,
        postal_code=member.postal_code,
        country=member.country,
        status=member.status.value if isinstance(member.status, MemberStatus) else member.status,
        member_type=member.member_type.value if isinstance(member.member_type, MemberType) else member.member_type,
        join_date=member.join_date,
        expiry_date=member.expiry_date,
        is_public=member.is_public,
        notes=member.notes,
        member_number=member.member_number,
        created=member.created,
        updated=member.updated,
    )


async def check_org_access(
    org_id: str,
    user: User,
    db: AsyncSession,
    require_admin: bool = False
) -> bool:
    """Check if user has access to the organization."""
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


@router.get("/members", response_model=MemberListResponse)
async def list_members(
    organization_id: str,
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status"),
    member_type_filter: Optional[str] = Query(None, alias="member_type"),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List members of an organization.
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    # Base query
    query = select(Member).where(Member.organization_id == organization_id)

    # Apply filters
    if status_filter:
        try:
            status_enum = MemberStatus(status_filter)
            query = query.where(Member.status == status_enum)
        except ValueError:
            pass

    if member_type_filter:
        try:
            type_enum = MemberType(member_type_filter)
            query = query.where(Member.member_type == type_enum)
        except ValueError:
            pass

    if search:
        query = query.where(
            Member.name.ilike(f"%{search}%") |
            Member.email.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * perPage).limit(perPage)
    query = query.order_by(Member.name.asc())

    # Execute query
    result = await db.execute(query)
    members = result.scalars().all()

    # Build response
    items = [member_to_response(m) for m in members]

    return MemberListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def create_member(
    organization_id: str,
    member_data: MemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new member.
    Requires org admin access.

    Validates against organization settings:
    - Member type must be in configured member_types list
    - Member status must be in configured member_statuses list
    - Phone is required if require_phone is True
    - Email is required if require_email is True
    """
    # Check admin access
    if not await check_org_access(organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add members to this organization"
        )

    # Fetch organization membership settings
    membership_config = await get_membership_config(db, organization_id)

    # Validate required fields based on settings
    if membership_config.require_phone and not member_data.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is required for this organization"
        )

    if membership_config.require_email and not member_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required for this organization"
        )

    # Parse and validate status
    status_value = member_data.status.lower() if member_data.status else "pending"

    # First try to validate against settings, then fall back to enum
    if not validate_member_status(status_value, membership_config):
        # Check if it's a valid enum value anyway (backwards compatibility)
        try:
            status_enum = MemberStatus(status_value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid member status '{status_value}'. Allowed statuses: {membership_config.member_statuses}"
            )
    else:
        try:
            status_enum = MemberStatus(status_value)
        except ValueError:
            # Status is valid per settings but not in enum - use default
            status_enum = MemberStatus.PENDING

    # Parse and validate member type
    type_value = member_data.member_type.lower() if member_data.member_type else "regular"

    if not validate_member_type(type_value, membership_config):
        try:
            member_type_enum = MemberType(type_value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid member type '{type_value}'. Allowed types: {membership_config.member_types}"
            )
    else:
        try:
            member_type_enum = MemberType(type_value)
        except ValueError:
            member_type_enum = MemberType.REGULAR

    # Create member
    member = Member(
        organization_id=organization_id,
        user_id=member_data.user_id,
        name=member_data.name,
        email=member_data.email,
        phone=member_data.phone,
        address=member_data.address,
        city=member_data.city,
        state=member_data.state,
        postal_code=member_data.postal_code,
        country=member_data.country,
        status=status_enum,
        member_type=member_type_enum,
        join_date=member_data.join_date,
        expiry_date=member_data.expiry_date,
        is_public=member_data.is_public,
        notes=member_data.notes,
        member_number=member_data.member_number,
    )

    db.add(member)
    await db.flush()

    return member_to_response(member)


@router.get("/members/{member_id}", response_model=MemberResponse)
async def get_member(
    organization_id: str,
    member_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a member by ID.
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    result = await db.execute(
        select(Member).where(
            Member.id == member_id,
            Member.organization_id == organization_id
        )
    )
    member = result.scalar_one_or_none()

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    return member_to_response(member)


@router.patch("/members/{member_id}", response_model=MemberResponse)
async def update_member(
    organization_id: str,
    member_id: str,
    member_data: MemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a member.
    Requires org admin access.

    Validates against organization settings:
    - Member type must be in configured member_types list
    - Member status must be in configured member_statuses list
    - Cannot clear phone if require_phone is True
    - Cannot clear email if require_email is True
    """
    # Check admin access
    if not await check_org_access(organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update members"
        )

    result = await db.execute(
        select(Member).where(
            Member.id == member_id,
            Member.organization_id == organization_id
        )
    )
    member = result.scalar_one_or_none()

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    # Fetch organization membership settings
    membership_config = await get_membership_config(db, organization_id)

    # Validate required fields if they're being cleared
    if membership_config.require_phone and member_data.phone == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is required for this organization"
        )

    if membership_config.require_email and member_data.email == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required for this organization"
        )

    # Update fields
    if member_data.name is not None:
        member.name = member_data.name
    if member_data.email is not None:
        member.email = member_data.email
    if member_data.phone is not None:
        member.phone = member_data.phone
    if member_data.address is not None:
        member.address = member_data.address
    if member_data.city is not None:
        member.city = member_data.city
    if member_data.state is not None:
        member.state = member_data.state
    if member_data.postal_code is not None:
        member.postal_code = member_data.postal_code
    if member_data.country is not None:
        member.country = member_data.country

    # Validate and update status
    if member_data.status is not None:
        status_value = member_data.status.lower()
        if not validate_member_status(status_value, membership_config):
            try:
                member.status = MemberStatus(status_value)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid member status '{status_value}'. Allowed statuses: {membership_config.member_statuses}"
                )
        else:
            try:
                member.status = MemberStatus(status_value)
            except ValueError:
                pass  # Keep current status if not a valid enum

    # Validate and update member type
    if member_data.member_type is not None:
        type_value = member_data.member_type.lower()
        if not validate_member_type(type_value, membership_config):
            try:
                member.member_type = MemberType(type_value)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid member type '{type_value}'. Allowed types: {membership_config.member_types}"
                )
        else:
            try:
                member.member_type = MemberType(type_value)
            except ValueError:
                pass  # Keep current type if not a valid enum

    if member_data.join_date is not None:
        member.join_date = member_data.join_date
    if member_data.expiry_date is not None:
        member.expiry_date = member_data.expiry_date
    if member_data.is_public is not None:
        member.is_public = member_data.is_public
    if member_data.notes is not None:
        member.notes = member_data.notes
    if member_data.member_number is not None:
        member.member_number = member_data.member_number
    if member_data.user_id is not None:
        member.user_id = member_data.user_id

    member.updated = datetime.now(timezone.utc)
    await db.flush()

    return member_to_response(member)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    organization_id: str,
    member_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a member.
    Requires org admin access.
    """
    # Check admin access
    if not await check_org_access(organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete members"
        )

    result = await db.execute(
        select(Member).where(
            Member.id == member_id,
            Member.organization_id == organization_id
        )
    )
    member = result.scalar_one_or_none()

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    await db.delete(member)
    await db.flush()

    return None
