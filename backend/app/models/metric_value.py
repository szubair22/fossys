"""
MetricValue model for storing historical metric values.

Each metric can have multiple values over time, allowing tracking of trends.
"""
from typing import Optional, TYPE_CHECKING
from datetime import date
from decimal import Decimal
from sqlalchemy import String, Text, ForeignKey, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.metric import Metric
    from app.models.user import User


class MetricValue(BaseModel):
    """
    MetricValue model for storing historical metric entries.

    Each value represents a point-in-time snapshot of a metric.
    """
    __tablename__ = "metric_values"

    # Metric relation
    metric_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("metrics.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # The numeric value (stored as Decimal for precision)
    value: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2),
        nullable=False
    )

    # When this value is considered effective (e.g., end of period)
    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )

    # Optional notes about this value entry
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit fields
    created_by_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    metric: Mapped["Metric"] = relationship(
        "Metric",
        back_populates="values",
        foreign_keys=[metric_id]
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )

    def __repr__(self) -> str:
        return f"<MetricValue {self.metric_id}: {self.value} @ {self.effective_date}>"
