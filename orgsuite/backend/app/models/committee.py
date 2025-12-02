"""
Committee model.
"""
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.meeting import Meeting


# Many-to-many relationship for committee admins
committee_admins = Table(
    "committee_admins",
    Base.metadata,
    Column("committee_id", String(15), ForeignKey("committees.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", String(15), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)


class Committee(BaseModel):
    """Committee within an organization."""
    __tablename__ = "committees"

    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="committees"
    )
    admins: Mapped[list["User"]] = relationship(
        "User",
        secondary=committee_admins,
        backref="admin_committees"
    )
    meetings: Mapped[list["Meeting"]] = relationship(
        "Meeting",
        back_populates="committee",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Committee {self.name}>"
