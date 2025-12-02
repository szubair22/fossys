"""
Activity model for CRM module.

Activities represent interactions and follow-ups related to opportunities,
such as calls, emails, meetings, notes, and tasks.
"""
from typing import Optional, TYPE_CHECKING
from enum import Enum
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.opportunity import Opportunity
    from app.models.contact import Contact
    from app.models.user import User


class ActivityType(str, Enum):
    """Type of CRM activity."""
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    NOTE = "note"
    TASK = "task"


class Activity(BaseModel):
    """
    Activity/Interaction model.

    Represents CRM timeline entries for opportunities:
    calls, emails, meetings, notes, and tasks.
    """
    __tablename__ = "activities"

    # Organization relation
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Required: link to opportunity
    opportunity_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Optional: link to contact
    contact_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True
    )

    # Activity details
    type: Mapped[ActivityType] = mapped_column(
        SQLEnum(
            ActivityType,
            name="activitytype",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=False,
        index=True
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Task-specific fields
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Created by user
    created_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id]
    )
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity",
        back_populates="activities",
        foreign_keys=[opportunity_id]
    )
    contact: Mapped[Optional["Contact"]] = relationship(
        "Contact",
        foreign_keys=[contact_id]
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_user_id]
    )

    def __repr__(self) -> str:
        return f"<Activity {self.type.value}: {self.subject}>"
