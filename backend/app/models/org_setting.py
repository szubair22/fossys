"""
Organization Setting model - per-organization settings by scope.
"""
from typing import Optional, TYPE_CHECKING
import enum
from sqlalchemy import String, JSON, ForeignKey, Enum, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization


class SettingScope(str, enum.Enum):
    """Scope categories for organization settings."""
    GENERAL = "general"
    GOVERNANCE = "governance"
    MEMBERSHIP = "membership"
    FINANCE = "finance"
    DOCUMENTS = "documents"


class OrgSetting(BaseModel):
    """
    Organization-level settings by scope.

    Each organization can have multiple settings grouped by scope:
    - general: org name/abbreviation, timezone, locale
    - governance: meeting defaults, quorum settings, motion types
    - membership: member types, statuses, ID format
    - finance: fiscal year, currency, dimensions
    - documents: file settings (future)

    Settings are stored as key-value pairs with JSONB values.
    Composite unique constraint on (organization_id, scope, key).
    """
    __tablename__ = "org_settings"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "scope", "key",
            name="uq_org_settings_org_scope_key"
        ),
        Index("ix_org_settings_org_scope", "organization_id", "scope"),
    )

    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    scope: Mapped[SettingScope] = mapped_column(
        Enum(SettingScope, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="org_settings"
    )

    def __repr__(self) -> str:
        return f"<OrgSetting {self.organization_id}/{self.scope.value}/{self.key}>"
