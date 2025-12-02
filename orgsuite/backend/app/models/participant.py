"""
Participant model - tracks meeting attendance.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, ForeignKey, DateTime, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.user import User


class ParticipantRole(str, enum.Enum):
    """Participant role in a meeting."""
    ADMIN = "admin"
    MODERATOR = "moderator"
    MEMBER = "member"
    GUEST = "guest"
    OBSERVER = "observer"


class AttendanceStatus(str, enum.Enum):
    """Attendance status for a participant."""
    INVITED = "invited"
    PRESENT = "present"
    ABSENT = "absent"
    EXCUSED = "excused"


class Participant(BaseModel):
    """Participant in a meeting."""
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("meeting_id", "user_id", name="uq_participants_meeting_user"),
    )

    meeting_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    role: Mapped[ParticipantRole] = mapped_column(
        Enum(ParticipantRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ParticipantRole.MEMBER
    )

    # Presence tracking
    is_present: Mapped[bool] = mapped_column(Boolean, default=False)
    attendance_status: Mapped[Optional[AttendanceStatus]] = mapped_column(
        Enum(AttendanceStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        default=AttendanceStatus.INVITED
    )

    # Voting rights
    can_vote: Mapped[bool] = mapped_column(Boolean, default=True)
    vote_weight: Mapped[int] = mapped_column(Integer, default=1)

    # Timing
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="participants"
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id]
    )

    def __repr__(self) -> str:
        return f"<Participant {self.user_id} in meeting {self.meeting_id}>"
