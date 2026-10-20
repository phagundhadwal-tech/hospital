"""
app/middleware/request_context.py
=================================
Gives every request an id (reusing a client-supplied X-Request-ID when present),
stores it on request.state, echoes it in the response and writes one access-log
line per request.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

log = logging.getLogger("carepulse.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(self.HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers[self.HEADER] = request_id
        log.info(
            "%s %s -> %s (%.1f ms) [%s]",
            request.method, request.url.path, response.status_code, elapsed_ms, request_id,
        )
        return response
