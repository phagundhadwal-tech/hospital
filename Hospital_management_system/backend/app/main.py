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

import logging

from fastapi import FastAPI

from app.config import get_settings
from app.middleware import register_middleware
from app.routes import register_routes


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.LOG_LEVEL.upper())

    app = FastAPI(
        title       = settings.APP_TITLE,
        description = settings.APP_DESCRIPTION,
        version     = settings.APP_VERSION,
        docs_url    = settings.DOCS_URL,
        redoc_url   = settings.REDOC_URL,
    )

    register_middleware(app, settings)    # CORS, request id/logging, security headers, error handlers
    register_routes(app, settings)        # /api/* routers and /health probes

    return app


# Module-level app instance consumed by uvicorn.
app = create_app()
