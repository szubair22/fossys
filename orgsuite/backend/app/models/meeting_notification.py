"""
Meeting notification model.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.user import User


class NotificationType(str, enum.Enum):
    """Notification type."""
    INVITATION = "invitation"
    REMINDER = "reminder"
    UPDATE = "update"
    CANCELLED = "cancelled"
    MINUTES_READY = "minutes_ready"


class NotificationStatus(str, enum.Enum):
    """Notification status."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class DeliveryMethod(str, enum.Enum):
    """Notification delivery method."""
    EMAIL = "email"
    IN_APP = "in_app"
    BOTH = "both"


class MeetingNotification(BaseModel):
    """Meeting notification record."""
    __tablename__ = "meeting_notifications"

    meeting_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    recipient_user_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=NotificationStatus.PENDING,
        index=True
    )

    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Notification metadata (JSON) - renamed from 'metadata' which is reserved in SQLAlchemy
    notification_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Email content
    email_subject: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    email_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    include_ics: Mapped[bool] = mapped_column(Boolean, default=True)

    delivery_method: Mapped[Optional[DeliveryMethod]] = mapped_column(
        Enum(DeliveryMethod, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        default=DeliveryMethod.BOTH
    )

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="notifications"
    )
    recipient_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[recipient_user_id]
    )

    def __repr__(self) -> str:
        return f"<MeetingNotification {self.notification_type} to {self.recipient_user_id}>"
