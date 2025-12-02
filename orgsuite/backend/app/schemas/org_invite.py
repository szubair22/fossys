"""
Organization invite schemas.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr


class OrgInviteCreate(BaseModel):
    """Create an organization invite."""
    organization_id: str
    email: EmailStr
    role: str = "member"  # admin, member, viewer
    message: Optional[str] = None


class OrgInviteResponse(BaseModel):
    """Organization invite response."""
    id: str
    organization_id: str
    organization_name: Optional[str] = None
    email: str
    role: str
    token: str
    status: str
    expires_at: datetime
    invited_by_id: str
    invited_by_name: Optional[str] = None
    accepted_by_id: Optional[str] = None
    accepted_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    message: Optional[str] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class OrgInviteListResponse(BaseModel):
    """Paginated list of organization invites."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: List[OrgInviteResponse]


class OrgInviteAccept(BaseModel):
    """Accept an organization invite."""
    token: str


class OrgInviteAcceptResponse(BaseModel):
    """Response after accepting an invite."""
    success: bool
    organization_id: str
    organization_name: str
    role: str
    message: str
