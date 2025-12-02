"""
SQLAlchemy models for OrgSuite.

OrgSuite modules:
- Governance (OrgMeet): Organizations, meetings, motions, polls, minutes
- Membership: Members, contacts
- Finance: Accounts, journal entries, donations
- Events: Projects (organizational initiatives)
- Documents: Files
"""
# Core models
from app.models.user import User
from app.models.organization import Organization
from app.models.org_membership import OrgMembership

# Governance module (OrgMeet)
from app.models.committee import Committee
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.agenda_item import AgendaItem
from app.models.motion import Motion
from app.models.poll import Poll
from app.models.vote import Vote
from app.models.speaker_queue import SpeakerQueue
from app.models.chat_message import ChatMessage
from app.models.meeting_template import MeetingTemplate
from app.models.meeting_minutes import MeetingMinutes
from app.models.meeting_notification import MeetingNotification
from app.models.recording import Recording

# Membership module
from app.models.member import Member, MemberStatus, MemberType
from app.models.contact import Contact, ContactType

# Finance module
from app.models.account import Account, AccountType, AccountSubType
from app.models.journal_entry import JournalEntry, JournalEntryStatus
from app.models.journal_line import JournalLine
from app.models.donation import Donation, DonationStatus, PaymentMethod
from app.models.contract import Contract, ContractStatus
from app.models.contract_line import ContractLine, ContractLineStatus, RecognitionPattern
from app.models.revenue_schedule import (
    RevenueSchedule,
    RevenueScheduleStatus,
    RevenueScheduleLine,
    RevenueScheduleLineStatus,
    RevenueRecognitionMethod,
)

# Documents module
from app.models.file import File
from app.models.ai_integration import AIIntegration

# Events module
from app.models.project import Project, ProjectStatus

# CRM module
from app.models.lead import Lead, LeadStatus, LeadSource
from app.models.opportunity import Opportunity, OpportunityStage, OpportunitySource, VALID_STAGE_TRANSITIONS
from app.models.activity import Activity, ActivityType

# Settings module
from app.models.app_setting import AppSetting
from app.models.org_setting import OrgSetting, SettingScope

# Invitations
from app.models.org_invite import OrgInvite, OrgInviteStatus, OrgInviteRole

# Dashboard Metrics
from app.models.metric import Metric, MetricValueType, MetricFrequency
from app.models.metric_value import MetricValue

__all__ = [
    # Core
    "User",
    "Organization",
    "OrgMembership",
    # Governance
    "Committee",
    "Meeting",
    "Participant",
    "AgendaItem",
    "Motion",
    "Poll",
    "Vote",
    "SpeakerQueue",
    "ChatMessage",
    "MeetingTemplate",
    "MeetingMinutes",
    "MeetingNotification",
    "Recording",
    # Membership
    "Member",
    "MemberStatus",
    "MemberType",
    "Contact",
    "ContactType",
    # Finance
    "Account",
    "AccountType",
    "AccountSubType",
    "JournalEntry",
    "JournalEntryStatus",
    "JournalLine",
    "Donation",
    "DonationStatus",
    "PaymentMethod",
    "Contract",
    "ContractStatus",
    "ContractLine",
    "ContractLineStatus",
    "RecognitionPattern",
    "RevenueSchedule",
    "RevenueScheduleStatus",
    "RevenueScheduleLine",
    "RevenueScheduleLineStatus",
    "RevenueRecognitionMethod",
    # Documents
    "File",
    "AIIntegration",
    # Events
    "Project",
    "ProjectStatus",
    # CRM
    "Lead",
    "LeadStatus",
    "LeadSource",
    "Opportunity",
    "OpportunityStage",
    "OpportunitySource",
    "VALID_STAGE_TRANSITIONS",
    "Activity",
    "ActivityType",
    # Settings
    "AppSetting",
    "OrgSetting",
    "SettingScope",
    # Invitations
    "OrgInvite",
    "OrgInviteStatus",
    "OrgInviteRole",
    # Dashboard Metrics
    "Metric",
    "MetricValueType",
    "MetricFrequency",
    "MetricValue",
]
