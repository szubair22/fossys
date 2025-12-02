"""
Meeting minutes schemas.
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class MeetingMinutesCreate(BaseModel):
    """Schema for creating meeting minutes."""
    meeting_id: str = Field(..., description="Meeting ID")
    content: Optional[str] = None
    summary: Optional[str] = None
    decisions: Optional[List[dict]] = None
    attendance_snapshot: Optional[List[dict]] = None
    status: str = "draft"


class MeetingMinutesUpdate(BaseModel):
    """Schema for updating meeting minutes."""
    content: Optional[str] = None
    summary: Optional[str] = None
    decisions: Optional[List[dict]] = None
    attendance_snapshot: Optional[List[dict]] = None
    status: Optional[str] = None


class MeetingMinutesResponse(BaseModel):
    """Schema for meeting minutes response."""
    id: str
    meeting_id: str
    content: Optional[str] = None
    summary: Optional[str] = None
    decisions: Optional[List[dict]] = None
    attendance_snapshot: Optional[List[dict]] = None
    generated_at: Optional[datetime] = None
    generated_by_id: Optional[str] = None
    status: str
    approved_by_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class MeetingMinutesListResponse(BaseModel):
    """Schema for paginated meeting minutes list response."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: List[MeetingMinutesResponse]
