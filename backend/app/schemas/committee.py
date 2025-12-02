"""
Committee schemas.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class CommitteeCreate(BaseModel):
    """Create committee request."""
    organization: str  # Organization ID
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class CommitteeUpdate(BaseModel):
    """Update committee request."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None


class CommitteeResponse(BaseModel):
    """Committee response - matches PocketBase record format."""
    id: str
    organization: str  # Organization ID
    name: str
    description: Optional[str] = None
    admins: list[str] = []  # List of user IDs
    created: datetime
    updated: datetime
    collectionId: str = "committees"
    collectionName: str = "committees"

    expand: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True
