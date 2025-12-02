"""Recording schemas (PocketBase-compatible)."""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class RecordingCreate(BaseModel):
    meeting: str = Field(..., min_length=1, max_length=15)
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    provider: Optional[str] = None
    url: Optional[str] = None
    visibility: Optional[str] = None


class RecordingUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    provider: Optional[str] = None
    url: Optional[str] = None
    visibility: Optional[str] = None
    status: Optional[str] = None


class RecordingResponse(BaseModel):
    id: str
    meeting: str
    title: str
    description: Optional[str] = None
    provider: Optional[str] = None
    url: Optional[str] = None
    file: Optional[str] = None
    thumbnail: Optional[str] = None
    recording_date: Optional[datetime] = None
    duration_seconds: Optional[int] = 0
    file_size: Optional[int] = 0
    status: str
    visibility: Optional[str] = None
    created_by: str
    created: datetime
    updated: datetime
    collectionId: str = "recordings"
    collectionName: str = "recordings"
    expand: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True
