"""
Base model with common fields.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


def generate_id() -> str:
    """Generate a 15-character ID similar to PocketBase."""
    return uuid.uuid4().hex[:15]


class TimestampMixin:
    """Mixin for created/updated timestamps."""
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class BaseModel(Base, TimestampMixin):
    """Abstract base model with id and timestamps."""
    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(15),
        primary_key=True,
        default=generate_id
    )
