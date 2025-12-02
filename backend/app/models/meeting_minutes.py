"""
Meeting minutes model.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, Enum, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.user import User


class MinutesStatus(str, enum.Enum):
    """Minutes status."""
    DRAFT = "draft"
    FINAL = "final"
    APPROVED = "approved"


class MeetingMinutes(BaseModel):
    """Meeting minutes document."""
    __tablename__ = "meeting_minutes"
    __table_args__ = (
        UniqueConstraint("meeting_id", name="uq_meeting_minutes_meeting"),
    )

    meeting_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # Content
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Structured data
    decisions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    attendance_snapshot: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Generation info
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    generated_by_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    status: Mapped[MinutesStatus] = mapped_column(
        Enum(MinutesStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=MinutesStatus.DRAFT
    )

    # Approval info
    approved_by_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="minutes"
    )
    generated_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[generated_by_id]
    )
    approved_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by_id]
    )

    def __repr__(self) -> str:
        return f"<MeetingMinutes for meeting {self.meeting_id}>"
