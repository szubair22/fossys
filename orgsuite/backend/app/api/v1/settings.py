"""
Public Organization Settings API.

Provides read-only access to organization settings for authenticated members.
This is separate from the admin settings API which allows modification.

These endpoints are used by the frontend to dynamically configure forms
based on organization settings (member types, payment methods, etc.).
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.org_membership import OrgMembership
from app.services.settings import (
    get_membership_config,
    get_governance_config,
    get_finance_config,
    get_general_config,
)
from app.schemas.settings import (
    MembershipConfig,
    GovernanceConfig,
    FinanceConfig,
    GeneralConfig,
)

router = APIRouter(prefix="/settings", tags=["settings"])


async def check_org_membership(
    org_id: str,
    user: User,
    db: AsyncSession
) -> bool:
    """Check if user is a member of the organization."""
    result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.organization_id == org_id,
            OrgMembership.user_id == user.id,
            OrgMembership.is_active == True
        )
    )
    return result.scalar_one_or_none() is not None


async def require_org_membership(
    org_id: str,
    user: User,
    db: AsyncSession
) -> None:
    """Verify user has membership in the organization."""
    if not await check_org_membership(org_id, user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )


class AllSettingsResponse(BaseModel):
    """Combined settings response for all scopes."""
    organization_id: str
    membership: MembershipConfig
    governance: GovernanceConfig
    finance: FinanceConfig
    general: GeneralConfig


@router.get("/membership", response_model=MembershipConfig)
async def get_membership_settings(
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get membership configuration for an organization.

    Returns settings like allowed member types, statuses, and required fields.
    Used by the frontend to dynamically populate forms.

    Requires membership in the organization.
    """
    await require_org_membership(organization_id, current_user, db)
    return await get_membership_config(db, organization_id)


@router.get("/governance", response_model=GovernanceConfig)
async def get_governance_settings(
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get governance configuration for an organization.

    Returns settings like meeting duration defaults, motion types, and vote methods.
    Used by the frontend to dynamically populate forms.

    Requires membership in the organization.
    """
    await require_org_membership(organization_id, current_user, db)
    return await get_governance_config(db, organization_id)


@router.get("/finance", response_model=FinanceConfig)
async def get_finance_settings(
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get finance configuration for an organization.

    Returns settings like default currency, payment methods, and enabled dimensions.
    Used by the frontend to dynamically populate forms.

    Requires membership in the organization.
    """
    await require_org_membership(organization_id, current_user, db)
    return await get_finance_config(db, organization_id)


@router.get("/general", response_model=GeneralConfig)
async def get_general_settings(
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get general configuration for an organization.

    Returns settings like timezone, locale, and date/time formats.
    Used by the frontend for display formatting.

    Requires membership in the organization.
    """
    await require_org_membership(organization_id, current_user, db)
    return await get_general_config(db, organization_id)


@router.get("", response_model=AllSettingsResponse)
async def get_all_settings(
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all settings for an organization.

    Returns settings for all scopes (membership, governance, finance, general).
    This is a convenience endpoint to fetch everything at once.

    Requires membership in the organization.
    """
    await require_org_membership(organization_id, current_user, db)

    return AllSettingsResponse(
        organization_id=organization_id,
        membership=await get_membership_config(db, organization_id),
        governance=await get_governance_config(db, organization_id),
        finance=await get_finance_config(db, organization_id),
        general=await get_general_config(db, organization_id),
    )
