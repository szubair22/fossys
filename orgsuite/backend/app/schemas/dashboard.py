"""
Dashboard schemas for OrgSuite.
"""
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class MeetingSnapshot(BaseModel):
    """Brief meeting info for dashboard."""
    id: str
    title: str
    start_time: Optional[datetime]
    status: str
    committee_name: Optional[str] = None


class MembershipSnapshot(BaseModel):
    """Membership statistics for dashboard."""
    total_active: int
    total_pending: int
    total_inactive: int
    recent_members: List[dict]  # List of {id, name, status, joined}


class FinanceSnapshot(BaseModel):
    """Finance summary for dashboard."""
    donations_this_month: Decimal
    donations_ytd: Decimal
    currency: str
    recent_journal_entries: List[dict]  # List of {id, description, entry_date, status}


class ProjectSnapshot(BaseModel):
    """Project statistics for dashboard."""
    total_active: int
    total_planned: int
    total_completed: int
    active_projects: List[dict]  # List of {id, name, status, start_date}


class CRMSnapshot(BaseModel):
    """CRM summary for dashboard."""
    open_opportunities: int
    total_pipeline_value: Decimal
    expected_revenue_this_month: Decimal
    currency: str
    recent_opportunities: List[dict]  # List of {id, title, stage, amount}


class DashboardSummaryResponse(BaseModel):
    """Complete dashboard summary for an organization."""
    organization_id: str
    organization_name: str
    user_role: Optional[str]

    # Upcoming meetings (next 5)
    upcoming_meetings: List[MeetingSnapshot]
    total_scheduled_meetings: int

    # Membership stats
    membership: MembershipSnapshot

    # Finance overview
    finance: FinanceSnapshot

    # Projects overview
    projects: ProjectSnapshot

    # CRM overview (optional, may be None if no CRM data)
    crm: Optional[CRMSnapshot] = None
