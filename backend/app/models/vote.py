"""
Vote model.
"""
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.poll import Poll
    from app.models.user import User


class Vote(BaseModel):
    """Individual vote on a poll."""
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("poll_id", "user_id", name="uq_votes_poll_user"),
    )

    poll_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("polls.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Vote value (JSON for flexibility: can be "yes"/"no", option index, ranked choices, etc.)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Vote weight (for weighted voting)
    weight: Mapped[int] = mapped_column(Integer, default=1)

    # Delegation support
    delegated_from_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    poll: Mapped["Poll"] = relationship(
        "Poll",
        back_populates="votes"
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id]
    )
    delegated_from: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[delegated_from_id]
    )

    def __repr__(self) -> str:
        return f"<Vote by {self.user_id} on poll {self.poll_id}>"
