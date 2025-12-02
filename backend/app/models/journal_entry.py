"""
Journal Entry model for double-entry bookkeeping.
"""
from typing import Optional, TYPE_CHECKING
from datetime import date
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Boolean, Date, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.journal_line import JournalLine


class JournalEntryStatus(str, Enum):
    """Status of a journal entry."""
    DRAFT = "draft"
    POSTED = "posted"
    VOIDED = "voided"


class JournalEntry(BaseModel):
    """
    Journal Entry model.

    Represents a journal entry (accounting transaction) with multiple lines.
    Each journal entry must balance (total debits = total credits).
    """
    __tablename__ = "journal_entries"

    # Organization relation
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Entry number (auto-generated or manual)
    entry_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    # Date of the transaction
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Description/memo
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Reference (invoice number, receipt number, etc.)
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Source document type (for tracking origin)
    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., "donation", "invoice", "manual"
    source_id: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)  # ID of the source document

    # Status
    # Use values_callable to store lowercase values in DB
    status: Mapped[JournalEntryStatus] = mapped_column(
        SQLEnum(
            JournalEntryStatus,
            name="journalentrystatus",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=JournalEntryStatus.DRAFT,
        nullable=False,
        index=True
    )

    # Posted/void tracking
    posted_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    posted_by_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    voided_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    voided_by_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    void_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Created by
    created_by_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id],
        back_populates="journal_entries"
    )
    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    posted_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[posted_by_id]
    )
    voided_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[voided_by_id]
    )
    lines: Mapped[list["JournalLine"]] = relationship(
        "JournalLine",
        back_populates="journal_entry",
        cascade="all, delete-orphan",
        order_by="JournalLine.line_number"
    )

    def __repr__(self) -> str:
        return f"<JournalEntry {self.entry_number or self.id} ({self.status.value})>"

    @property
    def is_balanced(self) -> bool:
        """Check if the journal entry is balanced (debits = credits)."""
        total_debits = sum(line.debit or 0 for line in self.lines)
        total_credits = sum(line.credit or 0 for line in self.lines)
        return abs(total_debits - total_credits) < 0.01  # Allow for small rounding

    @property
    def total_debits(self):
        """Calculate total debits."""
        return sum(line.debit or 0 for line in self.lines)

    @property
    def total_credits(self):
        """Calculate total credits."""
        return sum(line.credit or 0 for line in self.lines)
