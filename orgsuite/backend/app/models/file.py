"""
File/document model.
"""
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.meeting import Meeting
    from app.models.agenda_item import AgendaItem
    from app.models.motion import Motion
    from app.models.user import User


class FileType(str, enum.Enum):
    """File type category."""
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    IMAGE = "image"
    OTHER = "other"


class File(BaseModel):
    """File/document metadata."""
    __tablename__ = "files"

    # File storage
    file: Mapped[str] = mapped_column(String(500), nullable=False)  # File path

    # Relations (at least organization is required)
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    meeting_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    agenda_item_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("agenda_items.id", ondelete="CASCADE"),
        nullable=True
    )
    motion_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("motions.id", ondelete="CASCADE"),
        nullable=True
    )

    # Metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    file_type: Mapped[Optional[FileType]] = mapped_column(
        Enum(FileType, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        default=FileType.OTHER
    )
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)

    # Uploader
    uploaded_by_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="files"
    )
    meeting: Mapped[Optional["Meeting"]] = relationship(
        "Meeting",
        back_populates="files"
    )
    agenda_item: Mapped[Optional["AgendaItem"]] = relationship(
        "AgendaItem",
        back_populates="files"
    )
    motion: Mapped[Optional["Motion"]] = relationship(
        "Motion",
        back_populates="files"
    )
    uploaded_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[uploaded_by_id]
    )

    def __repr__(self) -> str:
        return f"<File {self.name}>"
