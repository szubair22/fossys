"""
Organization invitation model.

Allows org admins/owners to invite new users by email.
"""
import secrets
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone, timedelta
from enum import Enum
from sqlalchemy import String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class OrgInviteStatus(str, Enum):
    """Status of an organization invitation."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class OrgInviteRole(str, Enum):
    """Role to assign to invited user."""
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


def generate_invite_token() -> str:
    """Generate a secure random invite token."""
    return secrets.token_urlsafe(32)


def default_expiry() -> datetime:
    """Default expiry is 7 days from now."""
    return datetime.now(timezone.utc) + timedelta(days=7)


class OrgInvite(BaseModel):
    """
    Organization invitation model.

    When an admin/owner invites someone by email, an OrgInvite is created.
    The invitee can accept the invitation (with or without a new account)
    and be added to the organization with the specified role.
    """
    __tablename__ = "org_invites"

    # Organization being invited to
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Email address of invitee
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Role to assign when accepted
    role: Mapped[OrgInviteRole] = mapped_column(
        SQLEnum(
            OrgInviteRole,
            name="orginviterole",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=OrgInviteRole.MEMBER,
        nullable=False
    )

    # Secure token for accepting the invitation
    token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        default=generate_invite_token,
        index=True
    )

    # Status
    status: Mapped[OrgInviteStatus] = mapped_column(
        SQLEnum(
            OrgInviteStatus,
            name="orginvitestatus",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=OrgInviteStatus.PENDING,
        nullable=False,
        index=True
    )

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=default_expiry
    )

    # Who sent the invitation
    invited_by_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Who accepted (if accepted by existing user)
    accepted_by_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # When accepted/cancelled
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Optional message to include in invitation
    message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id]
    )
    invited_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[invited_by_id]
    )
    accepted_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[accepted_by_id]
    )

    @property
    def is_expired(self) -> bool:
        """Check if the invitation has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the invitation can still be accepted."""
        return (
            self.status == OrgInviteStatus.PENDING and
            not self.is_expired
        )

    def __repr__(self) -> str:
        return f"<OrgInvite {self.email} to {self.organization_id} ({self.status.value})>"
