"""
Poll and vote schemas.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PollCreate(BaseModel):
    """Create poll request."""
    meeting: str  # Meeting ID
    motion: Optional[str] = None  # Motion ID
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    poll_type: str = "yes_no"
    options: Optional[list] = None
    anonymous: bool = False


class PollUpdate(BaseModel):
    """Update poll request."""
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    status: Optional[str] = None
    results: Optional[dict] = None
    poll_category: Optional[str] = None
    winning_option: Optional[str] = None


class PollResponse(BaseModel):
    """Poll response - matches PocketBase record format."""
    id: str
    meeting: str  # Meeting ID
    motion: Optional[str] = None  # Motion ID
    title: str
    description: Optional[str] = None
    poll_type: str = "yes_no"
    options: Optional[list] = None
    status: str = "draft"
    results: Optional[dict] = None
    anonymous: bool = False
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_by: str  # User ID
    poll_category: Optional[str] = None
    winning_option: Optional[str] = None
    created: datetime
    updated: datetime
    collectionId: str = "polls"
    collectionName: str = "polls"

    expand: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class VoteCreate(BaseModel):
    """Create vote request."""
    poll: str  # Poll ID
    value: dict  # Vote value (JSON)


class VoteResponse(BaseModel):
    """Vote response - matches PocketBase record format."""
    id: str
    poll: str  # Poll ID
    user: str  # User ID
    value: dict
    weight: int = 1
    delegated_from: Optional[str] = None  # User ID
    created: datetime
    updated: datetime
    collectionId: str = "votes"
    collectionName: str = "votes"

    class Config:
        from_attributes = True
