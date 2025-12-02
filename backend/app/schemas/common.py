"""
Common schemas used across the application.
"""
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel
from datetime import datetime

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response - matches PocketBase format."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[T]


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


class HealthResponse(BaseModel):
    """Health check response - matches PocketBase /api/health format."""
    code: int = 200
    message: str = "API is healthy."


class BaseResponse(BaseModel):
    """Base response with common fields."""
    id: str
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class ExpandedUser(BaseModel):
    """Minimal user info for expansion in responses."""
    id: str
    email: str
    name: str
    display_name: Optional[str] = None

    class Config:
        from_attributes = True
