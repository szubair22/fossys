"""
Organization membership schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


class OrgMembershipCreate(BaseModel):
    """Schema for creating an organization membership."""
    organization_id: str = Field(..., description="Organization ID")
    user_id: Optional[str] = Field(None, description="User ID (if known)")
    user_email: Optional[str] = Field(None, description="User email (for lookup)")
    role: str = Field("member", description="Role: owner, admin, member, viewer")
    permissions: Optional[dict] = None


class OrgMembershipUpdate(BaseModel):
    """Schema for updating an organization membership."""
    role: Optional[str] = None
    is_active: Optional[bool] = None
    permissions: Optional[dict] = None


class UserInfo(BaseModel):
    """Embedded user info for membership response."""
    id: str
    email: str
    name: Optional[str] = None
    avatar: Optional[str] = None

    class Config:
        from_attributes = True


class OrganizationInfo(BaseModel):
    """Embedded organization info for membership response."""
    id: str
    name: str
    description: Optional[str] = None
    logo: Optional[str] = None

    class Config:
        from_attributes = True


class OrgMembershipResponse(BaseModel):
    """Schema for organization membership response."""
    id: str
    organization_id: str
    user_id: str
    role: str
    is_active: bool
    invited_by_id: Optional[str] = None
    invited_at: Optional[datetime] = None
    joined_at: Optional[datetime] = None
    permissions: Optional[dict] = None
    created: datetime
    updated: datetime
    # Expanded relations
    user: Optional[UserInfo] = None
    organization: Optional[OrganizationInfo] = None

    class Config:
        from_attributes = True


class OrgMembershipListResponse(BaseModel):
    """Schema for paginated organization membership list response."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: List[OrgMembershipResponse]


class AddMemberByEmailRequest(BaseModel):
    """Schema for adding a member by email."""
    email: EmailStr = Field(..., description="Email of user to add")
    role: str = Field("member", description="Role to assign")
