"""
Meeting template model.
"""
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel
from app.models.meeting import MeetingType

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class OrgType(str, enum.Enum):
    """Organization type for templates."""
    FRATERNITY = "fraternity"
    SORORITY = "sorority"
    HOA = "hoa"
    NONPROFIT = "nonprofit"
    CHURCH = "church"
    CORPORATE = "corporate"
    GOVERNMENT = "government"
    GENERIC = "generic"


class MeetingTemplate(BaseModel):
    """Meeting template for quick meeting creation."""
    __tablename__ = "meeting_templates"

    # Organization (null for global templates)
    organization_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    org_type: Mapped[Optional[OrgType]] = mapped_column(
        Enum(OrgType, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )

    # Default values
    default_meeting_title: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    default_meeting_type: Mapped[Optional[MeetingType]] = mapped_column(
        Enum(MeetingType, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        default=MeetingType.GENERAL
    )

    # Default agenda (JSON array of agenda item definitions)
    default_agenda: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Settings (JSON object)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Global template flag
    is_global: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Creator (null for system templates)
    created_by_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization",
        back_populates="templates"
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )

    def __repr__(self) -> str:
        return f"<MeetingTemplate {self.name}>"
