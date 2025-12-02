"""
Organization schemas.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class OrganizationCreate(BaseModel):
    """Create organization request."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class OrganizationUpdate(BaseModel):
    """Update organization request."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    settings: Optional[dict] = None


class OrganizationResponse(BaseModel):
    """Organization response - matches PocketBase record format."""
    id: str
    name: str
    description: Optional[str] = None
    logo: Optional[str] = None
    settings: Optional[dict] = None
    owner: str  # Owner user ID
    created: datetime
    updated: datetime
    collectionId: str = "organizations"
    collectionName: str = "organizations"

    # Expansion fields
    expand: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class OrganizationListResponse(BaseModel):
    """Paginated organization list - matches PocketBase format."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[OrganizationResponse]


class OrgMembershipCreate(BaseModel):
    """Create organization membership request."""
    user: str  # User ID
    role: str = "member"


class OrgMembershipResponse(BaseModel):
    """Organization membership response."""
    id: str
    organization: str
    user: str
    role: str
    is_active: bool = True
    invited_by: Optional[str] = None
    invited_at: Optional[datetime] = None
    joined_at: Optional[datetime] = None
    permissions: Optional[dict] = None
    created: datetime
    updated: datetime
    collectionId: str = "org_memberships"
    collectionName: str = "org_memberships"

    expand: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True
