"""
Lead model for CRM module.

Leads represent potential contacts or organizations that haven't yet been
fully qualified. They can be converted to Contacts and/or Opportunities.
"""
from typing import Optional, TYPE_CHECKING
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class LeadStatus(str, Enum):
    """Lead qualification status."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    CONVERTED = "converted"


class LeadSource(str, Enum):
    """Source of the lead."""
    WEBSITE = "website"
    REFERRAL = "referral"
    EVENT = "event"
    COLD_CALL = "cold_call"
    ADVERTISEMENT = "advertisement"
    SOCIAL_MEDIA = "social_media"
    PARTNER = "partner"
    OTHER = "other"


class Lead(BaseModel):
    """
    Lead model.

    Represents a potential contact/organization in the early qualification stage.
    Can be converted to a Contact and/or Opportunity.
    """
    __tablename__ = "leads"

    # Organization relation (which OrgSuite org owns this lead)
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Lead identity
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Lead status and source
    status: Mapped[LeadStatus] = mapped_column(
        SQLEnum(
            LeadStatus,
            name="leadstatus",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=LeadStatus.NEW,
        nullable=False,
        index=True
    )
    source: Mapped[LeadSource] = mapped_column(
        SQLEnum(
            LeadSource,
            name="leadsource",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=LeadSource.OTHER,
        nullable=False
    )

    # Owner (user responsible for this lead)
    owner_user_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Conversion tracking
    converted_contact_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True
    )
    converted_opportunity_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        nullable=True  # FK added after opportunity model
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id]
    )
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[owner_user_id]
    )

    def __repr__(self) -> str:
        return f"<Lead {self.name} ({self.status.value})>"
