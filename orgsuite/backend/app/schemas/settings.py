"""
Settings schemas for OrgSuite Admin API.

Provides Pydantic models for:
- AppSetting: Global application settings (superadmin only)
- OrgSetting: Per-organization settings by scope
"""
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class SettingScope(str, Enum):
    """Scope categories for organization settings."""
    GENERAL = "general"
    GOVERNANCE = "governance"
    MEMBERSHIP = "membership"
    FINANCE = "finance"
    DOCUMENTS = "documents"


# ============================================================================
# APP SETTINGS SCHEMAS
# ============================================================================

class AppSettingCreate(BaseModel):
    """Create a global app setting."""
    key: str = Field(..., min_length=1, max_length=100)
    value: Optional[Any] = None
    description: Optional[str] = Field(None, max_length=500)


class AppSettingUpdate(BaseModel):
    """Update a global app setting (by key)."""
    value: Optional[Any] = None
    description: Optional[str] = Field(None, max_length=500)


class AppSettingResponse(BaseModel):
    """Response for a single app setting."""
    id: str
    key: str
    value: Optional[Any] = None
    description: Optional[str] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class AppSettingListResponse(BaseModel):
    """Response for listing app settings."""
    items: list[AppSettingResponse]
    total: int


# ============================================================================
# ORG SETTINGS SCHEMAS
# ============================================================================

class OrgSettingCreate(BaseModel):
    """Create an organization setting."""
    organization_id: str = Field(..., min_length=1, max_length=15)
    scope: SettingScope
    key: str = Field(..., min_length=1, max_length=100)
    value: Optional[Any] = None
    description: Optional[str] = Field(None, max_length=500)


class OrgSettingUpdate(BaseModel):
    """Update an organization setting."""
    value: Optional[Any] = None
    description: Optional[str] = Field(None, max_length=500)


class OrgSettingResponse(BaseModel):
    """Response for a single org setting."""
    id: str
    organization_id: str
    scope: SettingScope
    key: str
    value: Optional[Any] = None
    description: Optional[str] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class OrgSettingListResponse(BaseModel):
    """Response for listing org settings."""
    items: list[OrgSettingResponse]
    total: int


class EffectiveSettingsResponse(BaseModel):
    """
    Merged effective settings for an organization.

    Returns all settings grouped by scope as a single JSON object.
    Example:
    {
        "general": {"timezone": "America/New_York", ...},
        "governance": {"default_meeting_duration_minutes": 60, ...},
        "membership": {"member_types": ["Regular", "Board"], ...},
        "finance": {"fiscal_year_start_month": 1, ...}
    }
    """
    organization_id: str
    settings: dict[str, dict[str, Any]]


# ============================================================================
# SPECIFIC CONFIG SCHEMAS (for type hints and validation)
# ============================================================================

class GovernanceConfig(BaseModel):
    """Governance module configuration."""
    default_meeting_duration_minutes: int = Field(60, ge=15, le=480)
    default_meeting_number_format: str = Field("FY{year}-{seq:03d}")
    default_quorum_type: str = Field("percent")  # "percent" or "count"
    default_quorum_value: int = Field(50, ge=0)
    motion_types: list[str] = Field(default_factory=lambda: [
        "Main Motion",
        "Amendment",
        "Motion to Table",
        "Motion to Postpone",
        "Motion to Refer",
        "Point of Order",
        "Motion to Adjourn"
    ])
    vote_methods: list[str] = Field(default_factory=lambda: [
        "Voice Vote",
        "Roll Call",
        "Ballot",
        "Show of Hands",
        "Unanimous Consent"
    ])


class MembershipConfig(BaseModel):
    """Membership module configuration."""
    member_types: list[str] = Field(default_factory=lambda: [
        "Regular",
        "Associate",
        "Lifetime",
        "Student",
        "Board",
        "Volunteer",
        "Staff"
    ])
    member_statuses: list[str] = Field(default_factory=lambda: [
        "Active",
        "Inactive",
        "Pending",
        "Alumni",
        "Guest",
        "Honorary",
        "Suspended"
    ])
    member_id_format: str = Field("ORG-{year}-{seq:04d}")
    require_phone: bool = False
    require_email: bool = False


class AccountingBasis(str, Enum):
    """Accounting basis types."""
    CASH = "cash"
    ACCRUAL = "accrual"
    GAAP = "gaap"
    NONPROFIT_GAAP = "nonprofit_gaap"


class OrgEdition(str, Enum):
    """Organization edition types."""
    STARTUP = "startup"
    NONPROFIT = "nonprofit"


class FinanceConfig(BaseModel):
    """Finance module configuration with edition support."""
    # Basic finance settings
    fiscal_year_start_month: int = Field(1, ge=1, le=12)
    default_currency: str = Field("USD", min_length=3, max_length=3)
    enabled_dimensions: list[str] = Field(default_factory=lambda: [
        "department",
        "location",
        "project"
    ])
    payment_methods: list[str] = Field(default_factory=lambda: [
        "Cash",
        "Check",
        "Credit Card",
        "Bank Transfer",
        "PayPal",
        "Venmo",
        "Other"
    ])

    # Edition and accounting settings
    edition: OrgEdition = Field(default=OrgEdition.STARTUP, description="Organization edition")
    accounting_basis: AccountingBasis = Field(default=AccountingBasis.CASH, description="Accounting basis")

    # Feature flags
    enable_rev_rec: bool = Field(default=False, description="Enable revenue recognition (ASC 606)")
    enable_contracts: bool = Field(default=False, description="Enable contracts module")
    enable_restrictions: bool = Field(default=False, description="Enable fund restrictions (nonprofit)")
    enable_donations: bool = Field(default=False, description="Enable donations module")
    enable_budgeting: bool = Field(default=False, description="Enable budgeting module")


# Default edition configurations
STARTUP_EDITION_DEFAULTS = {
    "edition": OrgEdition.STARTUP,
    "accounting_basis": AccountingBasis.CASH,
    "enable_rev_rec": False,
    "enable_contracts": False,
    "enable_restrictions": False,
    "enable_donations": False,
    "enable_budgeting": False,
}

NONPROFIT_EDITION_DEFAULTS = {
    "edition": OrgEdition.NONPROFIT,
    "accounting_basis": AccountingBasis.NONPROFIT_GAAP,
    "enable_rev_rec": True,
    "enable_contracts": True,
    "enable_restrictions": True,
    "enable_donations": True,
    "enable_budgeting": True,
}


class GeneralConfig(BaseModel):
    """General organization configuration."""
    timezone: str = Field("UTC")
    locale: str = Field("en-US")
    date_format: str = Field("YYYY-MM-DD")
    time_format: str = Field("HH:mm")


class AppFeaturesConfig(BaseModel):
    """App-level feature flags."""
    enable_governance: bool = True
    enable_membership: bool = True
    enable_finance: bool = True
    enable_documents: bool = True
    enable_projects: bool = False
    enable_events: bool = False


class AppBrandingConfig(BaseModel):
    """App-level branding settings."""
    app_name: str = Field("OrgSuite")
    primary_color: str = Field("#3B82F6")
    support_email: str = Field("support@orgsuite.app")
    logo_url: Optional[str] = None
