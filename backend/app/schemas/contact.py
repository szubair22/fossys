"""
Pydantic schemas for Contact endpoints.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class ContactCreate(BaseModel):
    """Create a new contact."""
    # Accept either 'name' or 'first_name'/'last_name' - frontend uses the latter
    name: Optional[str] = Field(None, max_length=200)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    company: Optional[str] = Field(None, max_length=200)
    company_name: Optional[str] = Field(None, max_length=200)  # Alias for frontend compatibility
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    contact_type: str = Field(default="other")
    is_active: bool = True
    tax_id: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None

    def get_full_name(self) -> str:
        """Get the full name from either name or first_name/last_name."""
        if self.name:
            return self.name
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) or "Unknown"

    def get_company(self) -> Optional[str]:
        """Get company from either company or company_name."""
        return self.company or self.company_name


class ContactUpdate(BaseModel):
    """Update a contact."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    company: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    contact_type: Optional[str] = None
    is_active: Optional[bool] = None
    tax_id: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class ContactResponse(BaseModel):
    """Contact response."""
    id: str
    organization_id: str
    name: str
    # Include both field names for frontend compatibility
    company: Optional[str] = None
    company_name: Optional[str] = None  # Alias for frontend
    first_name: Optional[str] = None  # Parsed from name for frontend
    last_name: Optional[str] = None  # Parsed from name for frontend
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    contact_type: str
    is_active: bool = True
    tax_id: Optional[str] = None
    notes: Optional[str] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    """Paginated list of contacts."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[ContactResponse]
