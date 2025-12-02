"""
Agenda item model.
"""
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.motion import Motion
    from app.models.speaker_queue import SpeakerQueue
    from app.models.file import File


class AgendaItemType(str, enum.Enum):
    """Agenda item type."""
    TOPIC = "topic"
    MOTION = "motion"
    ELECTION = "election"
    BREAK = "break"
    OTHER = "other"


class AgendaItemStatus(str, enum.Enum):
    """Agenda item status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class AgendaItem(BaseModel):
    """Agenda item within a meeting."""
    __tablename__ = "agenda_items"

    meeting_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Ordering
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)

    # Duration estimate in minutes
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)

    item_type: Mapped[AgendaItemType] = mapped_column(
        Enum(AgendaItemType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=AgendaItemType.TOPIC
    )

    status: Mapped[AgendaItemStatus] = mapped_column(
        Enum(AgendaItemStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=AgendaItemStatus.PENDING
    )

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="agenda_items"
    )
    motions: Mapped[list["Motion"]] = relationship(
        "Motion",
        back_populates="agenda_item"
    )
    speaker_queue: Mapped[list["SpeakerQueue"]] = relationship(
        "SpeakerQueue",
        back_populates="agenda_item",
        cascade="all, delete-orphan"
    )
    files: Mapped[list["File"]] = relationship(
        "File",
        back_populates="agenda_item"
    )

    def __repr__(self) -> str:
        return f"<AgendaItem {self.order}: {self.title}>"
