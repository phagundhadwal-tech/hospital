"""
app/middleware/security_headers.py
==================================
Adds defensive response headers. API responses (everything under the API prefix)
also get Cache-Control: no-store because they contain patient-related data.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_STATIC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options":        "DENY",
    "Referrer-Policy":        "no-referrer",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_prefix: str = "/api") -> None:
        super().__init__(app)
        self.api_prefix = api_prefix

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for name, value in _STATIC_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith(self.api_prefix):
            response.headers.setdefault("Cache-Control", "no-store")
        return response
