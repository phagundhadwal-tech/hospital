"""
app/middleware/error_handlers.py
================================
Turns exceptions into the standard  { "detail": "<message>" }  JSON body.

* CarePulseError   -> its own status code (raised by services / repositories).
* anything else    -> 500 with a generic message; the traceback is logged with the
                      request id so support can find it, but never sent to the client.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import CarePulseError, carepulse_error_handler

log = logging.getLogger("carepulse.errors")

INTERNAL_ERROR_DETAIL = "Internal server error."


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    log.error("Unhandled error [%s]: %s %s", request_id, request.method, request.url.path, exc_info=exc)
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(status_code=500, content={"detail": INTERNAL_ERROR_DETAIL}, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(CarePulseError, carepulse_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
