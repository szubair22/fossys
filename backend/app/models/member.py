"""
Member model for organization membership tracking.

Members are individuals who belong to an organization with a specific status.
This is separate from org_membership which tracks system access/roles.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime, date
from enum import Enum
from sqlalchemy import String, Text, ForeignKey, Boolean, Date, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.donation import Donation


class MemberStatus(str, Enum):
    """Status of an organization member."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ALUMNI = "alumni"
    GUEST = "guest"
    HONORARY = "honorary"
    SUSPENDED = "suspended"


class MemberType(str, Enum):
    """Type of member (for fraternities/nonprofits/etc)."""
    REGULAR = "regular"
    ASSOCIATE = "associate"
    LIFETIME = "lifetime"
    STUDENT = "student"
    BOARD = "board"
    VOLUNTEER = "volunteer"
    STAFF = "staff"


class Member(BaseModel):
    """
    Organization member model.

    Represents a member of an organization with status tracking,
    separate from system user accounts and access control.
    """
    __tablename__ = "members"

    # Organization relation
    organization_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Optional link to system user account
    user_id: Mapped[Optional[str]] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Member identity
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Address fields
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Member status and type
    # Use values_callable to store lowercase values in DB (e.g., 'active' not 'ACTIVE')
    status: Mapped[MemberStatus] = mapped_column(
        SQLEnum(
            MemberStatus,
            name="memberstatus",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=MemberStatus.PENDING,
        nullable=False,
        index=True
    )
    member_type: Mapped[Optional[MemberType]] = mapped_column(
        SQLEnum(
            MemberType,
            name="membertype",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=MemberType.REGULAR,
        nullable=True
    )

    # Membership dates
    join_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Flags
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Member number (for organizations that assign numbers)
    member_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id],
        back_populates="members"
    )
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="member_records"
    )
    donations: Mapped[list["Donation"]] = relationship(
        "Donation",
        back_populates="member",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Member {self.name} ({self.status.value})>"
