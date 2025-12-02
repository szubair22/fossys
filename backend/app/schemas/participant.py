"""
Participant schemas.
"""
from typing import Optional, Any
from pydantic import BaseModel
from datetime import datetime


class ParticipantCreate(BaseModel):
    """Create participant request."""
    meeting: str  # Meeting ID
    user: str  # User ID
    role: str = "member"
    can_vote: bool = True
    vote_weight: int = 1


class ParticipantUpdate(BaseModel):
    """Update participant request."""
    role: Optional[str] = None
    is_present: Optional[bool] = None
    attendance_status: Optional[str] = None
    can_vote: Optional[bool] = None
    vote_weight: Optional[int] = None


class ParticipantResponse(BaseModel):
    """Participant response - matches PocketBase record format."""
    id: str
    meeting: str  # Meeting ID
    user: str  # User ID
    role: str
    is_present: bool = False
    attendance_status: Optional[str] = "invited"
    can_vote: bool = True
    vote_weight: int = 1
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None
    created: datetime
    updated: datetime
    collectionId: str = "participants"
    collectionName: str = "participants"

    expand: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True
