"""
OrgSuite FastAPI Application - Main entry point.

OrgSuite is a modular platform for nonprofit organizations, fraternities/sororities,
and service-based companies. It includes the following modules:

- Governance (OrgMeet): Organizations, meetings, motions, polls, minutes
- Membership: Members, contacts, dues/subscriptions
- Finance: Chart of accounts, journal entries, donations
- Events: Events, projects, calendars
- Documents: File management and attachments

This API maintains backward compatibility with the PocketBase SDK used by the frontend.
Legacy endpoints follow the PocketBase REST API patterns:
- /api/collections/{collection}/records - CRUD operations
- /api/collections/users/auth-with-password - Login
- /api/health - Health check

New v1 API endpoints are available under /api/v1/{module}/ paths.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.base import init_db
from app.schemas.common import HealthResponse

# Import legacy routers (PocketBase-compatible)
from app.api.v1 import auth, organizations, committees, meetings, participants
from app.api.v1 import agenda_items, motions, polls
from app.api.v1.recordings import router as recordings_router
from app.api.v1.ai_integrations import router as ai_integrations_router
from app.api.v1.meeting_notifications import router as meeting_notifications_router
from app.api.v1.files import router as files_router

# Import new modular routers
from app.api.v1.membership import membership_router
from app.api.v1.finance import finance_router
from app.api.v1.events import events_router
from app.api.v1.documents import documents_router
from app.api.v1.governance import organizations_v1_router, governance_router
from app.api.v1.admin import admin_router
from app.api.v1 import settings as settings_router
from app.api.v1.dashboard import dashboard_router
from app.api.v1.crm import crm_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup: Initialize database
    # Note: In production, use Alembic migrations instead
    await init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="OrgSuite API",
    version="2.0.0",
    description="""
OrgSuite - Modular platform for organizations.

## Modules

- **Governance** (OrgMeet): Meeting management, motions, polls, minutes
- **Membership**: Member and contact management
- **Finance**: Accounting, donations, invoices
- **Events**: Event and project management
- **Documents**: File and document management
- **CRM**: Customer relationship management - leads, opportunities, activities

## API Versions

- Legacy PocketBase-compatible API: `/api/collections/*`
- New REST API v1: `/api/v1/*`
    """,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/api/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(code=200, message="API is healthy.")


# ============================================================================
# LEGACY POCKETBASE-COMPATIBLE ENDPOINTS
# These maintain backward compatibility with the existing frontend.
# ============================================================================

# Auth/Users - PocketBase SDK: pb.collection('users').*
app.include_router(
    auth.router,
    prefix="/api/collections/users",
    tags=["users"]
)

# Organizations - PocketBase SDK: pb.collection('organizations').*
app.include_router(
    organizations.router,
    prefix="/api/collections/organizations",
    tags=["organizations"]
)

# Org Memberships
# Note: org_memberships would need its own router, but for now
# membership is created automatically when creating an org

# Committees - PocketBase SDK: pb.collection('committees').*
app.include_router(
    committees.router,
    prefix="/api/collections/committees",
    tags=["committees"]
)

# Meetings - PocketBase SDK: pb.collection('meetings').*
app.include_router(
    meetings.router,
    prefix="/api/collections/meetings",
    tags=["meetings"]
)

# Participants - PocketBase SDK: pb.collection('participants').*
app.include_router(
    participants.router,
    prefix="/api/collections/participants",
    tags=["participants"]
)

# Agenda Items - PocketBase SDK: pb.collection('agenda_items').*
app.include_router(
    agenda_items.router,
    prefix="/api/collections/agenda_items",
    tags=["agenda_items"]
)

# Motions - PocketBase SDK: pb.collection('motions').*
app.include_router(
    motions.router,
    prefix="/api/collections/motions",
    tags=["motions"]
)

# Polls - PocketBase SDK: pb.collection('polls').*
app.include_router(
    polls.router,
    prefix="/api/collections/polls",
    tags=["polls"]
)

# Votes - PocketBase SDK: pb.collection('votes').*
app.include_router(
    polls.votes_router,
    prefix="/api/collections/votes",
    tags=["votes"]
)

# Recordings - PocketBase SDK: pb.collection('recordings').*
app.include_router(
    recordings_router,
    prefix="/api/collections/recordings",
    tags=["recordings"]
)

# AI Integrations - PocketBase SDK: pb.collection('ai_integrations').*
app.include_router(
    ai_integrations_router,
    prefix="/api/collections/ai_integrations",
    tags=["ai_integrations"]
)

# Meeting Notifications - PocketBase SDK: pb.collection('meeting_notifications').*
app.include_router(
    meeting_notifications_router,
    prefix="/api/collections/meeting_notifications",
    tags=["meeting_notifications"]
)

# Files - PocketBase SDK: pb.collection('files').*
app.include_router(
    files_router,
    prefix="/api/collections/files",
    tags=["files"]
)


# ============================================================================
# NEW V1 API ENDPOINTS
# These are the new modular endpoints for OrgSuite.
# ============================================================================

# Membership module - /api/v1/membership/*
app.include_router(
    membership_router,
    prefix="/api/v1",
)

# Finance module - /api/v1/finance/*
app.include_router(
    finance_router,
    prefix="/api/v1",
)

# Events module - /api/v1/events/*
app.include_router(
    events_router,
    prefix="/api/v1",
)

# Documents module - /api/v1/documents/*
app.include_router(
    documents_router,
    prefix="/api/v1",
)

# Organizations v1 module - /api/v1/organizations/*
# New v1 API endpoints (replaces PocketBase-compatible endpoints)
app.include_router(
    organizations_v1_router,
    prefix="/api/v1/organizations",
    tags=["organizations-v1"]
)

# Governance module - /api/v1/governance/*
# Includes: committees, meetings, participants, agenda-items, motions, polls, votes
app.include_router(
    governance_router,
    prefix="/api/v1",
)

# Admin module - /api/v1/admin/*
# Includes: app-settings, org-settings
app.include_router(
    admin_router,
    prefix="/api/v1",
)

# Public settings module - /api/v1/settings/*
# Read-only access to org settings for authenticated members
app.include_router(
    settings_router.router,
    prefix="/api/v1",
)

# Dashboard module - /api/v1/dashboard/*
# Aggregated data for dashboard view
app.include_router(
    dashboard_router,
    prefix="/api/v1",
)

# CRM module - /api/v1/crm/*
# Customer relationship management: leads, opportunities, activities
app.include_router(
    crm_router,
    prefix="/api/v1",
)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)}
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
