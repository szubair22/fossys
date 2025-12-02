"""
Admin API routers for OrgSuite.

Provides endpoints for:
- Global app settings (superadmin only)
- Organization settings by scope
"""
from fastapi import APIRouter

from app.api.v1.admin.app_settings import router as app_settings_router
from app.api.v1.admin.org_settings import router as org_settings_router

# Combined admin router
admin_router = APIRouter(tags=["admin"])

admin_router.include_router(
    app_settings_router,
    prefix="/admin/app-settings",
    tags=["admin-app-settings"]
)

admin_router.include_router(
    org_settings_router,
    prefix="/admin/org-settings",
    tags=["admin-org-settings"]
)

__all__ = ["admin_router"]
