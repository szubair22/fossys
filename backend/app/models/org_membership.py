"""
Organization membership model.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, DateTime, Enum, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.organization import Organization


class OrgMembershipRole(str, enum.Enum):
    """Roles in an organization."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class OrgMembership(BaseModel):
    """Organization membership model - links users to organizations with roles."""
    __tablename__ = "org_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_memberships_org_user"),
    )

    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[OrgMembershipRole] = mapped_column(
        Enum(OrgMembershipRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OrgMembershipRole.MEMBER,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Invitation tracking
    invited_by_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Custom permissions (JSON object)
    permissions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="memberships"
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="memberships"
    )
    invited_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[invited_by_id]
    )

    def __repr__(self) -> str:
        return f"<OrgMembership {self.user_id} in {self.organization_id} as {self.role}>"
