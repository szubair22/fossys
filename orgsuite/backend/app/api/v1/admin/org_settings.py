"""
Organization Settings API.

Provides endpoints to manage per-organization settings by scope:
- general: timezone, locale, etc.
- governance: meeting defaults, quorum, motion types
- membership: member types, statuses, ID format
- finance: fiscal year, currency, payment methods
- documents: file settings (future)
"""
from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.models.org_setting import OrgSetting, SettingScope
from app.schemas.settings import (
    OrgSettingCreate,
    OrgSettingUpdate,
    OrgSettingResponse,
    OrgSettingListResponse,
    EffectiveSettingsResponse,
    SettingScope as SettingScopeSchema,
)

router = APIRouter()


async def check_org_admin_access(
    org_id: str,
    user: User,
    db: AsyncSession
) -> bool:
    """
    Check if user has admin access to the organization.

    Returns True if user is:
    - A superadmin
    - The organization owner
    - An admin member of the organization
    """
    # Superadmins have access to all orgs
    if user.is_superadmin:
        return True

    # Check organization ownership
    result = await db.execute(
        select(Organization).where(
            Organization.id == org_id,
            Organization.owner_id == user.id
        )
    )
    if result.scalar_one_or_none():
        return True

    # Check membership with admin role
    result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.organization_id == org_id,
            OrgMembership.user_id == user.id,
            OrgMembership.is_active == True,
            OrgMembership.role.in_([OrgMembershipRole.OWNER, OrgMembershipRole.ADMIN])
        )
    )
    return result.scalar_one_or_none() is not None


async def require_org_admin(
    org_id: str,
    user: User,
    db: AsyncSession
) -> None:
    """Verify user has admin access to the organization."""
    # First check if org exists
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    if not await check_org_admin_access(org_id, user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this organization"
        )


