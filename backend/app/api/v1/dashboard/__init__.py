"""
Dashboard module - Provides aggregated org data and metrics for the dashboard.

This module handles:
- Dashboard summary (aggregated data from all modules)
- Organization metrics (KPI tracking)
- Metric values (historical data)
"""
from fastapi import APIRouter
from app.api.v1.dashboard.summary import router as summary_router
from app.api.v1.dashboard.metrics import router as metrics_router

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])
dashboard_router.include_router(summary_router)
dashboard_router.include_router(metrics_router)

__all__ = ["dashboard_router"]
