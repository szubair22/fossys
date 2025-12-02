"""
Recording model.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.user import User


class RecordingProvider(str, enum.Enum):
    """Recording provider/source."""
    JITSI = "jitsi"
    ZOOM = "zoom"
    LOCAL = "local"
    YOUTUBE = "youtube"
    VIMEO = "vimeo"
    OTHER = "other"


class RecordingStatus(str, enum.Enum):
    """Recording status."""
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class RecordingVisibility(str, enum.Enum):
    """Recording visibility."""
    PRIVATE = "private"
    MEMBERS = "members"
    PUBLIC = "public"


class Recording(BaseModel):
    """Meeting recording metadata."""
    __tablename__ = "recordings"

    meeting_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    provider: Mapped[Optional[RecordingProvider]] = mapped_column(
        Enum(RecordingProvider, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        default=RecordingProvider.LOCAL
    )

    # External URL (for YouTube, Vimeo, etc.)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Local file
    file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    thumbnail: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Metadata
    recording_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)

    status: Mapped[RecordingStatus] = mapped_column(
        Enum(RecordingStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RecordingStatus.READY,
        index=True
    )

    visibility: Mapped[Optional[RecordingVisibility]] = mapped_column(
        Enum(RecordingVisibility, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        default=RecordingVisibility.MEMBERS
    )

    # Creator
    created_by_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="recordings"
    )
    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )

    def __repr__(self) -> str:
        return f"<Recording {self.title}>"
