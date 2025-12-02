"""
Project model for the Events module.

Projects represent organizational initiatives that may span multiple meetings
and track progress over time.
"""
from enum import Enum
from datetime import date
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, Date, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ProjectStatus(str, Enum):
    """Project lifecycle status."""
    PLANNED = "planned"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Project(BaseModel):
    """
    Project model.

    Represents an organizational initiative or project that can be tracked
    across meetings and committees.
    """
    __tablename__ = "projects"

    # Required fields
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Optional fields
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus),
        default=ProjectStatus.PLANNED,
        nullable=False
    )
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Optional: link to a committee responsible for the project
    committee_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("committees.id", ondelete="SET NULL"),
        nullable=True
    )

    # Owner of the project (user who created it)
    owner_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="projects")
    committee: Mapped[Optional["Committee"]] = relationship()
    owner: Mapped[Optional["User"]] = relationship()

    def __repr__(self) -> str:
        return f"<Project {self.name} ({self.status.value})>"
