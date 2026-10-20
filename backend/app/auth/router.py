"""
app/auth/router.py
==================
Authentication routes. Handlers delegate to app/auth/controller.py.

POST /api/auth/login   → validates credentials, returns a signed JWT
GET  /api/auth/me      → returns the current user's profile (JWT required)

WHY /me instead of decoding the token client-side?
  The frontend CAN decode the token (it is not encrypted, just signed).
  But a /me endpoint is the conventional REST pattern and allows the
  server to enrich the response with extra fields (e.g. display name)
  without reissuing a new token.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import controller
from app.auth.models import LoginRequest, MeResponse, TokenResponse
from app.core.security import get_current_user
from app.users.models import TokenUser

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Obtain a JWT access token",
    description=(
        "Submit email + password.  On success, returns a signed JWT and "
        "the caller's role/department so the UI can render the correct dashboard."
    ),
)
def login(body: LoginRequest) -> TokenResponse:
    return controller.login(body)


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get the current user's profile",
    description="Returns the decoded JWT claims for the authenticated caller.",
)
def me(current_user: TokenUser = Depends(get_current_user)) -> MeResponse:
    return controller.me(current_user)
