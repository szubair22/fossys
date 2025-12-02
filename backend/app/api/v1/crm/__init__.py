"""
CRM module API routers.

Provides endpoints for:
- Leads: Early-stage prospect management
- Opportunities: Pipeline and deal management
- Activities: Interaction tracking (calls, emails, meetings, notes, tasks)
"""
from fastapi import APIRouter

from app.api.v1.crm.leads import router as leads_router
from app.api.v1.crm.opportunities import router as opportunities_router
from app.api.v1.crm.activities import router as activities_router

crm_router = APIRouter(prefix="/crm", tags=["crm"])

crm_router.include_router(leads_router)
crm_router.include_router(opportunities_router)
crm_router.include_router(activities_router)

__all__ = ["crm_router"]
