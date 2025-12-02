"""
Meeting model.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.committee import Committee
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.participant import Participant
    from app.models.agenda_item import AgendaItem
    from app.models.motion import Motion
    from app.models.poll import Poll
    from app.models.chat_message import ChatMessage
    from app.models.meeting_minutes import MeetingMinutes
    from app.models.meeting_notification import MeetingNotification
    from app.models.file import File
    from app.models.recording import Recording


class MeetingStatus(str, enum.Enum):
    """Meeting status values."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MeetingType(str, enum.Enum):
    """Meeting type values."""
    GENERAL = "general"
    BOARD = "board"
    COMMITTEE = "committee"
    ELECTION = "election"
    SPECIAL = "special"
    EMERGENCY = "emergency"
    ANNUAL = "annual"


class Meeting(BaseModel):
    """Meeting model."""
    __tablename__ = "meetings"

    # Optional direct organization linkage (may be NULL for legacy records using committee only)
    organization_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Optional committee relationship
    committee_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("committees.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=MeetingStatus.SCHEDULED,
        index=True
    )

    # Video conferencing
    jitsi_room: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Settings (JSON)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Creator
    created_by_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Meeting type
    meeting_type: Mapped[Optional[MeetingType]] = mapped_column(
        Enum(MeetingType, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        default=MeetingType.GENERAL
    )

    # Governance
    quorum_required: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    quorum_met: Mapped[bool] = mapped_column(Boolean, default=False)
    minutes_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    committee: Mapped[Optional["Committee"]] = relationship(
        "Committee",
        back_populates="meetings"
    )
    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    participants: Mapped[list["Participant"]] = relationship(
        "Participant",
        back_populates="meeting",
        cascade="all, delete-orphan"
    )
    agenda_items: Mapped[list["AgendaItem"]] = relationship(
        "AgendaItem",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="AgendaItem.order"
    )
    motions: Mapped[list["Motion"]] = relationship(
        "Motion",
        back_populates="meeting",
        cascade="all, delete-orphan"
    )
    polls: Mapped[list["Poll"]] = relationship(
        "Poll",
        back_populates="meeting",
        cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="meeting",
        cascade="all, delete-orphan"
    )
    minutes: Mapped[Optional["MeetingMinutes"]] = relationship(
        "MeetingMinutes",
        back_populates="meeting",
        uselist=False,
        cascade="all, delete-orphan"
    )
    notifications: Mapped[list["MeetingNotification"]] = relationship(
        "MeetingNotification",
        back_populates="meeting",
        cascade="all, delete-orphan"
    )
    files: Mapped[list["File"]] = relationship(
        "File",
        back_populates="meeting",
        cascade="all, delete-orphan"
    )
    recordings: Mapped[list["Recording"]] = relationship(
        "Recording",
        back_populates="meeting",
        cascade="all, delete-orphan"
    )

    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization",
        back_populates="meetings"
    )

    def __repr__(self) -> str:
        return f"<Meeting {self.title}>"
