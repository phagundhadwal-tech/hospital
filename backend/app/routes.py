"""
app/routes.py
=============
The single place where routers are mounted.

  /api/auth/...        authentication
  /api/analytics/...   dashboard data
  /health, /health/db  unauthenticated probes (outside the API prefix)
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from app.analytics.router import router as analytics_router
from app.auth.router import router as auth_router
from app.config import Settings
from app.health.router import router as health_router


def register_routes(app: FastAPI, settings: Settings) -> None:
    api = APIRouter(prefix=settings.API_PREFIX)
    api.include_router(auth_router)
    api.include_router(analytics_router)

    app.include_router(api)
    app.include_router(health_router)
