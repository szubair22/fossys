"""
Settings service for OrgSuite.

Provides helpers for fetching and using organization settings across modules.
This avoids duplicating settings fetch logic in every router.
"""
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.org_setting import OrgSetting, SettingScope
from app.schemas.settings import (
    GovernanceConfig,
    MembershipConfig,
    FinanceConfig,
    GeneralConfig,
    OrgEdition,
    AccountingBasis,
    STARTUP_EDITION_DEFAULTS,
    NONPROFIT_EDITION_DEFAULTS,
)


async def get_org_settings_by_scope(
    db: AsyncSession,
    organization_id: str,
    scope: SettingScope
) -> dict[str, Any]:
    """
    Fetch organization settings for a specific scope.

    Returns a dict with merged settings from all keys in that scope.
    """
    result = await db.execute(
        select(OrgSetting).where(
            OrgSetting.organization_id == organization_id,
            OrgSetting.scope == scope
        )
    )
    settings = result.scalars().all()

    merged: dict[str, Any] = {}
    for setting in settings:
        if isinstance(setting.value, dict):
            merged.update(setting.value)
        else:
            merged[setting.key] = setting.value

    return merged


async def get_membership_config(
    db: AsyncSession,
    organization_id: str
) -> MembershipConfig:
    """
    Get membership configuration for an organization.

    Returns default values if no settings are configured.
    """
    settings = await get_org_settings_by_scope(
        db, organization_id, SettingScope.MEMBERSHIP
    )

    # Start with defaults and override with any configured values
    config = MembershipConfig()

    if "member_types" in settings:
        config.member_types = settings["member_types"]
    if "member_statuses" in settings:
        config.member_statuses = settings["member_statuses"]
    if "member_id_format" in settings:
        config.member_id_format = settings["member_id_format"]
    if "require_phone" in settings:
        config.require_phone = settings["require_phone"]
    if "require_email" in settings:
        config.require_email = settings["require_email"]

    return config


async def get_governance_config(
    db: AsyncSession,
    organization_id: str
) -> GovernanceConfig:
    """
    Get governance configuration for an organization.

    Returns default values if no settings are configured.
    """
    settings = await get_org_settings_by_scope(
        db, organization_id, SettingScope.GOVERNANCE
    )

    config = GovernanceConfig()

    if "default_meeting_duration_minutes" in settings:
        config.default_meeting_duration_minutes = settings["default_meeting_duration_minutes"]
    if "default_meeting_number_format" in settings:
        config.default_meeting_number_format = settings["default_meeting_number_format"]
    if "default_quorum_type" in settings:
        config.default_quorum_type = settings["default_quorum_type"]
    if "default_quorum_value" in settings:
        config.default_quorum_value = settings["default_quorum_value"]
    if "motion_types" in settings:
        config.motion_types = settings["motion_types"]
    if "vote_methods" in settings:
        config.vote_methods = settings["vote_methods"]

    return config


async def get_finance_config(
    db: AsyncSession,
    organization_id: str
) -> FinanceConfig:
    """
    Get finance configuration for an organization.

    Returns default values if no settings are configured.
    Merges edition defaults with any user overrides.
    """
    settings = await get_org_settings_by_scope(
        db, organization_id, SettingScope.FINANCE
    )

    config = FinanceConfig()

    # Basic finance settings
    if "fiscal_year_start_month" in settings:
        config.fiscal_year_start_month = settings["fiscal_year_start_month"]
    if "default_currency" in settings:
        config.default_currency = settings["default_currency"]
    if "enabled_dimensions" in settings:
        config.enabled_dimensions = settings["enabled_dimensions"]
    if "payment_methods" in settings:
        config.payment_methods = settings["payment_methods"]

    # Edition and accounting settings
    if "edition" in settings:
        config.edition = OrgEdition(settings["edition"])
    if "accounting_basis" in settings:
        config.accounting_basis = AccountingBasis(settings["accounting_basis"])

    # Feature flags
    if "enable_rev_rec" in settings:
        config.enable_rev_rec = settings["enable_rev_rec"]
    if "enable_contracts" in settings:
        config.enable_contracts = settings["enable_contracts"]
    if "enable_restrictions" in settings:
        config.enable_restrictions = settings["enable_restrictions"]
    if "enable_donations" in settings:
        config.enable_donations = settings["enable_donations"]
    if "enable_budgeting" in settings:
        config.enable_budgeting = settings["enable_budgeting"]

    return config


