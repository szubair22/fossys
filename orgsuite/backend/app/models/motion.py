"""
Motion model.
"""
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, Enum, JSON, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.agenda_item import AgendaItem
    from app.models.user import User
    from app.models.poll import Poll
    from app.models.file import File


class MotionWorkflowState(str, enum.Enum):
    """Motion workflow states."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    SCREENING = "screening"
    DISCUSSION = "discussion"
    VOTING = "voting"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    REFERRED = "referred"


# Many-to-many relationship for motion supporters
motion_supporters = Table(
    "motion_supporters",
    Base.metadata,
    Column("motion_id", String(15), ForeignKey("motions.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", String(15), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)


class Motion(BaseModel):
    """Motion/proposal within a meeting."""
    __tablename__ = "motions"

    meeting_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    agenda_item_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("agenda_items.id", ondelete="SET NULL"),
        nullable=True
    )

    # Motion identification
    number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Submitter
    submitter_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Workflow
    workflow_state: Mapped[MotionWorkflowState] = mapped_column(
        Enum(MotionWorkflowState, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=MotionWorkflowState.DRAFT,
        index=True
    )

    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Vote result (JSON for flexibility)
    vote_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Final notes after decision
    final_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Attachments (file paths as JSON array)
    attachments: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="motions"
    )
    agenda_item: Mapped[Optional["AgendaItem"]] = relationship(
        "AgendaItem",
        back_populates="motions"
    )
    submitter: Mapped["User"] = relationship(
        "User",
        foreign_keys=[submitter_id]
    )
    supporters: Mapped[list["User"]] = relationship(
        "User",
        secondary=motion_supporters
    )
    polls: Mapped[list["Poll"]] = relationship(
        "Poll",
        back_populates="motion"
    )
    files: Mapped[list["File"]] = relationship(
        "File",
        back_populates="motion"
    )

    def __repr__(self) -> str:
        return f"<Motion {self.number or self.id}: {self.title[:50]}>"
