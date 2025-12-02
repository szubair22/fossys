"""
Motion schemas.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MotionCreate(BaseModel):
    """Create motion request."""
    meeting: str  # Meeting ID
    agenda_item: Optional[str] = None  # Agenda Item ID
    title: str = Field(..., min_length=1, max_length=500)
    text: str = Field(..., min_length=1)
    reason: Optional[str] = None
    category: Optional[str] = None
    number: Optional[str] = None


class MotionUpdate(BaseModel):
    """Update motion request."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    text: Optional[str] = None
    reason: Optional[str] = None
    category: Optional[str] = None
    workflow_state: Optional[str] = None
    vote_result: Optional[dict] = None
    final_notes: Optional[str] = None


class MotionResponse(BaseModel):
    """Motion response - matches PocketBase record format."""
    id: str
    meeting: str  # Meeting ID
    agenda_item: Optional[str] = None  # Agenda Item ID
    number: Optional[str] = None
    title: str
    text: str
    reason: Optional[str] = None
    submitter: str  # User ID
    supporters: list[str] = []  # List of user IDs
    workflow_state: str = "draft"
    category: Optional[str] = None
    vote_result: Optional[dict] = None
    final_notes: Optional[str] = None
    attachments: Optional[list] = None
    created: datetime
    updated: datetime
    collectionId: str = "motions"
    collectionName: str = "motions"

    expand: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True
