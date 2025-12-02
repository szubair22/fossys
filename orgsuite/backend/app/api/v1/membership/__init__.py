"""
Membership module - Member and contact management.

This module handles:
- Members (organization members with status tracking)
- Contacts (donors, vendors, sponsors, partners)
- Subscriptions/Dues (future)
"""
from fastapi import APIRouter

from app.api.v1.membership.members import router as members_router
from app.api.v1.membership.contacts import router as contacts_router

# Create the membership router for v1 API endpoints
membership_router = APIRouter(prefix="/membership", tags=["membership"])

# Include sub-routers
# Routes will be: /api/v1/membership/members, /api/v1/membership/contacts
membership_router.include_router(members_router)
membership_router.include_router(contacts_router)

__all__ = [
    "membership_router",
]
