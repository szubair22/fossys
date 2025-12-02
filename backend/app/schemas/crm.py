"""
Pydantic schemas for CRM module.

Includes schemas for Leads, Opportunities, and Activities.
"""
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field


# ============================================================================
# LEAD SCHEMAS
# ============================================================================

class LeadCreate(BaseModel):
    """Create a new lead."""
    name: str = Field(..., min_length=1, max_length=200)
    contact_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    company: Optional[str] = Field(None, max_length=200)
    website: Optional[str] = Field(None, max_length=500)
    status: str = Field(default="new")
    source: str = Field(default="other")
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    """Update a lead."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    company: Optional[str] = Field(None, max_length=200)
    website: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    owner_user_id: Optional[str] = None


class LeadConvert(BaseModel):
    """Convert lead to contact and/or opportunity."""
    create_contact: bool = True
    create_opportunity: bool = True
    opportunity_title: Optional[str] = None
    opportunity_amount: Optional[Decimal] = None


class LeadResponse(BaseModel):
    """Lead response."""
    id: str
    organization_id: str
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    status: str
    source: str
    owner_user_id: Optional[str] = None
    notes: Optional[str] = None
    converted_contact_id: Optional[str] = None
    converted_opportunity_id: Optional[str] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Paginated list of leads."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[LeadResponse]


# ============================================================================
# OPPORTUNITY SCHEMAS
# ============================================================================

class OpportunityCreate(BaseModel):
    """Create a new opportunity."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    related_contact_id: Optional[str] = None
    related_project_id: Optional[str] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field(default="USD", max_length=3)
    stage: str = Field(default="prospecting")
    probability: int = Field(default=10, ge=0, le=100)
    expected_close_date: Optional[date] = None
    source: str = Field(default="other")


class OpportunityUpdate(BaseModel):
    """Update an opportunity."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    related_contact_id: Optional[str] = None
    related_project_id: Optional[str] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    probability: Optional[int] = Field(None, ge=0, le=100)
    expected_close_date: Optional[date] = None
    actual_close_date: Optional[date] = None
    source: Optional[str] = None
    owner_user_id: Optional[str] = None


class OpportunityStageChange(BaseModel):
    """Change opportunity stage."""
    new_stage: str


class OpportunityResponse(BaseModel):
    """Opportunity response."""
    id: str
    organization_id: str
    title: str
    description: Optional[str] = None
    related_contact_id: Optional[str] = None
    related_project_id: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str
    stage: str
    probability: int
    expected_close_date: Optional[date] = None
    actual_close_date: Optional[date] = None
    source: str
    owner_user_id: Optional[str] = None
    created: datetime
    updated: datetime
    # Expanded fields for UI
    related_contact_name: Optional[str] = None
    related_project_name: Optional[str] = None
    owner_name: Optional[str] = None

    class Config:
        from_attributes = True


class OpportunityListResponse(BaseModel):
    """Paginated list of opportunities."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[OpportunityResponse]


# ============================================================================
# ACTIVITY SCHEMAS
# ============================================================================

class ActivityCreate(BaseModel):
    """Create a new activity."""
    opportunity_id: str
    contact_id: Optional[str] = None
    type: str = Field(..., description="Activity type: call, email, meeting, note, task")
    subject: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[datetime] = None


class ActivityUpdate(BaseModel):
    """Update an activity."""
    contact_id: Optional[str] = None
    type: Optional[str] = None
    subject: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ActivityResponse(BaseModel):
    """Activity response."""
    id: str
    organization_id: str
    opportunity_id: str
    contact_id: Optional[str] = None
    type: str
    subject: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by_user_id: Optional[str] = None
    created: datetime
    updated: datetime
    # Expanded fields for UI
    created_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class ActivityListResponse(BaseModel):
    """Paginated list of activities."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[ActivityResponse]


# ============================================================================
# CRM SUMMARY SCHEMAS (for Dashboard integration)
# ============================================================================

class CRMSnapshot(BaseModel):
    """CRM snapshot for dashboard."""
    open_opportunities: int = 0
    total_pipeline_value: Decimal = Decimal("0")
    expected_revenue_this_month: Decimal = Decimal("0")
    currency: str = "USD"
    recent_opportunities: list[dict] = []
