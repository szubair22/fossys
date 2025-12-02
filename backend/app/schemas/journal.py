"""
Pydantic schemas for Journal Entry endpoints.
"""
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator


class JournalLineCreate(BaseModel):
    """Create a journal line."""
    account_id: str
    debit: Optional[Decimal] = Field(default=Decimal(0), ge=0)
    credit: Optional[Decimal] = Field(default=Decimal(0), ge=0)
    description: Optional[str] = Field(None, max_length=500)
    # Dimension placeholders
    department_id: Optional[str] = None
    project_id: Optional[str] = None
    class_id: Optional[str] = None
    location_id: Optional[str] = None
    custom_dimensions: Optional[dict] = None

    @model_validator(mode='after')
    def validate_debit_or_credit(self):
        """Ensure either debit or credit is set, not both."""
        if self.debit and self.debit > 0 and self.credit and self.credit > 0:
            raise ValueError("A journal line cannot have both debit and credit")
        if (not self.debit or self.debit == 0) and (not self.credit or self.credit == 0):
            raise ValueError("A journal line must have either debit or credit")
        return self


class JournalLineResponse(BaseModel):
    """Journal line response."""
    id: str
    journal_entry_id: str
    line_number: int
    account_id: str
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None
    description: Optional[str] = None
    department_id: Optional[str] = None
    project_id: Optional[str] = None
    class_id: Optional[str] = None
    location_id: Optional[str] = None
    custom_dimensions: Optional[dict] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class JournalEntryCreate(BaseModel):
    """Create a journal entry."""
    entry_date: date
    description: str = Field(..., min_length=1, max_length=500)
    notes: Optional[str] = None
    reference: Optional[str] = Field(None, max_length=100)
    source_type: Optional[str] = Field(None, max_length=50)
    source_id: Optional[str] = None
    lines: list[JournalLineCreate] = Field(..., min_length=2)  # At least 2 lines required

    @model_validator(mode='after')
    def validate_balanced(self):
        """Ensure total debits equal total credits."""
        total_debits = sum(line.debit or Decimal(0) for line in self.lines)
        total_credits = sum(line.credit or Decimal(0) for line in self.lines)
        if abs(total_debits - total_credits) > Decimal('0.01'):
            raise ValueError(
                f"Journal entry is not balanced. "
                f"Debits: {total_debits}, Credits: {total_credits}"
            )
        return self


class JournalEntryUpdate(BaseModel):
    """Update a journal entry (only allowed for draft entries)."""
    entry_date: Optional[date] = None
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    notes: Optional[str] = None
    reference: Optional[str] = Field(None, max_length=100)


class JournalEntryResponse(BaseModel):
    """Journal entry response."""
    id: str
    organization_id: str
    entry_number: Optional[str] = None
    entry_date: date
    description: str
    notes: Optional[str] = None
    reference: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    status: str
    posted_at: Optional[date] = None
    posted_by_id: Optional[str] = None
    voided_at: Optional[date] = None
    voided_by_id: Optional[str] = None
    void_reason: Optional[str] = None
    created_by_id: str
    total_debits: Optional[Decimal] = None
    total_credits: Optional[Decimal] = None
    lines: list[JournalLineResponse] = []
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class JournalEntryListResponse(BaseModel):
    """Paginated list of journal entries."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[JournalEntryResponse]


class PostJournalEntryRequest(BaseModel):
    """Request to post a journal entry."""
    pass  # No additional data needed


class VoidJournalEntryRequest(BaseModel):
    """Request to void a journal entry."""
    reason: str = Field(..., min_length=1, max_length=500)
