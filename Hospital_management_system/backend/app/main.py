"""
app/main.py
===========
FastAPI application factory.

WHY a factory function (create_app) instead of a bare global `app`?
  A factory makes it easy to create isolated app instances in tests without
  sharing state.  It also keeps startup logic (middleware, routers, handlers)
  in one readable place.

Running locally:
  From the project root:
    uvicorn backend.app.main:app --reload --port 8000

  Or from the backend/ directory:
    uvicorn app.main:app --reload --port 8000

Interactive API docs are available at:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.analytics.router import router as analytics_router
from app.auth.router import router as auth_router
from app.config import get_settings
from app.core.exceptions import CarePulseError, carepulse_error_handler


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title       = "CarePulse Hospital Management API",
        description = (
            "REST API for the CarePulse HMS dashboard. "
            "All endpoints require a valid JWT Bearer token except POST /api/auth/login."
        ),
        version     = "1.0.0",
        docs_url    = "/docs",
        redoc_url   = "/redoc",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Allow the Vite dev server (port 5173) and any other configured origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins     = settings.cors_origins,
        allow_credentials = True,
        allow_methods     = ["*"],
        allow_headers     = ["*"],
    )

    # ── Custom exception handler ───────────────────────────────────────────────
    app.add_exception_handler(CarePulseError, carepulse_error_handler)

    # ── Routers ───────────────────────────────────────────────────────────────
    # All API routes are prefixed with /api so that the Vite proxy can forward
    # /api/* requests to this server while serving the React app at /.
    app.include_router(auth_router,      prefix="/api")
    app.include_router(analytics_router, prefix="/api")

    # Health-check endpoint — no auth required.  Useful for load-balancer
    # liveness probes and to verify the server is running.
    @app.get("/health", tags=["Health"], include_in_schema=False)
    def health() -> dict:
        return {"status": "ok", "service": "CarePulse API"}

    @app.get("/health/db", tags=["Health"], include_in_schema=False)
    def health_db() -> dict:
        """Checks the SQL Server connection (503 with a clear message if it fails)."""
        from app.db.database import get_database

        rows = get_database().query("SELECT 1 AS ok")
        return {"status": "ok", "database": "reachable", "result": rows[0]["ok"]}

    return app


# Module-level app instance consumed by uvicorn.
app = create_app()
