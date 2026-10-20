"""
app/core/exceptions.py
=======================
Custom exception classes and their FastAPI exception handlers.

WHY custom exceptions?
  Raising HTTPException inside service or repository layers mixes HTTP concerns
  with business logic.  Custom exceptions let service code signal a problem
  (e.g. "resource not found") without knowing it is running inside an HTTP
  server.  The handler translates them to HTTP responses at the boundary.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class CarePulseError(Exception):
    """Base class for all CarePulse application errors."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail      = detail
        super().__init__(detail)


class NotFoundError(CarePulseError):
    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(404, detail)


class ForbiddenError(CarePulseError):
    def __init__(self, detail: str = "You do not have permission to access this resource") -> None:
        super().__init__(403, detail)


class UnauthorizedError(CarePulseError):
    def __init__(self, detail: str = "Authentication required") -> None:
        super().__init__(401, detail)


class BadRequestError(CarePulseError):
    def __init__(self, detail: str = "Invalid request") -> None:
        super().__init__(400, detail)


# ── FastAPI exception handler ─────────────────────────────────────────────────

async def carepulse_error_handler(request: Request, exc: CarePulseError) -> JSONResponse:
    """
    Converts any CarePulseError into a standard JSON error response:
        { "detail": "<message>" }
    Register this handler in main.py with app.add_exception_handler().
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


class DatabaseUnavailableError(CarePulseError):
    """Raised when SQL Server cannot be reached (maps to HTTP 503)."""

    def __init__(self, detail: str = "The hospital database is currently unavailable. Please try again shortly.") -> None:
        super().__init__(503, detail)


class DatabaseQueryError(CarePulseError):
    """Raised when SQL Server is reachable but a query fails (maps to HTTP 500)."""

    def __init__(self, detail: str = "The database query failed. Check that the tables exist (python scripts/check_db.py).") -> None:
        super().__init__(500, detail)
