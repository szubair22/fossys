"""
Agenda item schemas.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AgendaItemCreate(BaseModel):
    """Create agenda item request."""
    meeting: str  # Meeting ID
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    order: int = 0
    duration_minutes: Optional[int] = 0
    item_type: str = "topic"
    status: str = "pending"


class AgendaItemUpdate(BaseModel):
    """Update agenda item request."""
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    order: Optional[int] = None
    duration_minutes: Optional[int] = None
    item_type: Optional[str] = None
    status: Optional[str] = None


class AgendaItemResponse(BaseModel):
    """Agenda item response - matches PocketBase record format."""
    id: str
    meeting: str  # Meeting ID
    title: str
    description: Optional[str] = None
    order: int = 0
    duration_minutes: Optional[int] = 0
    item_type: str = "topic"
    status: str = "pending"
    created: datetime
    updated: datetime
    collectionId: str = "agenda_items"
    collectionName: str = "agenda_items"

    expand: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True
