"""
Organization invitation endpoints for OrgSuite.

Allows org admins/owners to invite new users by email.
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.core.permissions import require_role
from app.models.user import User
from app.models.organization import Organization
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.models.org_invite import OrgInvite, OrgInviteStatus, OrgInviteRole
from app.schemas.org_invite import (
    OrgInviteCreate, OrgInviteResponse, OrgInviteListResponse,
    OrgInviteAccept, OrgInviteAcceptResponse
)
from app.services.email import send_invitation_email

router = APIRouter()


def invite_to_response(invite: OrgInvite, org_name: str = None, inviter_name: str = None) -> OrgInviteResponse:
    """Convert OrgInvite model to response schema."""
    return OrgInviteResponse(
        id=invite.id,
        organization_id=invite.organization_id,
        organization_name=org_name,
        email=invite.email,
        role=invite.role.value if hasattr(invite.role, 'value') else invite.role,
        token=invite.token,
        status=invite.status.value if hasattr(invite.status, 'value') else invite.status,
        expires_at=invite.expires_at,
        invited_by_id=invite.invited_by_id,
        invited_by_name=inviter_name,
        accepted_by_id=invite.accepted_by_id,
        accepted_at=invite.accepted_at,
        cancelled_at=invite.cancelled_at,
        message=invite.message,
        created=invite.created,
        updated=invite.updated,
    )


@router.post("", response_model=OrgInviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    invite_data: OrgInviteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create an organization invitation.

    Only admins and owners can create invitations.
    """
    # Check user has admin/owner role
    await require_role(
        db, current_user.id, invite_data.organization_id,
        [OrgMembershipRole.ADMIN, OrgMembershipRole.OWNER]
    )

    # Get organization name
    org_result = await db.execute(
        select(Organization).where(Organization.id == invite_data.organization_id)
    )
    organization = org_result.scalar_one_or_none()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check if user already has a pending invite to this org
    existing_invite_result = await db.execute(
        select(OrgInvite).where(
            OrgInvite.organization_id == invite_data.organization_id,
            OrgInvite.email == invite_data.email.lower(),
            OrgInvite.status == OrgInviteStatus.PENDING
        )
    )
    if existing_invite_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invitation is already pending for this email"
        )

    # Check if user is already a member
    user_result = await db.execute(
        select(User).where(User.email == invite_data.email.lower())
    )
    existing_user = user_result.scalar_one_or_none()
    if existing_user:
        membership_result = await db.execute(
            select(OrgMembership).where(
                OrgMembership.organization_id == invite_data.organization_id,
                OrgMembership.user_id == existing_user.id
            )
        )
        if membership_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization"
            )

    # Validate role
    try:
        role = OrgInviteRole(invite_data.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be admin, member, or viewer"
        )

    # Create invitation
    invite = OrgInvite(
        organization_id=invite_data.organization_id,
        email=invite_data.email.lower(),
        role=role,
        message=invite_data.message,
        invited_by_id=current_user.id,
    )

    db.add(invite)
    await db.flush()

    # Send invitation email
    await send_invitation_email(
        to=invite.email,
        organization_name=organization.name,
        inviter_name=current_user.name,
        role=role.value,
        invite_token=invite.token,
        message=invite.message
    )

    return invite_to_response(invite, organization.name, current_user.name)


