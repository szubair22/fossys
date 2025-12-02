"""
Chart of Accounts model for double-entry bookkeeping.
"""
from typing import Optional, TYPE_CHECKING
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Boolean, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.journal_line import JournalLine


class AccountType(str, Enum):
    """Standard account types for double-entry bookkeeping."""
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class AccountSubType(str, Enum):
    """Sub-types for more granular categorization."""
    # Assets
    CASH = "cash"
    BANK = "bank"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    INVENTORY = "inventory"
    FIXED_ASSET = "fixed_asset"
    OTHER_ASSET = "other_asset"
    # Liabilities
    ACCOUNTS_PAYABLE = "accounts_payable"
    CREDIT_CARD = "credit_card"
    CURRENT_LIABILITY = "current_liability"
    LONG_TERM_LIABILITY = "long_term_liability"
    # Equity
    RETAINED_EARNINGS = "retained_earnings"
    OPENING_BALANCE = "opening_balance"
    OTHER_EQUITY = "other_equity"
    # Income
    OPERATING_INCOME = "operating_income"
    DONATIONS = "donations"
    DUES = "dues"
    GRANTS = "grants"
    OTHER_INCOME = "other_income"
    # Expenses
    OPERATING_EXPENSE = "operating_expense"
    COST_OF_GOODS = "cost_of_goods"
    PAYROLL = "payroll"
    OTHER_EXPENSE = "other_expense"


class Account(BaseModel):
    """
    Chart of Accounts model.

    Represents an account in the organization's chart of accounts
    for double-entry bookkeeping.
    """
    __tablename__ = "accounts"

    # Organization relation
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Account code (e.g., "1000", "1100", "4000")
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Account name
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Account type and subtype
    # Use values_callable to store lowercase values in DB
    account_type: Mapped[AccountType] = mapped_column(
        SQLEnum(
            AccountType,
            name="accounttype",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=False,
        index=True
    )
    account_subtype: Mapped[Optional[AccountSubType]] = mapped_column(
        SQLEnum(
            AccountSubType,
            name="accountsubtype",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=True
    )

    # Parent account for hierarchical chart of accounts
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Display order within its level
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    # Status flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # System accounts can't be deleted

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id],
        back_populates="accounts"
    )
    parent: Mapped[Optional["Account"]] = relationship(
        "Account",
        foreign_keys=[parent_id],
        remote_side="Account.id",
        back_populates="children"
    )
    children: Mapped[list["Account"]] = relationship(
        "Account",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    journal_lines: Mapped[list["JournalLine"]] = relationship(
        "JournalLine",
        back_populates="account",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Account {self.code} - {self.name}>"

    @property
    def is_debit_positive(self) -> bool:
        """Returns True if this account type increases with debits."""
        return self.account_type in [AccountType.ASSET, AccountType.EXPENSE]

    @property
    def is_credit_positive(self) -> bool:
        """Returns True if this account type increases with credits."""
        return self.account_type in [AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE]
