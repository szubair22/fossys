"""
Meeting template schemas.
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class MeetingTemplateCreate(BaseModel):
    """Schema for creating a meeting template."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    org_type: Optional[str] = None
    default_meeting_title: Optional[str] = None
    default_meeting_type: Optional[str] = None
    default_agenda: Optional[List[dict]] = None
    settings: Optional[dict] = None
    is_global: bool = False


class MeetingTemplateUpdate(BaseModel):
    """Schema for updating a meeting template."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    org_type: Optional[str] = None
    default_meeting_title: Optional[str] = None
    default_meeting_type: Optional[str] = None
    default_agenda: Optional[List[dict]] = None
    settings: Optional[dict] = None
    is_global: Optional[bool] = None


class MeetingTemplateResponse(BaseModel):
    """Schema for meeting template response."""
    id: str
    organization_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    org_type: Optional[str] = None
    default_meeting_title: Optional[str] = None
    default_meeting_type: Optional[str] = None
    default_agenda: Optional[List[dict]] = None
    settings: Optional[dict] = None
    is_global: bool = False
    created_by_id: Optional[str] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class MeetingTemplateListResponse(BaseModel):
    """Schema for paginated meeting template list response."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: List[MeetingTemplateResponse]
