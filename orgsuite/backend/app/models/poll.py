"""
Poll model.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.motion import Motion
    from app.models.meeting import Meeting
    from app.models.user import User
    from app.models.vote import Vote


class PollType(str, enum.Enum):
    """Poll type."""
    YES_NO = "yes_no"
    YES_NO_ABSTAIN = "yes_no_abstain"
    MULTIPLE_CHOICE = "multiple_choice"
    RANKED_CHOICE = "ranked_choice"


class PollStatus(str, enum.Enum):
    """Poll status."""
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    PUBLISHED = "published"


class Poll(BaseModel):
    """Poll/vote within a meeting."""
    __tablename__ = "polls"

    motion_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("motions.id", ondelete="CASCADE"),
        nullable=True
    )
    meeting_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    poll_type: Mapped[PollType] = mapped_column(
        Enum(PollType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=PollType.YES_NO
    )

    # Options for multiple choice (JSON array)
    options: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    status: Mapped[PollStatus] = mapped_column(
        Enum(PollStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=PollStatus.DRAFT,
        index=True
    )

    # Results (JSON object)
    results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Anonymous voting
    anonymous: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timing
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Creator
    created_by_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Additional fields
    poll_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    winning_option: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    motion: Mapped[Optional["Motion"]] = relationship(
        "Motion",
        back_populates="polls"
    )
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="polls"
    )
    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    votes: Mapped[list["Vote"]] = relationship(
        "Vote",
        back_populates="poll",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Poll {self.title}>"
