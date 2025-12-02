"""Meeting Notification schemas (PocketBase-compatible)."""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MeetingNotificationCreate(BaseModel):
    meeting: str = Field(..., min_length=1, max_length=15)
    recipient_user: str = Field(..., min_length=1, max_length=15)
    notification_type: str
    status: Optional[str] = "pending"
    scheduled_at: Optional[datetime] = None
    delivery_method: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    include_ics: Optional[bool] = True
    notification_metadata: Optional[dict] = None


class MeetingNotificationUpdate(BaseModel):
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    include_ics: Optional[bool] = None
    delivery_method: Optional[str] = None
    notification_metadata: Optional[dict] = None


class MeetingNotificationResponse(BaseModel):
    id: str
    meeting: str
    recipient_user: str
    notification_type: str
    status: str
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    include_ics: bool = True
    delivery_method: Optional[str] = None
    notification_metadata: Optional[dict] = None
    created: datetime
    updated: datetime
    collectionId: str = "meeting_notifications"
    collectionName: str = "meeting_notifications"
    expand: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True
