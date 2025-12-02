"""
Contract and ContractLine schemas for ASC 606 revenue recognition.

Provides Pydantic models for:
- Contract CRUD operations
- ContractLine CRUD operations
- Nested contract creation with lines
"""
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum


class ContractStatus(str, Enum):
    """Status of a contract."""
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class RecognitionPattern(str, Enum):
    """Revenue recognition pattern types."""
    POINT_IN_TIME = "point_in_time"
    STRAIGHT_LINE = "straight_line"


class ContractLineStatus(str, Enum):
    """Status of a contract line."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ============================================================================
# CONTRACT LINE SCHEMAS
# ============================================================================

class ContractLineBase(BaseModel):
    """Base schema for contract line fields."""
    description: str = Field(..., min_length=1, max_length=500)
    product_type: str = Field("service", max_length=50)
    recognition_pattern: RecognitionPattern = Field(default=RecognitionPattern.STRAIGHT_LINE)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    quantity: Decimal = Field(default=Decimal("1"), ge=0)
    unit_price: Decimal = Field(..., ge=0)
    ssp_amount: Decimal = Field(..., ge=0)
    revenue_account_id: Optional[str] = Field(None, max_length=15)
    deferred_revenue_account_id: Optional[str] = Field(None, max_length=15)
    sort_order: int = Field(default=0)


class ContractLineCreate(ContractLineBase):
    """Schema for creating a contract line."""
    pass


class ContractLineUpdate(BaseModel):
    """Schema for updating a contract line."""
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    product_type: Optional[str] = Field(None, max_length=50)
    recognition_pattern: Optional[RecognitionPattern] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    ssp_amount: Optional[Decimal] = Field(None, ge=0)
    revenue_account_id: Optional[str] = Field(None, max_length=15)
    deferred_revenue_account_id: Optional[str] = Field(None, max_length=15)
    status: Optional[ContractLineStatus] = None
    sort_order: Optional[int] = None


class ContractLineResponse(ContractLineBase):
    """Schema for contract line response."""
    id: str
    contract_id: str
    allocated_transaction_price: Optional[Decimal] = None
    status: ContractLineStatus
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


# ============================================================================
# CONTRACT SCHEMAS
# ============================================================================

class ContractBase(BaseModel):
    """Base schema for contract fields."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    contract_number: Optional[str] = Field(None, max_length=50)
    customer_contact_id: Optional[str] = Field(None, max_length=15)
    member_id: Optional[str] = Field(None, max_length=15)
    project_id: Optional[str] = Field(None, max_length=15)
    start_date: date
    end_date: Optional[date] = None
    total_transaction_price: Decimal = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    notes: Optional[str] = Field(None, max_length=5000)


class ContractCreate(ContractBase):
    """Schema for creating a contract with optional nested lines."""
    organization_id: str = Field(..., min_length=1, max_length=15)
    status: ContractStatus = Field(default=ContractStatus.DRAFT)
    lines: Optional[List[ContractLineCreate]] = Field(default=None)


class ContractUpdate(BaseModel):
    """Schema for updating a contract."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    contract_number: Optional[str] = Field(None, max_length=50)
    customer_contact_id: Optional[str] = Field(None, max_length=15)
    member_id: Optional[str] = Field(None, max_length=15)
    project_id: Optional[str] = Field(None, max_length=15)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_transaction_price: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    status: Optional[ContractStatus] = None
    notes: Optional[str] = Field(None, max_length=5000)


class ContractResponse(ContractBase):
    """Schema for contract response."""
    id: str
    organization_id: str
    status: ContractStatus
    created_by_id: Optional[str] = None
    created: datetime
    updated: datetime
    # Include customer name from relationship
    customer_name: Optional[str] = None
    # Include lines in response
    lines: List[ContractLineResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ContractListResponse(BaseModel):
    """Schema for listing contracts."""
    items: List[ContractResponse]
    total: int


class ContractSummary(BaseModel):
    """Summary view of a contract (for lists without nested lines)."""
    id: str
    organization_id: str
    contract_number: Optional[str] = None
    name: str
    customer_name: Optional[str] = None
    status: ContractStatus
    start_date: date
    end_date: Optional[date] = None
    total_transaction_price: Decimal
    currency: str
    lines_count: int = 0
    created: datetime

    class Config:
        from_attributes = True


class ContractListSummaryResponse(BaseModel):
    """Schema for listing contract summaries."""
    items: List[ContractSummary]
    total: int


# ============================================================================
# CONTRACT LINE ADD/REMOVE SCHEMAS
# ============================================================================

class ContractLineAddRequest(BaseModel):
    """Schema for adding a line to an existing contract."""
    contract_id: str = Field(..., min_length=1, max_length=15)
    line: ContractLineCreate


class ContractLinesAddRequest(BaseModel):
    """Schema for adding multiple lines to an existing contract."""
    contract_id: str = Field(..., min_length=1, max_length=15)
    lines: List[ContractLineCreate]


# ============================================================================
# CONTRACT ACTIVATION SCHEMA
# ============================================================================

class ContractActivateRequest(BaseModel):
    """Request to activate a contract (triggers allocation and schedule generation)."""
    generate_schedules: bool = Field(
        default=True,
        description="Whether to generate revenue schedules for lines"
    )


class ContractActivateResponse(BaseModel):
    """Response from activating a contract."""
    contract_id: str
    status: ContractStatus
    lines_allocated: int
    schedules_generated: int
    message: str
