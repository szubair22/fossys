"""
Opportunity model for CRM module.

Opportunities represent potential deals or engagements with contacts/organizations.
Inspired by Dolibarr's commercial proposal and pipeline concepts.
"""
from typing import Optional, TYPE_CHECKING
from enum import Enum
from decimal import Decimal
from datetime import date
from sqlalchemy import String, Text, ForeignKey, Numeric, Integer, Date, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.contact import Contact
    from app.models.project import Project
    from app.models.user import User


class OpportunityStage(str, Enum):
    """Opportunity pipeline stage (Dolibarr-inspired)."""
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    PROPOSAL_MADE = "proposal_made"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class OpportunitySource(str, Enum):
    """Source of the opportunity."""
    COLD_CALL = "cold_call"
    WEB = "web"
    PARTNER = "partner"
    EVENT = "event"
    REFERRAL = "referral"
    EXISTING_CLIENT = "existing_client"
    MARKETING_CAMPAIGN = "marketing_campaign"
    OTHER = "other"


# Valid stage transitions (from -> to allowed stages)
VALID_STAGE_TRANSITIONS = {
    OpportunityStage.PROSPECTING: [
        OpportunityStage.QUALIFICATION,
        OpportunityStage.LOST
    ],
    OpportunityStage.QUALIFICATION: [
        OpportunityStage.PROSPECTING,
        OpportunityStage.PROPOSAL_MADE,
        OpportunityStage.LOST
    ],
    OpportunityStage.PROPOSAL_MADE: [
        OpportunityStage.QUALIFICATION,
        OpportunityStage.NEGOTIATION,
        OpportunityStage.WON,
        OpportunityStage.LOST
    ],
    OpportunityStage.NEGOTIATION: [
        OpportunityStage.PROPOSAL_MADE,
        OpportunityStage.WON,
        OpportunityStage.LOST
    ],
    OpportunityStage.WON: [],  # Terminal state
    OpportunityStage.LOST: [
        OpportunityStage.PROSPECTING  # Can reopen
    ]
}


class Opportunity(BaseModel):
    """
    Opportunity model.

    Represents a potential deal or engagement tracked through pipeline stages.
    Can be linked to contacts, organizations, and projects.
    """
    __tablename__ = "opportunities"

    # Organization relation (which OrgSuite org owns this opportunity)
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Core fields
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Related entities
    related_contact_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    related_project_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True
    )

    # Value fields
    amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False
    )

    # Pipeline fields
    stage: Mapped[OpportunityStage] = mapped_column(
        SQLEnum(
            OpportunityStage,
            name="opportunitystage",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=OpportunityStage.PROSPECTING,
        nullable=False,
        index=True
    )
    probability: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False
    )

    # Dates
    expected_close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Source
    source: Mapped[OpportunitySource] = mapped_column(
        SQLEnum(
            OpportunitySource,
            name="opportunitysource",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=OpportunitySource.OTHER,
        nullable=False
    )

    # Owner (user responsible for this opportunity)
    owner_user_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id]
    )
    related_contact: Mapped[Optional["Contact"]] = relationship(
        "Contact",
        foreign_keys=[related_contact_id]
    )
    related_project: Mapped[Optional["Project"]] = relationship(
        "Project",
        foreign_keys=[related_project_id]
    )
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[owner_user_id]
    )
    activities: Mapped[list["Activity"]] = relationship(
        "Activity",
        back_populates="opportunity",
        cascade="all, delete-orphan"
    )

    def can_transition_to(self, new_stage: OpportunityStage) -> bool:
        """Check if transition to new_stage is valid."""
        allowed = VALID_STAGE_TRANSITIONS.get(self.stage, [])
        return new_stage in allowed

    def __repr__(self) -> str:
        return f"<Opportunity {self.title} ({self.stage.value})>"
