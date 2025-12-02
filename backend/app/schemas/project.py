"""
Pydantic schemas for Project endpoints.
"""
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Create a new project."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    status: str = Field(default="planned")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    committee_id: Optional[str] = None


class ProjectUpdate(BaseModel):
    """Update a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    committee_id: Optional[str] = None


class ProjectResponse(BaseModel):
    """Project response."""
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    committee_id: Optional[str] = None
    owner_id: Optional[str] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Paginated list of projects."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[ProjectResponse]
