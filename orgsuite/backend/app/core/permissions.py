"""Role & permission helpers for organization-scoped resources."""
from typing import Iterable, Sequence, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.models.organization import Organization
from app.models.meeting import Meeting
from app.models.committee import Committee


async def get_membership(db: AsyncSession, user_id: str, organization_id: str):
    result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.user_id == user_id,
            OrgMembership.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def ensure_org_exists(db: AsyncSession, organization_id: str):
    result = await db.execute(select(Organization).where(Organization.id == organization_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


def _role_rank(role: OrgMembershipRole) -> int:
    order = [OrgMembershipRole.VIEWER, OrgMembershipRole.MEMBER, OrgMembershipRole.ADMIN, OrgMembershipRole.OWNER]
    return order.index(role)


async def require_role(
    db: AsyncSession,
    user_id: str,
    organization_id: str,
    allowed: Sequence[OrgMembershipRole] | Iterable[OrgMembershipRole],
) -> OrgMembership:
    """Ensure the user has any role in allowed sequence. Raises 403 otherwise.
    Special case: if no membership rows exist yet and user is the org.owner, allow.
    """
    org = await ensure_org_exists(db, organization_id)
    membership = await get_membership(db, user_id, organization_id)
    if membership is None:
        # Allow implicit owner bootstrap
        if getattr(org, "owner_id", None) == user_id and OrgMembershipRole.OWNER in allowed:
            return membership  # None, but owner accepted
        raise HTTPException(status_code=403, detail="Not a member of organization")
    if membership.role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient role")
    return membership


async def require_min_role(
    db: AsyncSession,
    user_id: str,
    organization_id: str,
    minimum: OrgMembershipRole,
) -> OrgMembership:
    """Ensure membership role rank >= minimum."""
    org = await ensure_org_exists(db, organization_id)
    membership = await get_membership(db, user_id, organization_id)
    if membership is None:
        if getattr(org, "owner_id", None) == user_id and minimum == OrgMembershipRole.OWNER:
            return membership
        raise HTTPException(status_code=403, detail="Not a member of organization")
    if _role_rank(membership.role) < _role_rank(minimum):
        raise HTTPException(status_code=403, detail="Insufficient role")
    return membership


def is_admin_or_owner(membership: OrgMembership | None) -> bool:
    if membership is None:
        return False
    return membership.role in (OrgMembershipRole.ADMIN, OrgMembershipRole.OWNER)


async def resolve_meeting_org_id(db: AsyncSession, meeting: Meeting) -> Optional[str]:
    """Return organization_id for a meeting, preferring direct FK, else committee's org."""
    if getattr(meeting, "organization_id", None):
        return meeting.organization_id
    if getattr(meeting, "committee_id", None):
        committee_result = await db.execute(select(Committee).where(Committee.id == meeting.committee_id))
        committee = committee_result.scalar_one_or_none()
        if committee:
            return committee.organization_id
    return None
