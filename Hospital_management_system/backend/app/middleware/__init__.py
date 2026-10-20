"""
app/middleware/
===============
Cross-cutting HTTP concerns, registered in one place by register_middleware().

Starlette runs the LAST middleware added first (outermost), so the order below is:
  CORS -> request context (id + access log) -> security headers -> routes
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.middleware.error_handlers import register_exception_handlers
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware


def register_middleware(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(SecurityHeadersMiddleware, api_prefix=settings.API_PREFIX)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins     = settings.cors_origins,
        allow_credentials = True,
        allow_methods     = ["*"],
        allow_headers     = ["*"],
        expose_headers    = [RequestContextMiddleware.HEADER],
    )
    register_exception_handlers(app)


__all__ = ["register_middleware"]
