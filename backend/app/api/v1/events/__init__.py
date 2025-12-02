"""
Events module - Event and project management.

This module handles:
- Projects (organizational initiatives)
- Events (future)
- Calendars (future)
"""
from fastapi import APIRouter
from app.api.v1.events.projects import router as projects_router

# Create the events router for v1 API endpoints
events_router = APIRouter(prefix="/events", tags=["events"])

# Include sub-routers
events_router.include_router(projects_router, prefix="/projects", tags=["projects"])

__all__ = [
    "events_router",
]
