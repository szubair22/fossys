"""
Donation model for tracking donations to the organization.
"""
from typing import Optional, TYPE_CHECKING
from datetime import date
from decimal import Decimal
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Numeric, Date, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.member import Member
    from app.models.contact import Contact
    from app.models.user import User


class DonationStatus(str, Enum):
    """Status of a donation."""
    PLEDGED = "pledged"
    PENDING = "pending"
    RECEIVED = "received"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Method of payment for donation."""
    CASH = "cash"
    CHECK = "check"
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    VENMO = "venmo"
    OTHER = "other"


class Donation(BaseModel):
    """
    Donation model.

    Tracks donations made to the organization by members or contacts.
    """
    __tablename__ = "donations"

    # Organization relation
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Donor - either member or contact (one should be set)
    member_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("members.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    contact_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # For anonymous or one-off donors (no member/contact)
    donor_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    donor_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Amount
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Date
    donation_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Payment details
    # Use values_callable to store lowercase values in DB
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(
        SQLEnum(
            PaymentMethod,
            name="paymentmethod",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=True
    )
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    status: Mapped[DonationStatus] = mapped_column(
        SQLEnum(
            DonationStatus,
            name="donationstatus",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=DonationStatus.PENDING,
        nullable=False,
        index=True
    )

    # Purpose/campaign
    purpose: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    campaign: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Tax receipt
    is_tax_deductible: Mapped[bool] = mapped_column(default=True)
    receipt_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    receipt_sent: Mapped[bool] = mapped_column(default=False)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Created by (user who recorded the donation)
    created_by_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id],
        back_populates="donations"
    )
    member: Mapped[Optional["Member"]] = relationship(
        "Member",
        foreign_keys=[member_id],
        back_populates="donations"
    )
    contact: Mapped[Optional["Contact"]] = relationship(
        "Contact",
        foreign_keys=[contact_id],
        back_populates="donations"
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )

    def __repr__(self) -> str:
        return f"<Donation {self.amount} {self.currency} ({self.status.value})>"
