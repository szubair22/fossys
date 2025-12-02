"""
Committee endpoints - compatible with PocketBase SDK.
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
from app.models.committee import Committee
from app.models.organization import Organization
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.schemas.committee import CommitteeCreate, CommitteeUpdate, CommitteeResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()


def committee_to_response(committee: Committee, expand: Optional[dict] = None) -> CommitteeResponse:
    """Convert Committee model to CommitteeResponse schema."""
    return CommitteeResponse(
        id=committee.id,
        organization=committee.organization_id,
        name=committee.name,
        description=committee.description,
        admins=[admin.id for admin in committee.admins] if committee.admins else [],
        created=committee.created,
        updated=committee.updated,
        expand=expand,
    )


@router.get("/records", response_model=PaginatedResponse[CommitteeResponse])
async def list_committees(
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    filter: Optional[str] = None,
    sort: Optional[str] = None,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    List committees.
    PocketBase SDK: pb.collection('committees').getList()
    """
    query = select(Committee).options(selectinload(Committee.admins))

    # Parse simple filters if provided
    if filter:
        # Simple organization filter: organization='xxx'
        if "organization=" in filter:
            org_id = filter.split("organization=")[1].split("'")[1] if "'" in filter else filter.split("organization=")[1].split()[0]
            query = query.where(Committee.organization_id == org_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply sorting
    if sort:
        if sort.startswith("-"):
            field_name = sort[1:]
            if hasattr(Committee, field_name):
                query = query.order_by(getattr(Committee, field_name).desc())
        else:
            if hasattr(Committee, sort):
                query = query.order_by(getattr(Committee, sort).asc())
    else:
        query = query.order_by(Committee.created.desc())

    # Apply pagination
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    committees = result.unique().scalars().all()

    # Build response
    items = [committee_to_response(c) for c in committees]

    return PaginatedResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/records", response_model=CommitteeResponse, status_code=status.HTTP_200_OK)
async def create_committee(
    committee_data: CommitteeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new committee.
    PocketBase SDK: pb.collection('committees').create()
    """
    # Check organization exists and user has permission
    org_result = await db.execute(
        select(Organization).where(Organization.id == committee_data.organization)
    )
    org = org_result.scalar_one_or_none()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check user is member of org
    membership_result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.organization_id == committee_data.organization,
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
            detail="Not authorized to create committees in this organization"
        )

    # Create committee
    committee = Committee(
        organization_id=committee_data.organization,
        name=committee_data.name,
        description=committee_data.description,
    )
    committee.admins = [current_user]

    db.add(committee)
    await db.flush()

    return committee_to_response(committee)


@router.get("/records/{committee_id}", response_model=CommitteeResponse)
async def get_committee(
    committee_id: str,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get committee by ID.
    PocketBase SDK: pb.collection('committees').getOne()
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

    return committee_to_response(committee)


@router.patch("/records/{committee_id}", response_model=CommitteeResponse)
async def update_committee(
    committee_id: str,
    committee_data: CommitteeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update committee.
    PocketBase SDK: pb.collection('committees').update()
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
        org_result = await db.execute(
            select(Organization).where(Organization.id == committee.organization_id)
        )
        org = org_result.scalar_one_or_none()

        membership_result = await db.execute(
            select(OrgMembership).where(
                OrgMembership.organization_id == committee.organization_id,
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


@router.delete("/records/{committee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_committee(
    committee_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete committee.
    PocketBase SDK: pb.collection('committees').delete()
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

    # Check permission - org owner or admin only
    org_result = await db.execute(
        select(Organization).where(Organization.id == committee.organization_id)
    )
    org = org_result.scalar_one_or_none()

    if org.owner_id != current_user.id:
        membership_result = await db.execute(
            select(OrgMembership).where(
                OrgMembership.organization_id == committee.organization_id,
                OrgMembership.user_id == current_user.id,
                OrgMembership.is_active == True
            )
        )
        membership = membership_result.scalar_one_or_none()

        if membership is None or membership.role not in [OrgMembershipRole.OWNER, OrgMembershipRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this committee"
            )

    await db.delete(committee)
    await db.flush()

    return None
