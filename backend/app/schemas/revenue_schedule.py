"""
Revenue Schedule schemas for ASC 606 revenue recognition.

Provides Pydantic models for:
- RevenueSchedule CRUD operations
- RevenueScheduleLine operations
- Revenue recognition run requests/responses
- Waterfall report schemas
"""
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum


class RevenueRecognitionMethod(str, Enum):
    """Revenue recognition method types."""
    POINT_IN_TIME = "point_in_time"
    STRAIGHT_LINE = "straight_line"


class RevenueScheduleStatus(str, Enum):
    """Status of a revenue schedule."""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RevenueScheduleLineStatus(str, Enum):
    """Status of a revenue schedule line."""
    PLANNED = "planned"
    POSTED = "posted"
    CANCELLED = "cancelled"


# ============================================================================
# REVENUE SCHEDULE LINE SCHEMAS
# ============================================================================

class RevenueScheduleLineBase(BaseModel):
    """Base schema for revenue schedule line fields."""
    schedule_date: date
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    amount: Decimal = Field(..., ge=0)
    notes: Optional[str] = Field(None, max_length=1000)


class RevenueScheduleLineResponse(RevenueScheduleLineBase):
    """Schema for revenue schedule line response."""
    id: str
    revenue_schedule_id: str
    status: RevenueScheduleLineStatus
    journal_entry_id: Optional[str] = None
    posted_at: Optional[date] = None
    posted_by_id: Optional[str] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


# ============================================================================
# REVENUE SCHEDULE SCHEMAS
# ============================================================================

class RevenueScheduleBase(BaseModel):
    """Base schema for revenue schedule fields."""
    schedule_number: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=2000)
    total_amount: Decimal = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    recognition_method: RevenueRecognitionMethod = Field(
        default=RevenueRecognitionMethod.STRAIGHT_LINE
    )
    notes: Optional[str] = Field(None, max_length=5000)


class RevenueScheduleCreate(RevenueScheduleBase):
    """Schema for creating a revenue schedule entry."""
    organization_id: str = Field(..., min_length=1, max_length=15)
    contract_line_id: str = Field(..., min_length=1, max_length=15)
    status: RevenueScheduleStatus = Field(default=RevenueScheduleStatus.PLANNED)


class RevenueScheduleUpdate(BaseModel):
    """Schema for updating a revenue schedule entry."""
    schedule_number: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=2000)
    recognition_method: Optional[RevenueRecognitionMethod] = None
    status: Optional[RevenueScheduleStatus] = None
    notes: Optional[str] = Field(None, max_length=5000)


class RevenueScheduleResponse(RevenueScheduleBase):
    """Schema for revenue schedule response."""
    id: str
    organization_id: str
    contract_line_id: str
    status: RevenueScheduleStatus
    created_by_id: Optional[str] = None
    created: datetime
    updated: datetime
    # Computed properties
    recognized_amount: Optional[Decimal] = None
    deferred_amount: Optional[Decimal] = None
    planned_amount: Optional[Decimal] = None
    # Include lines
    lines: List[RevenueScheduleLineResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class RevenueScheduleListResponse(BaseModel):
    """Schema for listing revenue schedules."""
    items: List[RevenueScheduleResponse]
    total: int


# ============================================================================
# SCHEDULE GENERATION SCHEMAS
# ============================================================================

class GenerateScheduleRequest(BaseModel):
    """Request to generate revenue schedules for a contract or lines."""
    contract_id: Optional[str] = Field(None, max_length=15)
    contract_line_ids: Optional[List[str]] = Field(None)

    # Optional: Override schedule granularity (default is monthly)
    # For Phase 1, we only support monthly
    granularity: str = Field(
        default="monthly",
        description="Schedule granularity (monthly only in Phase 1)"
    )


class GenerateScheduleResponse(BaseModel):
    """Response from generating revenue schedules."""
    schedules_created: int
    lines_created: int
    total_amount: Decimal
    contract_id: Optional[str] = None
    schedule_ids: List[str] = Field(default_factory=list)
    message: str


# ============================================================================
# REVENUE RECOGNITION RUN SCHEMAS
# ============================================================================

class RevRecRunRequest(BaseModel):
    """Request to run revenue recognition for due schedule lines."""
    organization_id: str = Field(..., min_length=1, max_length=15)
    as_of_date: date = Field(..., description="Recognize revenue for schedule lines due on or before this date")

    # Optional filters
    contract_id: Optional[str] = Field(None, max_length=15)
    dry_run: bool = Field(
        default=False,
        description="If true, preview results without posting"
    )


class RevRecRunLineResult(BaseModel):
    """Result for a single schedule line in the rev rec run."""
    schedule_line_id: str
    schedule_date: date
    amount: Decimal
    journal_entry_id: Optional[str] = None
    status: str


class RevRecRunResponse(BaseModel):
    """Response from running revenue recognition."""
    lines_processed: int
    lines_posted: int
    total_amount: Decimal
    journal_entries_created: int
    journal_entry_ids: List[str] = Field(default_factory=list)
    dry_run: bool = False
    line_results: List[RevRecRunLineResult] = Field(default_factory=list)
    message: str


# ============================================================================
# WATERFALL REPORT SCHEMAS
# ============================================================================

class WaterfallPeriod(BaseModel):
    """Single period in a revenue waterfall."""
    period: str  # e.g., "2024-01", "2024-02"
    period_start: date
    period_end: date
    planned_amount: Decimal = Decimal(0)
    posted_amount: Decimal = Decimal(0)
    deferred_amount: Decimal = Decimal(0)


class WaterfallResponse(BaseModel):
    """Revenue waterfall report response."""
    organization_id: str
    from_date: date
    to_date: date
    currency: str = "USD"
    total_planned: Decimal = Decimal(0)
    total_posted: Decimal = Decimal(0)
    total_deferred: Decimal = Decimal(0)
    periods: List[WaterfallPeriod] = Field(default_factory=list)


# ============================================================================
# DUE SCHEDULE LINES SCHEMA
# ============================================================================

class DueScheduleLineResponse(BaseModel):
    """Response for a due schedule line."""
    id: str
    revenue_schedule_id: str
    schedule_date: date
    amount: Decimal
    status: RevenueScheduleLineStatus
    # Include context info
    contract_line_description: Optional[str] = None
    contract_name: Optional[str] = None
    contract_number: Optional[str] = None


class DueScheduleLinesResponse(BaseModel):
    """Response for listing due schedule lines."""
    items: List[DueScheduleLineResponse]
    total: int
    total_amount: Decimal
    as_of_date: date
