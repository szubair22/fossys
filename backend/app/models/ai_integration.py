"""
AI integration model.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class AIProvider(str, enum.Enum):
    """AI provider."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    CUSTOM = "custom"


class AIIntegration(BaseModel):
    """AI integration settings for an organization."""
    __tablename__ = "ai_integrations"

    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    provider: Mapped[AIProvider] = mapped_column(
        Enum(AIProvider, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )

    # API credentials (should be encrypted in production)
    api_key: Mapped[str] = mapped_column(String(500), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Settings (JSON object)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Creator
    created_by_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Usage tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="ai_integrations"
    )
    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )

    def __repr__(self) -> str:
        return f"<AIIntegration {self.provider} for {self.organization_id}>"