@router.get("/org/{organization_id}", response_model=OrgInviteListResponse)
async def list_org_invites(
    organization_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List invitations for an organization.

    Only admins and owners can view invitations.
    """
    # Check user has admin/owner role
    await require_role(
        db, current_user.id, organization_id,
        [OrgMembershipRole.ADMIN, OrgMembershipRole.OWNER]
    )

    # Get org name
    org_result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = org_result.scalar_one_or_none()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Build query
    query = select(OrgInvite).where(OrgInvite.organization_id == organization_id)

    # Apply status filter
    if status_filter:
        try:
            status_enum = OrgInviteStatus(status_filter)
            query = query.where(OrgInvite.status == status_enum)
        except ValueError:
            pass

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(OrgInvite.created.desc())
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute
    result = await db.execute(query)
    invites = result.scalars().all()

    # Get inviter names
    items = []
    for invite in invites:
        inviter_name = None
        if invite.invited_by_id:
            inviter_result = await db.execute(
                select(User.name).where(User.id == invite.invited_by_id)
            )
            inviter_name = inviter_result.scalar_one_or_none()
        items.append(invite_to_response(invite, organization.name, inviter_name))

    return OrgInviteListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.get("/{invite_id}", response_model=OrgInviteResponse)
async def get_invite(
    invite_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get an invitation by ID.

    Admins/owners can view any invite for their org.
    Users can view invites sent to their email.
    """
    result = await db.execute(
        select(OrgInvite).where(OrgInvite.id == invite_id)
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Check access - either admin/owner of org or the invitee
    is_invitee = invite.email.lower() == current_user.email.lower()

    if not is_invitee:
        await require_role(
            db, current_user.id, invite.organization_id,
            [OrgMembershipRole.ADMIN, OrgMembershipRole.OWNER]
        )

    # Get org and inviter names
    org_result = await db.execute(
        select(Organization).where(Organization.id == invite.organization_id)
    )
    org = org_result.scalar_one_or_none()

    inviter_result = await db.execute(
        select(User.name).where(User.id == invite.invited_by_id)
    )
    inviter_name = inviter_result.scalar_one_or_none()

    return invite_to_response(invite, org.name if org else None, inviter_name)


@router.get("/by-token/{token}", response_model=OrgInviteResponse)
async def get_invite_by_token(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get an invitation by token (public endpoint for registration flow).

    Returns limited info for security.
    """
    result = await db.execute(
        select(OrgInvite).where(OrgInvite.token == token)
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Check if still valid
    if invite.status != OrgInviteStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Invitation is {invite.status.value}")

    if invite.is_expired:
        raise HTTPException(status_code=400, detail="Invitation has expired")

    # Get org name
    org_result = await db.execute(
        select(Organization).where(Organization.id == invite.organization_id)
    )
    org = org_result.scalar_one_or_none()

    return invite_to_response(invite, org.name if org else None)


@router.post("/accept", response_model=OrgInviteAcceptResponse)
async def accept_invite(
    accept_data: OrgInviteAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept an organization invitation.

    Creates org membership for the accepting user.
    """
    # Find invite by token
    result = await db.execute(
        select(OrgInvite).where(OrgInvite.token == accept_data.token)
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Check if still valid
    if invite.status != OrgInviteStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation has already been {invite.status.value}"
        )

    if invite.is_expired:
        # Mark as expired
        invite.status = OrgInviteStatus.EXPIRED
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )

    # Check if user is already a member
    membership_result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.organization_id == invite.organization_id,
            OrgMembership.user_id == current_user.id
        )
    )
    if membership_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this organization"
        )

    # Get organization
    org_result = await db.execute(
        select(Organization).where(Organization.id == invite.organization_id)
    )
    organization = org_result.scalar_one_or_none()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Map invite role to membership role
    role_mapping = {
        OrgInviteRole.ADMIN: OrgMembershipRole.ADMIN,
        OrgInviteRole.MEMBER: OrgMembershipRole.MEMBER,
        OrgInviteRole.VIEWER: OrgMembershipRole.VIEWER,
    }
    membership_role = role_mapping.get(invite.role, OrgMembershipRole.MEMBER)

    # Create membership
    membership = OrgMembership(
        organization_id=invite.organization_id,
        user_id=current_user.id,
        role=membership_role,
        is_active=True,
        invited_by_id=invite.invited_by_id,
        invited_at=invite.created,
        joined_at=datetime.now(timezone.utc),
    )
    db.add(membership)

    # Update invite status
    invite.status = OrgInviteStatus.ACCEPTED
    invite.accepted_by_id = current_user.id
    invite.accepted_at = datetime.now(timezone.utc)

    await db.flush()

    return OrgInviteAcceptResponse(
        success=True,
        organization_id=organization.id,
        organization_name=organization.name,
        role=membership_role.value,
        message=f"You have joined {organization.name} as a {membership_role.value}"
    )


@router.post("/{invite_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invite(
    invite_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel an organization invitation.

    Only admins/owners can cancel invitations.
    """
    result = await db.execute(
        select(OrgInvite).where(OrgInvite.id == invite_id)
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Check user has admin/owner role
    await require_role(
        db, current_user.id, invite.organization_id,
        [OrgMembershipRole.ADMIN, OrgMembershipRole.OWNER]
    )

    if invite.status != OrgInviteStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel an invitation that is {invite.status.value}"
        )

    invite.status = OrgInviteStatus.CANCELLED
    invite.cancelled_at = datetime.now(timezone.utc)

    await db.flush()

    return None


@router.post("/{invite_id}/resend", response_model=OrgInviteResponse)
async def resend_invite(
    invite_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Resend an invitation (extends expiry and regenerates token).

    Only admins/owners can resend invitations.
    """
    result = await db.execute(
        select(OrgInvite).where(OrgInvite.id == invite_id)
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Check user has admin/owner role
    await require_role(
        db, current_user.id, invite.organization_id,
        [OrgMembershipRole.ADMIN, OrgMembershipRole.OWNER]
    )

    if invite.status == OrgInviteStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot resend an accepted invitation"
        )

    # Reset the invitation
    from app.models.org_invite import generate_invite_token, default_expiry

    invite.token = generate_invite_token()
    invite.expires_at = default_expiry()
    invite.status = OrgInviteStatus.PENDING
    invite.invited_by_id = current_user.id
    invite.updated = datetime.now(timezone.utc)

    await db.flush()

    # Get org name
    org_result = await db.execute(
        select(Organization).where(Organization.id == invite.organization_id)
    )
    org = org_result.scalar_one_or_none()

    # Send invitation email
    await send_invitation_email(
        to=invite.email,
        organization_name=org.name if org else "Organization",
        inviter_name=current_user.name,
        role=invite.role.value if hasattr(invite.role, 'value') else invite.role,
        invite_token=invite.token,
        message=invite.message
    )

    return invite_to_response(invite, org.name if org else None, current_user.name)
