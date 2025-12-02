"""
Pydantic schemas for Donation endpoints.
"""
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, EmailStr


class DonationCreate(BaseModel):
    """Create a new donation."""
    # Donor identification - one of member_id, contact_id, or donor_name
    member_id: Optional[str] = None
    contact_id: Optional[str] = None
    donor_name: Optional[str] = Field(None, max_length=200)
    donor_email: Optional[EmailStr] = None

    # Amount
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)

    # Date
    donation_date: date

    # Payment details
    payment_method: Optional[str] = None  # cash, check, credit_card, bank_transfer, paypal, venmo, other
    payment_reference: Optional[str] = Field(None, max_length=100)

    # Status
    status: str = Field(default="pending")  # pledged, pending, received, cancelled, refunded

    # Purpose/campaign
    purpose: Optional[str] = Field(None, max_length=200)
    campaign: Optional[str] = Field(None, max_length=200)

    # Tax receipt
    is_tax_deductible: bool = True
    receipt_number: Optional[str] = Field(None, max_length=50)
    receipt_sent: bool = False

    # Notes
    notes: Optional[str] = None


class DonationUpdate(BaseModel):
    """Update a donation."""
    member_id: Optional[str] = None
    contact_id: Optional[str] = None
    donor_name: Optional[str] = Field(None, max_length=200)
    donor_email: Optional[EmailStr] = None
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    currency: Optional[str] = Field(None, max_length=3)
    donation_date: Optional[date] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None
    purpose: Optional[str] = Field(None, max_length=200)
    campaign: Optional[str] = Field(None, max_length=200)
    is_tax_deductible: Optional[bool] = None
    receipt_number: Optional[str] = Field(None, max_length=50)
    receipt_sent: Optional[bool] = None
    notes: Optional[str] = None


class DonorInfo(BaseModel):
    """Embedded donor information for response."""
    id: Optional[str] = None
    name: str
    email: Optional[str] = None
    type: str  # "member", "contact", or "anonymous"


class DonationResponse(BaseModel):
    """Donation response."""
    id: str
    organization_id: str

    # Donor IDs
    member_id: Optional[str] = None
    contact_id: Optional[str] = None
    donor_name: Optional[str] = None
    donor_email: Optional[str] = None

    # Resolved donor info
    donor: Optional[DonorInfo] = None

    # Amount
    amount: Decimal
    currency: str

    # Date
    donation_date: date

    # Payment details
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None

    # Status
    status: str

    # Purpose/campaign
    purpose: Optional[str] = None
    campaign: Optional[str] = None

    # Tax receipt
    is_tax_deductible: bool = True
    receipt_number: Optional[str] = None
    receipt_sent: bool = False

    # Notes
    notes: Optional[str] = None

    # Audit
    created_by_id: Optional[str] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class DonationListResponse(BaseModel):
    """Paginated list of donations."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[DonationResponse]


class DonationSummary(BaseModel):
    """Summary statistics for donations."""
    total_received: Decimal
    total_pending: Decimal
    total_pledged: Decimal
    count_received: int
    count_pending: int
    count_pledged: int
    currency: str = "USD"
