"""
File schemas (PocketBase-compatible response shapes).
"""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class FileCreate(BaseModel):
    """Create file request (metadata + upload)."""
    organization: str = Field(..., min_length=1, max_length=15)
    meeting: Optional[str] = Field(None, min_length=1, max_length=15)
    agenda_item: Optional[str] = Field(None, min_length=1, max_length=15)
    motion: Optional[str] = Field(None, min_length=1, max_length=15)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    file_type: Optional[str] = None  # enum value


class FileUpdate(BaseModel):
    """Update file metadata request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    file_type: Optional[str] = None


class FileResponse(BaseModel):
    """File metadata response - PocketBase-like fields."""
    id: str
    name: str
    description: Optional[str] = None
    file_type: Optional[str] = None
    file_size: int | None = 0
    file: str  # stored path
    organization: str
    meeting: Optional[str] = None
    agenda_item: Optional[str] = None
    motion: Optional[str] = None
    uploaded_by: str
    created: datetime
    updated: datetime
    collectionId: str = "files"
    collectionName: str = "files"
    expand: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True
