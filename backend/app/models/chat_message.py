"""
Chat message model.
"""
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.meeting import Meeting
    from app.models.user import User


class MessageType(str, enum.Enum):
    """Chat message type."""
    TEXT = "text"
    SYSTEM = "system"
    ANNOUNCEMENT = "announcement"


class ChatMessage(BaseModel):
    """Chat message within a meeting."""
    __tablename__ = "chat_messages"

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

    message: Mapped[str] = mapped_column(Text, nullable=False)

    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=MessageType.TEXT
    )

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="chat_messages"
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id]
    )

    def __repr__(self) -> str:
        return f"<ChatMessage {self.id} by {self.user_id}>"
