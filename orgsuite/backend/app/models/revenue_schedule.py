"""
Revenue Schedule and Revenue Schedule Line models for ASC 606 revenue recognition.

RevenueSchedule: Represents a revenue schedule for a contract line.
RevenueScheduleLine: Individual schedule entries for periodic revenue recognition.
"""
from typing import Optional, TYPE_CHECKING, List
from datetime import date
from decimal import Decimal
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Numeric, Date, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.contract_line import ContractLine
    from app.models.journal_entry import JournalEntry
    from app.models.user import User


class RevenueRecognitionMethod(str, Enum):
    """Revenue recognition method types."""
    POINT_IN_TIME = "point_in_time"
    STRAIGHT_LINE = "straight_line"


class RevenueScheduleStatus(str, Enum):
    """Status of a revenue schedule."""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RevenueScheduleLineStatus(str, Enum):
    """Status of a revenue schedule line."""
    PLANNED = "planned"
    POSTED = "posted"
    CANCELLED = "cancelled"


class RevenueSchedule(BaseModel):
    """
    Revenue Schedule model for tracking revenue recognition.

    Represents a schedule of revenue to be recognized from a contract line.
    Contains multiple schedule lines for periodic recognition.
    """
    __tablename__ = "revenue_schedules"

    # Organization relation (denormalized for easier querying)
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Contract line relation
    contract_line_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("contract_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Schedule identification
    schedule_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Total amount to be recognized
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Recognition method (derived from contract line or overridden)
    recognition_method: Mapped[RevenueRecognitionMethod] = mapped_column(
        SQLEnum(
            RevenueRecognitionMethod,
            name="revenuerecognitionmethod",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=RevenueRecognitionMethod.STRAIGHT_LINE,
        nullable=False
    )

    # Status
    status: Mapped[RevenueScheduleStatus] = mapped_column(
        SQLEnum(
            RevenueScheduleStatus,
            name="revenueschedulestatus",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=RevenueScheduleStatus.PLANNED,
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
    contract_line: Mapped["ContractLine"] = relationship(
        "ContractLine",
        foreign_keys=[contract_line_id],
        back_populates="revenue_schedules"
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    lines: Mapped[List["RevenueScheduleLine"]] = relationship(
        "RevenueScheduleLine",
        back_populates="schedule",
        cascade="all, delete-orphan",
        order_by="RevenueScheduleLine.schedule_date"
    )

    def __repr__(self) -> str:
        return f"<RevenueSchedule {self.schedule_number or self.id} ({self.status.value})>"

    @property
    def recognized_amount(self) -> Decimal:
        """Calculate total recognized (posted) amount."""
        return sum(
            (line.amount or Decimal(0))
            for line in self.lines
            if line.status == RevenueScheduleLineStatus.POSTED
        )

    @property
    def deferred_amount(self) -> Decimal:
        """Calculate remaining deferred (unrecognized) amount."""
        return self.total_amount - self.recognized_amount

    @property
    def planned_amount(self) -> Decimal:
        """Calculate total planned (not yet posted) amount."""
        return sum(
            (line.amount or Decimal(0))
            for line in self.lines
            if line.status == RevenueScheduleLineStatus.PLANNED
        )


class RevenueScheduleLine(BaseModel):
    """
    Revenue Schedule Line model for individual recognition entries.

    Each line represents a single recognition event on a specific date.
    When posted, creates a journal entry and links to it.
    """
    __tablename__ = "revenue_schedule_lines"

    # Revenue schedule relation
    revenue_schedule_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("revenue_schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Schedule date - when this revenue should be recognized
    schedule_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Period covered by this recognition (for reporting)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Amount to recognize
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False
    )

    # Status
    status: Mapped[RevenueScheduleLineStatus] = mapped_column(
        SQLEnum(
            RevenueScheduleLineStatus,
            name="revenueschedulelinestatus",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=RevenueScheduleLineStatus.PLANNED,
        nullable=False,
        index=True
    )

    # Link to journal entry when posted
    journal_entry_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Posted tracking
    posted_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    posted_by_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    schedule: Mapped["RevenueSchedule"] = relationship(
        "RevenueSchedule",
        foreign_keys=[revenue_schedule_id],
        back_populates="lines"
    )
    journal_entry: Mapped[Optional["JournalEntry"]] = relationship(
        "JournalEntry",
        foreign_keys=[journal_entry_id]
    )
    posted_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[posted_by_id]
    )

    def __repr__(self) -> str:
        return f"<RevenueScheduleLine {self.schedule_date} ${self.amount} ({self.status.value})>"

    @property
    def is_due(self) -> bool:
        """Check if this line is due for recognition (planned and date has passed)."""
        if self.status != RevenueScheduleLineStatus.PLANNED:
            return False
        return self.schedule_date <= date.today()
