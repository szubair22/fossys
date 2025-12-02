"""
Meeting schemas.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MeetingCreate(BaseModel):
    """Create meeting request."""
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "scheduled"
    meeting_type: Optional[str] = "general"
    committee: Optional[str] = None  # Committee ID (optional)
    organization: Optional[str] = None  # Direct organization ID if not using committee
    quorum_required: Optional[int] = 0
    settings: Optional[dict] = None


class MeetingUpdate(BaseModel):
    """Update meeting request."""
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    meeting_type: Optional[str] = None
    quorum_required: Optional[int] = None
    quorum_met: Optional[bool] = None
    settings: Optional[dict] = None


class MeetingResponse(BaseModel):
    """Meeting response - matches PocketBase record format."""
    id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    jitsi_room: Optional[str] = None
    settings: Optional[dict] = None
    created_by: str  # User ID
    committee: Optional[str] = None  # Committee ID
    organization: Optional[str] = None  # Direct organization ID
    meeting_type: Optional[str] = "general"
    quorum_required: Optional[int] = 0
    quorum_met: bool = False
    minutes_generated: bool = False
    created: datetime
    updated: datetime
    collectionId: str = "meetings"
    collectionName: str = "meetings"

    expand: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class MeetingListResponse(BaseModel):
    """Paginated meeting list - matches PocketBase format."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[MeetingResponse]
