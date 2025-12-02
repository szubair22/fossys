"""
Organization model.
"""
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.org_membership import OrgMembership
    from app.models.committee import Committee
    from app.models.meeting_template import MeetingTemplate
    from app.models.file import File
    from app.models.ai_integration import AIIntegration
    from app.models.member import Member
    from app.models.contact import Contact
    from app.models.donation import Donation
    from app.models.account import Account
    from app.models.journal_entry import JournalEntry
    from app.models.org_setting import OrgSetting
    from app.models.project import Project


class Organization(BaseModel):
    """Organization model."""
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # File path
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Owner relation
    owner_id: Mapped[str] = mapped_column(
        String(15),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner_id],
        back_populates="owned_organizations"
    )
    default_org_users: Mapped[list["User"]] = relationship(
        "User",
        foreign_keys="User.default_org_id",
        back_populates="default_org"
    )
    memberships: Mapped[list["OrgMembership"]] = relationship(
        "OrgMembership",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    committees: Mapped[list["Committee"]] = relationship(
        "Committee",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    meetings: Mapped[list["Meeting"]] = relationship(
        "Meeting",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    templates: Mapped[list["MeetingTemplate"]] = relationship(
        "MeetingTemplate",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    files: Mapped[list["File"]] = relationship(
        "File",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    ai_integrations: Mapped[list["AIIntegration"]] = relationship(
        "AIIntegration",
        back_populates="organization",
        cascade="all, delete-orphan"
    )

    # OrgSuite module relationships
    members: Mapped[list["Member"]] = relationship(
        "Member",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    contacts: Mapped[list["Contact"]] = relationship(
        "Contact",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    donations: Mapped[list["Donation"]] = relationship(
        "Donation",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    accounts: Mapped[list["Account"]] = relationship(
        "Account",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    journal_entries: Mapped[list["JournalEntry"]] = relationship(
        "JournalEntry",
        back_populates="organization",
        cascade="all, delete-orphan"
    )

    # Settings module
    org_settings: Mapped[list["OrgSetting"]] = relationship(
        "OrgSetting",
        back_populates="organization",
        cascade="all, delete-orphan"
    )

    # Events module
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="organization",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"
