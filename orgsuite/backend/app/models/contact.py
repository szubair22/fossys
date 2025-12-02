"""
Contact model for third-party entities (donors, vendors, sponsors, partners).

Contacts are external entities that interact with the organization
but are not members.
"""
from typing import Optional, TYPE_CHECKING
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.donation import Donation


class ContactType(str, Enum):
    """Type of contact/third party."""
    DONOR = "donor"
    VENDOR = "vendor"
    SPONSOR = "sponsor"
    PARTNER = "partner"
    CLIENT = "client"
    VOLUNTEER = "volunteer"
    PROSPECT = "prospect"
    GRANT_MAKER = "grant_maker"
    GOVERNMENT = "government"
    OTHER = "other"


class Contact(BaseModel):
    """
    Contact/Third-party model.

    Represents external entities that interact with the organization:
    donors, vendors, sponsors, partners, etc.
    """
    __tablename__ = "contacts"

    # Organization relation
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Contact identity
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Address fields
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Contact type and status
    # Use values_callable to store lowercase values in DB
    contact_type: Mapped[ContactType] = mapped_column(
        SQLEnum(
            ContactType,
            name="contacttype",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=ContactType.OTHER,
        nullable=False,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Tax/legal info (for donations, invoices)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id],
        back_populates="contacts"
    )
    donations: Mapped[list["Donation"]] = relationship(
        "Donation",
        back_populates="contact",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Contact {self.name} ({self.contact_type.value})>"
