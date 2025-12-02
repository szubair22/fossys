"""
Dashboard summary endpoint for OrgSuite.

Provides aggregated data from all modules for the dashboard view.
"""
from datetime import datetime, timezone, date, timedelta
from typing import Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, extract

from app.db.base import get_db
from app.core.deps import get_current_user
from app.core.permissions import get_membership
from app.models.user import User
from app.models.organization import Organization
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.models.meeting import Meeting, MeetingStatus
from app.models.committee import Committee
from app.models.member import Member, MemberStatus
from app.models.donation import Donation, DonationStatus
from app.models.journal_entry import JournalEntry, JournalEntryStatus
from app.models.project import Project, ProjectStatus
from app.models.participant import Participant
from app.models.opportunity import Opportunity, OpportunityStage
from app.schemas.dashboard import (
    DashboardSummaryResponse, MeetingSnapshot, MembershipSnapshot,
    FinanceSnapshot, ProjectSnapshot, CRMSnapshot
)
from app.services.settings import get_finance_config

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get dashboard summary for an organization.

    Returns aggregated data including:
    - Upcoming meetings (next 5)
    - Membership stats
    - Finance overview (donations this month, YTD)
    - Projects overview

    Requires org membership to access.
    """
    # Get and verify organization
    org_result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = org_result.scalar_one_or_none()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check user membership
    membership = await get_membership(db, current_user.id, organization_id)
    user_role = None

    # Allow org owner even without explicit membership record
    if membership:
        user_role = membership.role.value if membership.role else None
    elif organization.owner_id == current_user.id:
        user_role = "owner"
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    # Get upcoming meetings (next 5)
    now = datetime.now(timezone.utc)
    upcoming_meetings_query = select(Meeting).where(
        or_(
            Meeting.organization_id == organization_id,
            Meeting.committee_id.in_(
                select(Committee.id).where(Committee.organization_id == organization_id)
            )
        ),
        Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS]),
        Meeting.start_time >= now
    ).order_by(Meeting.start_time.asc()).limit(5)

    meetings_result = await db.execute(upcoming_meetings_query)
    meetings = meetings_result.scalars().all()

    # Get total scheduled meetings count
    total_scheduled_query = select(func.count(Meeting.id)).where(
        or_(
            Meeting.organization_id == organization_id,
            Meeting.committee_id.in_(
                select(Committee.id).where(Committee.organization_id == organization_id)
            )
        ),
        Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS]),
        Meeting.start_time >= now
    )
    total_scheduled_result = await db.execute(total_scheduled_query)
    total_scheduled = total_scheduled_result.scalar() or 0

    # Build meeting snapshots with committee names
    meeting_snapshots = []
    for m in meetings:
        committee_name = None
        if m.committee_id:
            comm_result = await db.execute(
                select(Committee.name).where(Committee.id == m.committee_id)
            )
            committee_name = comm_result.scalar_one_or_none()

        meeting_snapshots.append(MeetingSnapshot(
            id=m.id,
            title=m.title,
            start_time=m.start_time,
            status=m.status.value if isinstance(m.status, MeetingStatus) else m.status,
            committee_name=committee_name
        ))

    # Membership stats
    member_count_query = select(
        Member.status,
        func.count(Member.id).label('count')
    ).where(
        Member.organization_id == organization_id
    ).group_by(Member.status)

    member_counts_result = await db.execute(member_count_query)
    member_counts = {row.status.value if hasattr(row.status, 'value') else row.status: row.count
                     for row in member_counts_result}

    # Recent members (last 5)
    recent_members_query = select(Member).where(
        Member.organization_id == organization_id
    ).order_by(Member.created.desc()).limit(5)

    recent_members_result = await db.execute(recent_members_query)
    recent_members = [
        {
            "id": m.id,
            "name": m.name,
            "status": m.status.value if hasattr(m.status, 'value') else m.status,
            "joined": m.join_date.isoformat() if m.join_date else None
        }
        for m in recent_members_result.scalars().all()
    ]

    membership_snapshot = MembershipSnapshot(
        total_active=member_counts.get('active', 0),
        total_pending=member_counts.get('pending', 0),
        total_inactive=member_counts.get('inactive', 0),
        recent_members=recent_members
    )

    # Finance: Donations this month and YTD
    today = date.today()
    first_of_month = today.replace(day=1)
    first_of_year = today.replace(month=1, day=1)

    # Get finance config for currency
    finance_config = await get_finance_config(db, organization_id)
    currency = finance_config.default_currency if finance_config else "USD"

    # Donations this month
    donations_this_month_query = select(
        func.coalesce(func.sum(Donation.amount), 0)
    ).where(
        Donation.organization_id == organization_id,
        Donation.status == DonationStatus.RECEIVED,
        Donation.donation_date >= first_of_month
    )
    donations_this_month_result = await db.execute(donations_this_month_query)
    donations_this_month = Decimal(str(donations_this_month_result.scalar() or 0))

    # Donations YTD
    donations_ytd_query = select(
        func.coalesce(func.sum(Donation.amount), 0)
    ).where(
        Donation.organization_id == organization_id,
        Donation.status == DonationStatus.RECEIVED,
        Donation.donation_date >= first_of_year
    )
    donations_ytd_result = await db.execute(donations_ytd_query)
    donations_ytd = Decimal(str(donations_ytd_result.scalar() or 0))

    # Recent journal entries (last 5 posted)
    recent_journal_query = select(JournalEntry).where(
        JournalEntry.organization_id == organization_id,
        JournalEntry.status == JournalEntryStatus.POSTED
    ).order_by(JournalEntry.entry_date.desc(), JournalEntry.created.desc()).limit(5)

    recent_journal_result = await db.execute(recent_journal_query)
    recent_journal = [
        {
            "id": j.id,
            "description": j.description,
            "entry_date": j.entry_date.isoformat() if j.entry_date else None,
            "status": j.status.value if hasattr(j.status, 'value') else j.status
        }
        for j in recent_journal_result.scalars().all()
    ]

    finance_snapshot = FinanceSnapshot(
        donations_this_month=donations_this_month,
        donations_ytd=donations_ytd,
        currency=currency,
        recent_journal_entries=recent_journal
    )

    # Projects overview
    project_count_query = select(
        Project.status,
        func.count(Project.id).label('count')
    ).where(
        Project.organization_id == organization_id
    ).group_by(Project.status)

    project_counts_result = await db.execute(project_count_query)
    project_counts = {row.status.value if hasattr(row.status, 'value') else str(row.status): row.count
                      for row in project_counts_result}

    # Active projects (up to 5)
    active_projects_query = select(Project).where(
        Project.organization_id == organization_id,
        Project.status == ProjectStatus.ACTIVE
    ).order_by(Project.start_date.desc().nullslast(), Project.created.desc()).limit(5)

    active_projects_result = await db.execute(active_projects_query)
    active_projects = [
        {
            "id": p.id,
            "name": p.name,
            "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
            "start_date": p.start_date.isoformat() if p.start_date else None
        }
        for p in active_projects_result.scalars().all()
    ]

    project_snapshot = ProjectSnapshot(
        total_active=project_counts.get('active', 0),
        total_planned=project_counts.get('planned', 0),
        total_completed=project_counts.get('completed', 0),
        active_projects=active_projects
    )

    # CRM overview - Open opportunities, pipeline value, expected this month
    open_stages = [
        OpportunityStage.PROSPECTING,
        OpportunityStage.QUALIFICATION,
        OpportunityStage.PROPOSAL_MADE,
        OpportunityStage.NEGOTIATION
    ]

    # Count open opportunities
    open_opps_query = select(func.count(Opportunity.id)).where(
        Opportunity.organization_id == organization_id,
        Opportunity.stage.in_(open_stages)
    )
    open_opps_result = await db.execute(open_opps_query)
    open_opportunities = open_opps_result.scalar() or 0

    # Total pipeline value (sum of open opportunities)
    pipeline_value_query = select(
        func.coalesce(func.sum(Opportunity.amount), 0)
    ).where(
        Opportunity.organization_id == organization_id,
        Opportunity.stage.in_(open_stages)
    )
    pipeline_value_result = await db.execute(pipeline_value_query)
    total_pipeline_value = Decimal(str(pipeline_value_result.scalar() or 0))

    # Expected revenue this month (opportunities closing this month, weighted by probability)
    last_day_of_month = (first_of_month.replace(month=first_of_month.month % 12 + 1, day=1)
                         if first_of_month.month < 12
                         else first_of_month.replace(year=first_of_month.year + 1, month=1, day=1))
    last_day_of_month = last_day_of_month.replace(day=1) - timedelta(days=1) if first_of_month.month < 12 else first_of_month.replace(month=12, day=31)

    expected_this_month_query = select(
        func.coalesce(func.sum(Opportunity.amount * Opportunity.probability / 100), 0)
    ).where(
        Opportunity.organization_id == organization_id,
        Opportunity.stage.in_(open_stages),
        Opportunity.expected_close_date >= first_of_month,
        Opportunity.expected_close_date <= today
    )
    expected_this_month_result = await db.execute(expected_this_month_query)
    expected_revenue_this_month = Decimal(str(expected_this_month_result.scalar() or 0))

    # Recent opportunities (last 5 updated)
    recent_opps_query = select(Opportunity).where(
        Opportunity.organization_id == organization_id
    ).order_by(Opportunity.updated.desc()).limit(5)

    recent_opps_result = await db.execute(recent_opps_query)
    recent_opportunities = [
        {
            "id": o.id,
            "title": o.title,
            "stage": o.stage.value if hasattr(o.stage, 'value') else str(o.stage),
            "amount": str(o.amount) if o.amount else None
        }
        for o in recent_opps_result.scalars().all()
    ]

    crm_snapshot = CRMSnapshot(
        open_opportunities=open_opportunities,
        total_pipeline_value=total_pipeline_value,
        expected_revenue_this_month=expected_revenue_this_month,
        currency=currency,
        recent_opportunities=recent_opportunities
    ) if open_opportunities > 0 or recent_opportunities else None

    return DashboardSummaryResponse(
        organization_id=organization_id,
        organization_name=organization.name,
        user_role=user_role,
        upcoming_meetings=meeting_snapshots,
        total_scheduled_meetings=total_scheduled,
        membership=membership_snapshot,
        finance=finance_snapshot,
        projects=project_snapshot,
        crm=crm_snapshot
    )
