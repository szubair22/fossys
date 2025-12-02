"""
Organization v1 schemas - new format for OrgSuite API.

These schemas follow the same patterns as membership and finance modules,
without the PocketBase-compatible fields (collectionId, collectionName).
"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class OrganizationV1Create(BaseModel):
    """Create organization request."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    settings: Optional[dict] = None


class OrganizationV1Update(BaseModel):
    """Update organization request."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    settings: Optional[dict] = None
    logo: Optional[str] = None


class OrganizationV1Response(BaseModel):
    """Organization response - v1 API format."""
    id: str
    name: str
    description: Optional[str] = None
    logo: Optional[str] = None
    settings: Optional[dict] = None
    owner_id: str
    created: datetime
    updated: datetime

    # User's role in this organization (populated dynamically)
    user_role: Optional[str] = None

    class Config:
        from_attributes = True


class OrganizationV1ListResponse(BaseModel):
    """Paginated organization list - v1 API format."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[OrganizationV1Response]
