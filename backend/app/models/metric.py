"""
Metric model for org-specific KPI tracking.

Each organization can define custom metrics they want to track.
Metrics can be manual (user-entered values) or automatic (calculated from other data).
"""
from typing import Optional, TYPE_CHECKING, List
from enum import Enum
from decimal import Decimal
from sqlalchemy import String, Text, ForeignKey, Numeric, Integer, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.metric_value import MetricValue


class MetricValueType(str, Enum):
    """Type of metric value for display formatting."""
    NUMBER = "number"
    CURRENCY = "currency"
    PERCENT = "percent"


class MetricFrequency(str, Enum):
    """How often the metric is expected to be updated."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class Metric(BaseModel):
    """
    Metric model for tracking organization KPIs.

    Metrics are org-specific and can be either:
    - Manual: User enters values via dashboard
    - Automatic: Values calculated from other modules (future)
    """
    __tablename__ = "metrics"

    # Organization relation
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Metric definition
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Value type for display formatting
    value_type: Mapped[MetricValueType] = mapped_column(
        SQLEnum(
            MetricValueType,
            name="metricvaluetype",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=MetricValueType.NUMBER,
        nullable=False
    )

    # Update frequency
    frequency: Mapped[MetricFrequency] = mapped_column(
        SQLEnum(
            MetricFrequency,
            name="metricfrequency",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=MetricFrequency.MONTHLY,
        nullable=False
    )

    # Currency code for currency metrics (e.g., "USD", "EUR")
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Automatic vs manual
    is_automatic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_source: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )  # e.g., "membership_active_count", "finance_mtd_revenue"

    # Target value for progress tracking
    target_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=18, scale=2),
        nullable=True
    )

    # Display order
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Archived metrics are hidden but kept for history
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Audit fields
    created_by_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    updated_by_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id]
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    updated_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[updated_by_id]
    )
    values: Mapped[List["MetricValue"]] = relationship(
        "MetricValue",
        back_populates="metric",
        cascade="all, delete-orphan",
        order_by="MetricValue.effective_date.desc()"
    )

    def __repr__(self) -> str:
        return f"<Metric {self.name} ({self.organization_id})>"

    @property
    def latest_value(self) -> Optional["MetricValue"]:
        """Get the most recent value for this metric."""
        if self.values:
            return self.values[0]  # Already ordered by effective_date desc
        return None
