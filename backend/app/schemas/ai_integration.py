"""AI Integration schemas (PocketBase-compatible)."""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AIIntegrationCreate(BaseModel):
    organization: str = Field(..., min_length=1, max_length=15)
    provider: str
    api_key: str
    model: Optional[str] = None
    is_active: bool = True
    settings: Optional[dict] = None


class AIIntegrationUpdate(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[dict] = None
    last_used_at: Optional[datetime] = None
    usage_count: Optional[int] = None


class AIIntegrationResponse(BaseModel):
    id: str
    organization: str
    provider: str
    model: Optional[str] = None
    is_active: bool
    settings: Optional[dict] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    created_by: str
    created: datetime
    updated: datetime
    # Do not expose api_key directly for security (PB may have but we omit)
    collectionId: str = "ai_integrations"
    collectionName: str = "ai_integrations"
    expand: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True
