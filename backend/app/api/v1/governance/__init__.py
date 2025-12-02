"""
Governance module - OrgMeet core functionality.

This module handles:
- Organizations
- Committees
- Meetings
- Motions
- Polls/Votes
- Participants
- Agenda items
- Minutes
- Notifications

NEW v1 API:
All new v1 endpoints are under /api/v1/governance/* and follow modern REST patterns.
Legacy PocketBase-compatible endpoints are maintained for backward compatibility.
"""
from fastapi import APIRouter

# Import existing routers - these maintain the PocketBase-compatible API
from app.api.v1 import (
    organizations as org_router,
    committees as comm_router,
    meetings as meeting_router,
    participants as participant_router,
    agenda_items as agenda_router,
    motions as motion_router,
    polls as poll_router,
)

# Import new v1 governance routers
from app.api.v1.governance.organizations import router as organizations_v1_router
from app.api.v1.governance.committees import router as committees_v1_router
from app.api.v1.governance.meetings import router as meetings_v1_router
from app.api.v1.governance.participants import router as participants_v1_router
from app.api.v1.governance.agenda_items import router as agenda_items_v1_router
from app.api.v1.governance.motions import router as motions_v1_router
from app.api.v1.governance.polls import router as polls_v1_router
from app.api.v1.governance.polls import votes_router as votes_v1_router
from app.api.v1.governance.templates import router as templates_v1_router
from app.api.v1.governance.minutes import router as minutes_v1_router
from app.api.v1.governance.org_memberships import router as org_memberships_v1_router
from app.api.v1.governance.org_invites import router as org_invites_v1_router

# Create a combined governance router for new v1 API endpoints
governance_router = APIRouter(prefix="/governance", tags=["governance"])

# Include all v1 sub-routers under /api/v1/governance
governance_router.include_router(committees_v1_router, prefix="/committees", tags=["committees-v1"])
governance_router.include_router(meetings_v1_router, prefix="/meetings", tags=["meetings-v1"])
governance_router.include_router(participants_v1_router, prefix="/participants", tags=["participants-v1"])
governance_router.include_router(agenda_items_v1_router, prefix="/agenda-items", tags=["agenda-items-v1"])
governance_router.include_router(motions_v1_router, prefix="/motions", tags=["motions-v1"])
governance_router.include_router(polls_v1_router, prefix="/polls", tags=["polls-v1"])
governance_router.include_router(votes_v1_router, prefix="/votes", tags=["votes-v1"])
governance_router.include_router(templates_v1_router, prefix="/templates", tags=["templates-v1"])
governance_router.include_router(minutes_v1_router, prefix="/minutes", tags=["minutes-v1"])
governance_router.include_router(org_memberships_v1_router, prefix="/org-memberships", tags=["org-memberships-v1"])
governance_router.include_router(org_invites_v1_router, prefix="/org-invites", tags=["org-invites-v1"])

# Re-export the existing routers for legacy compatibility
organizations_router = org_router.router
committees_router = comm_router.router
meetings_router = meeting_router.router
participants_router = participant_router.router
agenda_items_router = agenda_router.router
motions_router = motion_router.router
polls_router = poll_router.router

__all__ = [
    # New v1 combined router
    "governance_router",
    # Individual v1 routers
    "organizations_v1_router",
    "committees_v1_router",
    "meetings_v1_router",
    "participants_v1_router",
    "agenda_items_v1_router",
    "motions_v1_router",
    "polls_v1_router",
    "votes_v1_router",
    "templates_v1_router",
    "minutes_v1_router",
    "org_memberships_v1_router",
    "org_invites_v1_router",
    # Legacy routers
    "organizations_router",
    "committees_router",
    "meetings_router",
    "participants_router",
    "agenda_items_router",
    "motions_router",
    "polls_router",
]
