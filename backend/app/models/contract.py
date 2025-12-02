"""
Contract model for ASC 606 revenue recognition.

Represents a customer contract with performance obligations (contract lines).
Supports allocation of transaction price and revenue schedule generation.
"""
from typing import Optional, TYPE_CHECKING, List
from datetime import date
from decimal import Decimal
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Numeric, Date, Enum as SQLEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.member import Member
    from app.models.contact import Contact
    from app.models.user import User
    from app.models.project import Project
    from app.models.contract_line import ContractLine


class ContractStatus(str, Enum):
    """Status of a contract."""
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Contract(BaseModel):
    """
    Contract model for revenue recognition.

    Represents a customer contract under ASC 606/958.
    Contains contract lines (performance obligations) and links to revenue schedules.
    """
    __tablename__ = "contracts"

    # Organization relation
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Contract identification
    contract_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Customer - link to contact for this phase
    customer_contact_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Legacy member_id for backward compatibility
    member_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("members.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Optional project link
    project_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Contract dates
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Contract value - Total transaction price for allocation
    total_transaction_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Status
    status: Mapped[ContractStatus] = mapped_column(
        SQLEnum(
            ContractStatus,
            name="contractstatus",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=ContractStatus.DRAFT,
        nullable=False,
        index=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit fields
    created_by_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id]
    )
    customer_contact: Mapped[Optional["Contact"]] = relationship(
        "Contact",
        foreign_keys=[customer_contact_id]
    )
    member: Mapped[Optional["Member"]] = relationship(
        "Member",
        foreign_keys=[member_id]
    )
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        foreign_keys=[project_id]
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    lines: Mapped[List["ContractLine"]] = relationship(
        "ContractLine",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractLine.sort_order"
    )

    def __repr__(self) -> str:
        return f"<Contract {self.contract_number or self.id} ({self.status.value})>"

    @property
    def total_ssp(self) -> Decimal:
        """Calculate total standalone selling price from all lines."""
        return sum((line.ssp_amount or Decimal(0)) for line in self.lines)

    @property
    def total_allocated(self) -> Decimal:
        """Calculate total allocated transaction price from all lines."""
        return sum((line.allocated_transaction_price or Decimal(0)) for line in self.lines)

    @property
    def customer_name(self) -> Optional[str]:
        """Get customer name from contact or member."""
        if self.customer_contact:
            return self.customer_contact.name
        if self.member:
            return self.member.name
        return None