async def get_org_edition(
    db: AsyncSession,
    organization_id: str
) -> OrgEdition:
    """
    Get the edition for an organization.

    Returns "startup" by default if no edition is configured.
    """
    config = await get_finance_config(db, organization_id)
    return config.edition


async def get_finance_features(
    db: AsyncSession,
    organization_id: str
) -> dict:
    """
    Get finance feature flags for an organization.

    Merges default edition settings with any user overrides.
    Returns a dict of feature flags.
    """
    config = await get_finance_config(db, organization_id)

    return {
        "edition": config.edition.value,
        "accounting_basis": config.accounting_basis.value,
        "enable_rev_rec": config.enable_rev_rec,
        "enable_contracts": config.enable_contracts,
        "enable_restrictions": config.enable_restrictions,
        "enable_donations": config.enable_donations,
        "enable_budgeting": config.enable_budgeting,
    }


def get_edition_defaults(edition: OrgEdition) -> dict:
    """
    Get default settings for a given edition.

    Args:
        edition: The organization edition (startup or nonprofit)

    Returns:
        dict of default settings for the edition
    """
    if edition == OrgEdition.NONPROFIT:
        return NONPROFIT_EDITION_DEFAULTS.copy()
    return STARTUP_EDITION_DEFAULTS.copy()


def apply_edition_defaults(
    current_config: dict,
    edition: OrgEdition,
    preserve_overrides: bool = False
) -> dict:
    """
    Apply edition defaults to a config, optionally preserving user overrides.

    Args:
        current_config: Current configuration dict
        edition: Target edition
        preserve_overrides: If True, only sets values not already in current_config

    Returns:
        Updated configuration dict
    """
    defaults = get_edition_defaults(edition)
    result = current_config.copy()

    for key, value in defaults.items():
        if preserve_overrides and key in result:
            continue
        result[key] = value

    return result


async def get_general_config(
    db: AsyncSession,
    organization_id: str
) -> GeneralConfig:
    """
    Get general configuration for an organization.

    Returns default values if no settings are configured.
    """
    settings = await get_org_settings_by_scope(
        db, organization_id, SettingScope.GENERAL
    )

    config = GeneralConfig()

    if "timezone" in settings:
        config.timezone = settings["timezone"]
    if "locale" in settings:
        config.locale = settings["locale"]
    if "date_format" in settings:
        config.date_format = settings["date_format"]
    if "time_format" in settings:
        config.time_format = settings["time_format"]

    return config


def validate_member_type(member_type: str, config: MembershipConfig) -> bool:
    """Check if member type is valid according to config."""
    # Convert to lowercase for comparison
    valid_types = [t.lower() for t in config.member_types]
    return member_type.lower() in valid_types


def validate_member_status(status: str, config: MembershipConfig) -> bool:
    """Check if member status is valid according to config."""
    valid_statuses = [s.lower() for s in config.member_statuses]
    return status.lower() in valid_statuses


def validate_payment_method(method: str, config: FinanceConfig) -> bool:
    """Check if payment method is valid according to config."""
    valid_methods = [m.lower().replace(" ", "_") for m in config.payment_methods]
    return method.lower().replace(" ", "_") in valid_methods


def validate_motion_type(motion_type: str, config: GovernanceConfig) -> bool:
    """Check if motion type is valid according to config."""
    valid_types = [t.lower() for t in config.motion_types]
    return motion_type.lower() in valid_types


def validate_vote_method(method: str, config: GovernanceConfig) -> bool:
    """Check if vote method is valid according to config."""
    valid_methods = [m.lower().replace(" ", "_") for m in config.vote_methods]
    return method.lower().replace(" ", "_") in valid_methods
