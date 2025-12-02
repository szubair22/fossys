"""
Pydantic schemas for Member endpoints.
"""
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, EmailStr


class MemberCreate(BaseModel):
    """Create a new member."""
    name: str = Field(..., min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    status: str = Field(default="pending")
    member_type: Optional[str] = Field(default="regular")
    join_date: Optional[date] = None
    expiry_date: Optional[date] = None
    is_public: bool = False
    notes: Optional[str] = None
    member_number: Optional[str] = Field(None, max_length=50)
    user_id: Optional[str] = None  # Optional link to system user


class MemberUpdate(BaseModel):
    """Update a member."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None
    member_type: Optional[str] = None
    join_date: Optional[date] = None
    expiry_date: Optional[date] = None
    is_public: Optional[bool] = None
    notes: Optional[str] = None
    member_number: Optional[str] = Field(None, max_length=50)
    user_id: Optional[str] = None


class MemberResponse(BaseModel):
    """Member response."""
    id: str
    organization_id: str
    user_id: Optional[str] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    status: str
    member_type: Optional[str] = None
    join_date: Optional[date] = None
    expiry_date: Optional[date] = None
    is_public: bool = False
    notes: Optional[str] = None
    member_number: Optional[str] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class MemberListResponse(BaseModel):
    """Paginated list of members."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[MemberResponse]