@router.get("", response_model=OrgSettingListResponse)
async def list_org_settings(
    organization_id: str = Query(..., description="Organization ID"),
    scope: Optional[SettingScopeSchema] = Query(None, description="Filter by scope"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List organization settings.

    Requires admin access to the organization.

    Optional scope filter to get settings for a specific module.
    """
    await require_org_admin(organization_id, current_user, db)

    query = select(OrgSetting).where(
        OrgSetting.organization_id == organization_id
    )

    if scope:
        query = query.where(OrgSetting.scope == SettingScope(scope.value))

    query = query.order_by(OrgSetting.scope, OrgSetting.key)

    result = await db.execute(query)
    settings = result.scalars().all()

    return OrgSettingListResponse(
        items=[OrgSettingResponse.model_validate(s) for s in settings],
        total=len(settings)
    )


@router.get("/effective", response_model=EffectiveSettingsResponse)
async def get_effective_settings(
    organization_id: str = Query(..., description="Organization ID"),
    scope: Optional[SettingScopeSchema] = Query(None, description="Filter by scope"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get effective (merged) settings for an organization.

    Returns all settings grouped by scope as a single JSON object.
    This is useful for loading all settings at once for the frontend.

    If scope is provided, only returns settings for that scope.
    """
    await require_org_admin(organization_id, current_user, db)

    query = select(OrgSetting).where(
        OrgSetting.organization_id == organization_id
    )

    if scope:
        query = query.where(OrgSetting.scope == SettingScope(scope.value))

    result = await db.execute(query)
    settings = result.scalars().all()

    # Group settings by scope
    merged: dict[str, dict[str, Any]] = {}
    for setting in settings:
        scope_name = setting.scope.value
        if scope_name not in merged:
            merged[scope_name] = {}

        # If value is a dict, merge it; otherwise use key directly
        if isinstance(setting.value, dict):
            merged[scope_name].update(setting.value)
        else:
            merged[scope_name][setting.key] = setting.value

    return EffectiveSettingsResponse(
        organization_id=organization_id,
        settings=merged
    )


@router.get("/{setting_id}", response_model=OrgSettingResponse)
async def get_org_setting(
    setting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single organization setting by ID.

    Requires admin access to the organization.
    """
    result = await db.execute(
        select(OrgSetting).where(OrgSetting.id == setting_id)
    )
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization setting not found"
        )

    await require_org_admin(setting.organization_id, current_user, db)

    return OrgSettingResponse.model_validate(setting)


@router.post("", response_model=OrgSettingResponse, status_code=status.HTTP_201_CREATED)
async def create_org_setting(
    data: OrgSettingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new organization setting.

    Requires admin access to the organization.

    Settings are unique by (organization_id, scope, key).
    """
    await require_org_admin(data.organization_id, current_user, db)

    # Check for existing setting with same key in same scope
    result = await db.execute(
        select(OrgSetting).where(
            OrgSetting.organization_id == data.organization_id,
            OrgSetting.scope == SettingScope(data.scope.value),
            OrgSetting.key == data.key
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Setting '{data.key}' already exists for scope '{data.scope.value}'"
        )

    setting = OrgSetting(
        organization_id=data.organization_id,
        scope=SettingScope(data.scope.value),
        key=data.key,
        value=data.value,
        description=data.description,
    )
    db.add(setting)
    await db.flush()
    await db.refresh(setting)

    return OrgSettingResponse.model_validate(setting)


@router.patch("/{setting_id}", response_model=OrgSettingResponse)
async def update_org_setting(
    setting_id: str,
    data: OrgSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an organization setting.

    Requires admin access to the organization.
    """
    result = await db.execute(
        select(OrgSetting).where(OrgSetting.id == setting_id)
    )
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization setting not found"
        )

    await require_org_admin(setting.organization_id, current_user, db)

    if data.value is not None:
        setting.value = data.value
    if data.description is not None:
        setting.description = data.description

    setting.updated = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(setting)

    return OrgSettingResponse.model_validate(setting)


@router.delete("/{setting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org_setting(
    setting_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an organization setting.

    Requires admin access to the organization.
    """
    result = await db.execute(
        select(OrgSetting).where(OrgSetting.id == setting_id)
    )
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization setting not found"
        )

    await require_org_admin(setting.organization_id, current_user, db)

    await db.delete(setting)
    await db.flush()

    return None


@router.put("/by-key", response_model=OrgSettingResponse)
async def upsert_org_setting_by_key(
    organization_id: str = Query(..., description="Organization ID"),
    scope: SettingScopeSchema = Query(..., description="Setting scope"),
    key: str = Query(..., description="Setting key"),
    data: OrgSettingUpdate = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create or update an organization setting by key (upsert).

    Requires admin access to the organization.

    This is a convenience endpoint for upserting a setting without
    needing to know the setting ID.
    """
    await require_org_admin(organization_id, current_user, db)

    # Try to find existing setting
    result = await db.execute(
        select(OrgSetting).where(
            OrgSetting.organization_id == organization_id,
            OrgSetting.scope == SettingScope(scope.value),
            OrgSetting.key == key
        )
    )
    setting = result.scalar_one_or_none()

    if setting:
        # Update existing
        if data and data.value is not None:
            setting.value = data.value
        if data and data.description is not None:
            setting.description = data.description
        setting.updated = datetime.now(timezone.utc)
    else:
        # Create new
        setting = OrgSetting(
            organization_id=organization_id,
            scope=SettingScope(scope.value),
            key=key,
            value=data.value if data else None,
            description=data.description if data else None,
        )
        db.add(setting)

    await db.flush()
    await db.refresh(setting)

    return OrgSettingResponse.model_validate(setting)


@router.post("/bulk", response_model=OrgSettingListResponse)
async def bulk_upsert_org_settings(
    organization_id: str = Query(..., description="Organization ID"),
    scope: SettingScopeSchema = Query(..., description="Setting scope"),
    settings: dict = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Bulk create or update organization settings for a scope.

    Requires admin access to the organization.

    Accepts a dict of key: value pairs and creates/updates each.
    Useful for saving an entire config section at once.
    """
    await require_org_admin(organization_id, current_user, db)

    if not settings:
        settings = {}

    updated_settings = []

    for key, value in settings.items():
        # Try to find existing setting
        result = await db.execute(
            select(OrgSetting).where(
                OrgSetting.organization_id == organization_id,
                OrgSetting.scope == SettingScope(scope.value),
                OrgSetting.key == key
            )
        )
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = value
            setting.updated = datetime.now(timezone.utc)
        else:
            setting = OrgSetting(
                organization_id=organization_id,
                scope=SettingScope(scope.value),
                key=key,
                value=value,
            )
            db.add(setting)

        await db.flush()
        await db.refresh(setting)
        updated_settings.append(setting)

    return OrgSettingListResponse(
        items=[OrgSettingResponse.model_validate(s) for s in updated_settings],
        total=len(updated_settings)
    )
