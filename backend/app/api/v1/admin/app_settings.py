"""
Global App Settings API - superadmin only.

Provides endpoints to manage global application settings like:
- app_name, primary_color, support_email
- Feature flags (enable_governance, enable_membership, etc.)
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.app_setting import AppSetting
from app.schemas.settings import (
    AppSettingCreate,
    AppSettingUpdate,
    AppSettingResponse,
    AppSettingListResponse,
)

router = APIRouter()


def require_superadmin(current_user: User) -> User:
    """Verify user is a superadmin."""
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    return current_user


@router.get("", response_model=AppSettingListResponse)
async def list_app_settings(
    key: Optional[str] = Query(None, description="Filter by key prefix"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all global app settings.

    Superadmin access required.

    Optional filter by key prefix to search specific settings.
    """
    require_superadmin(current_user)

    query = select(AppSetting)

    if key:
        query = query.where(AppSetting.key.ilike(f"{key}%"))

    query = query.order_by(AppSetting.key)

    result = await db.execute(query)
    settings = result.scalars().all()

    return AppSettingListResponse(
        items=[AppSettingResponse.model_validate(s) for s in settings],
        total=len(settings)
    )


@router.get("/{key}", response_model=AppSettingResponse)
async def get_app_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single app setting by key.

    Superadmin access required.
    """
    require_superadmin(current_user)

    result = await db.execute(
        select(AppSetting).where(AppSetting.key == key)
    )
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App setting '{key}' not found"
        )

    return AppSettingResponse.model_validate(setting)


@router.put("/{key}", response_model=AppSettingResponse)
async def upsert_app_setting(
    key: str,
    data: AppSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create or update an app setting by key (upsert).

    Superadmin access required.

    If the setting exists, updates its value.
    If not, creates a new setting with the given key.
    """
    require_superadmin(current_user)

    # Try to find existing setting
    result = await db.execute(
        select(AppSetting).where(AppSetting.key == key)
    )
    setting = result.scalar_one_or_none()

    if setting:
        # Update existing
        if data.value is not None:
            setting.value = data.value
        if data.description is not None:
            setting.description = data.description
        setting.updated = datetime.now(timezone.utc)
    else:
        # Create new
        setting = AppSetting(
            key=key,
            value=data.value,
            description=data.description,
        )
        db.add(setting)

    await db.flush()
    await db.refresh(setting)

    return AppSettingResponse.model_validate(setting)


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_app_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an app setting by key.

    Superadmin access required.
    """
    require_superadmin(current_user)

    result = await db.execute(
        select(AppSetting).where(AppSetting.key == key)
    )
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App setting '{key}' not found"
        )

    await db.delete(setting)
    await db.flush()

    return None


@router.post("/bulk", response_model=AppSettingListResponse)
async def bulk_upsert_app_settings(
    settings: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Bulk create or update multiple app settings.

    Superadmin access required.

    Accepts a dict of key: value pairs and creates/updates each.
    """
    require_superadmin(current_user)

    updated_settings = []

    for key, value in settings.items():
        # Try to find existing setting
        result = await db.execute(
            select(AppSetting).where(AppSetting.key == key)
        )
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = value
            setting.updated = datetime.now(timezone.utc)
        else:
            setting = AppSetting(key=key, value=value)
            db.add(setting)

        await db.flush()
        await db.refresh(setting)
        updated_settings.append(setting)

    return AppSettingListResponse(
        items=[AppSettingResponse.model_validate(s) for s in updated_settings],
        total=len(updated_settings)
    )


@router.get("/public/features", response_model=dict)
async def get_public_features(
    db: AsyncSession = Depends(get_db),
):
    """
    Get public feature flags - no auth required.

    Returns enabled features for the application.
    Used by frontend to show/hide modules.
    """
    result = await db.execute(
        select(AppSetting).where(AppSetting.key == "features")
    )
    setting = result.scalar_one_or_none()

    if setting and setting.value:
        return setting.value

    # Return defaults if not configured
    return {
        "enable_governance": True,
        "enable_membership": True,
        "enable_finance": True,
        "enable_documents": True,
        "enable_projects": False,
        "enable_events": False,
    }


@router.get("/public/branding", response_model=dict)
async def get_public_branding(
    db: AsyncSession = Depends(get_db),
):
    """
    Get public branding settings - no auth required.

    Returns app branding for the application.
    Used by frontend for customization.
    """
    result = await db.execute(
        select(AppSetting).where(AppSetting.key == "branding")
    )
    setting = result.scalar_one_or_none()

    if setting and setting.value:
        return setting.value

    # Return defaults if not configured
    return {
        "app_name": "OrgSuite",
        "primary_color": "#3B82F6",
        "support_email": "support@orgsuite.app",
        "logo_url": None,
    }
