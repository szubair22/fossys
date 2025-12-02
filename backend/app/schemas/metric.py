"""
Metric and MetricValue schemas for dashboard metrics.

Provides Pydantic models for:
- Metric CRUD operations
- MetricValue CRUD operations
- Response schemas with latest value and history
"""
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum


class MetricValueType(str, Enum):
    """Type of metric value for display formatting."""
    NUMBER = "number"
    CURRENCY = "currency"
    PERCENT = "percent"


class MetricFrequency(str, Enum):
    """How often the metric is expected to be updated."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


# ============================================================================
# METRIC VALUE SCHEMAS
# ============================================================================

class MetricValueBase(BaseModel):
    """Base schema for metric value fields."""
    value: Decimal = Field(..., description="The numeric value")
    effective_date: date = Field(default_factory=date.today, description="Date this value is effective")
    notes: Optional[str] = Field(None, max_length=2000, description="Optional notes about this value")


class MetricValueCreate(MetricValueBase):
    """Schema for creating a metric value."""
    pass


class MetricValueResponse(MetricValueBase):
    """Schema for metric value response."""
    id: str
    metric_id: str
    created_by_id: Optional[str] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class MetricValueListResponse(BaseModel):
    """Schema for listing metric values."""
    items: List[MetricValueResponse]
    total: int


# ============================================================================
# METRIC SCHEMAS
# ============================================================================

class MetricBase(BaseModel):
    """Base schema for metric fields."""
    name: str = Field(..., min_length=1, max_length=200, description="Metric name")
    description: Optional[str] = Field(None, max_length=2000, description="Detailed description")
    value_type: MetricValueType = Field(default=MetricValueType.NUMBER, description="How to format the value")
    frequency: MetricFrequency = Field(default=MetricFrequency.MONTHLY, description="Expected update frequency")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Currency for currency metrics")
    target_value: Optional[Decimal] = Field(None, ge=0, description="Optional target for progress tracking")
    sort_order: int = Field(default=0, description="Display order")


class MetricCreate(MetricBase):
    """Schema for creating a metric."""
    organization_id: str = Field(..., min_length=1, max_length=15)
    is_automatic: bool = Field(default=False)
    auto_source: Optional[str] = Field(None, max_length=100)


class MetricUpdate(BaseModel):
    """Schema for updating a metric."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    value_type: Optional[MetricValueType] = None
    frequency: Optional[MetricFrequency] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    target_value: Optional[Decimal] = Field(None)
    is_automatic: Optional[bool] = None
    auto_source: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[int] = None
    is_archived: Optional[bool] = None


class MetricResponse(MetricBase):
    """Schema for metric response with latest value."""
    id: str
    organization_id: str
    is_automatic: bool
    auto_source: Optional[str] = None
    is_archived: bool
    created_by_id: Optional[str] = None
    updated_by_id: Optional[str] = None
    created: datetime
    updated: datetime

    # Latest value info (populated from relationship)
    latest_value: Optional[MetricValueResponse] = None
    # Recent history (last 5 entries)
    recent_history: List[MetricValueResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class MetricListResponse(BaseModel):
    """Schema for listing metrics."""
    items: List[MetricResponse]
    total: int


# ============================================================================
# METRIC WIZARD/SETUP SCHEMAS
# ============================================================================

class MetricTemplate(BaseModel):
    """Template for suggested metrics during setup."""
    name: str
    description: Optional[str] = None
    value_type: MetricValueType = MetricValueType.NUMBER
    frequency: MetricFrequency = MetricFrequency.MONTHLY
    category: Optional[str] = None  # e.g., "membership", "finance", "engagement"


class MetricSetupItem(MetricBase):
    """Item for setup request - org_id not needed as it comes from parent."""
    is_automatic: bool = Field(default=False)
    auto_source: Optional[str] = Field(None, max_length=100)


class MetricSetupRequest(BaseModel):
    """Request for setting up multiple metrics at once (wizard)."""
    organization_id: str = Field(..., min_length=1, max_length=15)
    metrics: List[MetricSetupItem]


class MetricSetupResponse(BaseModel):
    """Response from metric setup."""
    metrics_created: int
    metrics: List[MetricResponse]


# Default metric templates
DEFAULT_METRIC_TEMPLATES: List[MetricTemplate] = [
    MetricTemplate(
        name="Active Members",
        description="Total number of active members in the organization",
        value_type=MetricValueType.NUMBER,
        frequency=MetricFrequency.MONTHLY,
        category="membership"
    ),
    MetricTemplate(
        name="Monthly Revenue",
        description="Total revenue for the current month",
        value_type=MetricValueType.CURRENCY,
        frequency=MetricFrequency.MONTHLY,
        category="finance"
    ),
    MetricTemplate(
        name="Monthly Donations",
        description="Total donations received this month",
        value_type=MetricValueType.CURRENCY,
        frequency=MetricFrequency.MONTHLY,
        category="finance"
    ),
    MetricTemplate(
        name="Events This Month",
        description="Number of events or meetings held",
        value_type=MetricValueType.NUMBER,
        frequency=MetricFrequency.MONTHLY,
        category="engagement"
    ),
    MetricTemplate(
        name="Volunteer Hours",
        description="Total volunteer hours contributed",
        value_type=MetricValueType.NUMBER,
        frequency=MetricFrequency.MONTHLY,
        category="engagement"
    ),
    MetricTemplate(
        name="New Members",
        description="New members added this period",
        value_type=MetricValueType.NUMBER,
        frequency=MetricFrequency.MONTHLY,
        category="membership"
    ),
    MetricTemplate(
        name="Member Retention Rate",
        description="Percentage of members retained from last period",
        value_type=MetricValueType.PERCENT,
        frequency=MetricFrequency.QUARTERLY,
        category="membership"
    ),
]
