"""
Contract Line model for ASC 606 revenue recognition.

Represents a performance obligation within a contract.
Each line can have its own recognition pattern and allocated transaction price.
"""
from typing import Optional, TYPE_CHECKING, List
from datetime import date
from decimal import Decimal
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Numeric, Date, Enum as SQLEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.contract import Contract
    from app.models.account import Account
    from app.models.revenue_schedule import RevenueSchedule


class RecognitionPattern(str, Enum):
    """Revenue recognition pattern types."""
    POINT_IN_TIME = "point_in_time"
    STRAIGHT_LINE = "straight_line"


class ContractLineStatus(str, Enum):
    """Status of a contract line."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ContractLine(BaseModel):
    """
    Contract Line model representing a performance obligation.

    Each line within a contract has:
    - A standalone selling price (SSP) for allocation
    - An allocated transaction price (after allocation)
    - A recognition pattern determining how revenue is recognized
    - Links to revenue and deferred revenue accounts
    """
    __tablename__ = "contract_lines"

    # Contract relation
    contract_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Line description
    description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Product/service type (simple string for Phase 1)
    product_type: Mapped[str] = mapped_column(
        String(50),
        default="service",
        nullable=False
    )  # e.g., "subscription", "service", "donation", "grant"

    # Recognition pattern
    recognition_pattern: Mapped[RecognitionPattern] = mapped_column(
        SQLEnum(
            RecognitionPattern,
            name="recognitionpattern",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=RecognitionPattern.STRAIGHT_LINE,
        nullable=False
    )

    # Service period dates (required for straight_line, optional for point_in_time)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Quantity and pricing
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=4),
        default=Decimal("1"),
        nullable=False
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False
    )

    # Standalone selling price (SSP) - used for allocation
    ssp_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False
    )

    # Allocated transaction price - set after allocation
    allocated_transaction_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=True
    )

    # Account links for journal entries
    revenue_account_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    deferred_revenue_account_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Status
    status: Mapped[ContractLineStatus] = mapped_column(
        SQLEnum(
            ContractLineStatus,
            name="contractlinestatus",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=ContractLineStatus.DRAFT,
        nullable=False,
        index=True
    )

    # Display order
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    contract: Mapped["Contract"] = relationship(
        "Contract",
        foreign_keys=[contract_id],
        back_populates="lines"
    )
    revenue_account: Mapped[Optional["Account"]] = relationship(
        "Account",
        foreign_keys=[revenue_account_id]
    )
    deferred_revenue_account: Mapped[Optional["Account"]] = relationship(
        "Account",
        foreign_keys=[deferred_revenue_account_id]
    )
    revenue_schedules: Mapped[List["RevenueSchedule"]] = relationship(
        "RevenueSchedule",
        back_populates="contract_line",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ContractLine {self.id} ({self.description[:30]}...)>"

    @property
    def extended_price(self) -> Decimal:
        """Calculate extended price (quantity * unit_price)."""
        return self.quantity * self.unit_price

    @property
    def has_schedule(self) -> bool:
        """Check if this line has any revenue schedules."""
        return len(self.revenue_schedules) > 0

    @property
    def total_scheduled(self) -> Decimal:
        """Calculate total amount scheduled for recognition."""
        total = Decimal(0)
        for schedule in self.revenue_schedules:
            total += schedule.total_amount or Decimal(0)
        return total
