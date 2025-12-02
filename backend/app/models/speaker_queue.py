"""
Speaker queue model.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.agenda_item import AgendaItem
    from app.models.user import User


class SpeakerStatus(str, enum.Enum):
    """Speaker status in queue."""
    WAITING = "waiting"
    SPEAKING = "speaking"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class SpeakerType(str, enum.Enum):
    """Type of speaker request."""
    NORMAL = "normal"
    POINT_OF_ORDER = "point_of_order"
    REPLY = "reply"


class SpeakerQueue(BaseModel):
    """Speaker queue for agenda items."""
    __tablename__ = "speaker_queue"

    agenda_item_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("agenda_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)

    status: Mapped[SpeakerStatus] = mapped_column(
        Enum(SpeakerStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SpeakerStatus.WAITING
    )

    speaker_type: Mapped[SpeakerType] = mapped_column(
        Enum(SpeakerType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SpeakerType.NORMAL
    )

    # Time tracking
    speaking_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    agenda_item: Mapped["AgendaItem"] = relationship(
        "AgendaItem",
        back_populates="speaker_queue"
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id]
    )

    def __repr__(self) -> str:
        return f"<SpeakerQueue {self.user_id} at position {self.position}>"
