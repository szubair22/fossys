"""
User model.
"""
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.org_membership import OrgMembership
    from app.models.member import Member


class User(BaseModel):
    """User model for authentication and profile."""
    __tablename__ = "users"

    # Core auth fields
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Email verification (matching PocketBase behavior)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Superadmin flag for global app administration
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Profile fields (from migration 1700000009)
    display_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notify_meeting_invites: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_meeting_reminders: Mapped[bool] = mapped_column(Boolean, default=True)

    # Default organization (relation)
    default_org_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True
    )

    # Avatar (file path)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    default_org: Mapped[Optional["Organization"]] = relationship(
        "Organization",
        foreign_keys=[default_org_id],
        back_populates="default_org_users"
    )
    owned_organizations: Mapped[list["Organization"]] = relationship(
        "Organization",
        foreign_keys="Organization.owner_id",
        back_populates="owner"
    )
    memberships: Mapped[list["OrgMembership"]] = relationship(
        "OrgMembership",
        foreign_keys="OrgMembership.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # OrgSuite module relationships
    member_records: Mapped[list["Member"]] = relationship(
        "Member",
        foreign_keys="Member.user_id",
        back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
