"""
Pydantic schemas for Chart of Accounts endpoints.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    """Create a new account."""
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    account_type: str = Field(...)  # asset, liability, equity, income, expense
    account_subtype: Optional[str] = None
    parent_id: Optional[str] = None
    display_order: int = 0
    is_active: bool = True


class AccountUpdate(BaseModel):
    """Update an account."""
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    account_type: Optional[str] = None
    account_subtype: Optional[str] = None
    parent_id: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class AccountResponse(BaseModel):
    """Account response."""
    id: str
    organization_id: str
    code: str
    name: str
    description: Optional[str] = None
    account_type: str
    account_subtype: Optional[str] = None
    parent_id: Optional[str] = None
    display_order: int = 0
    is_active: bool = True
    is_system: bool = False
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class AccountListResponse(BaseModel):
    """Paginated list of accounts."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[AccountResponse]
