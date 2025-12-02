"""
Journal Line model for double-entry bookkeeping.
"""
from typing import Optional, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import String, Text, ForeignKey, Integer, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.journal_entry import JournalEntry
    from app.models.account import Account


class JournalLine(BaseModel):
    """
    Journal Line model.

    Represents a single line in a journal entry.
    Each line debits or credits a specific account.
    """
    __tablename__ = "journal_lines"

    # Journal entry relation
    journal_entry_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Line number for ordering
    line_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Account relation
    account_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Debit/Credit amounts (one should be set, other is 0 or null)
    debit: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=True,
        default=0
    )
    credit: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=True,
        default=0
    )

    # Line description/memo (can override entry description)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # =========================================================================
    # DIMENSION PLACEHOLDERS (for future Intacct-like functionality)
    # These are optional and can be used to track costs by various dimensions.
    # =========================================================================

    # Department/Fund dimension
    department_id: Mapped[Optional[str]] = mapped_column(String(15), nullable=True, index=True)

    # Project dimension
    project_id: Mapped[Optional[str]] = mapped_column(String(15), nullable=True, index=True)

    # Class dimension (e.g., program, grant, event)
    class_id: Mapped[Optional[str]] = mapped_column(String(15), nullable=True, index=True)

    # Location dimension
    location_id: Mapped[Optional[str]] = mapped_column(String(15), nullable=True, index=True)

    # Custom dimensions (JSON for flexibility)
    # Can store things like: {"committee": "finance", "event": "gala2024"}
    custom_dimensions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    journal_entry: Mapped["JournalEntry"] = relationship(
        "JournalEntry",
        foreign_keys=[journal_entry_id],
        back_populates="lines"
    )
    account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[account_id],
        back_populates="journal_lines"
    )

    def __repr__(self) -> str:
        if self.debit and self.debit > 0:
            return f"<JournalLine DR {self.account_id}: {self.debit}>"
        return f"<JournalLine CR {self.account_id}: {self.credit}>"

    @property
    def amount(self) -> Decimal:
        """Returns the absolute amount of this line."""
        return (self.debit or Decimal(0)) + (self.credit or Decimal(0))

    @property
    def is_debit(self) -> bool:
        """Returns True if this is a debit line."""
        return bool(self.debit and self.debit > 0)

    @property
    def is_credit(self) -> bool:
        """Returns True if this is a credit line."""
        return bool(self.credit and self.credit > 0)
