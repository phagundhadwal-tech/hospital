"""
app/auth/router.py
==================
FastAPI router for authentication endpoints.

Routes
------
POST /api/auth/login   → validates credentials, returns a signed JWT
GET  /api/auth/me      → returns the current user's profile (JWT required)

WHY /me instead of decoding the token client-side?
  The frontend CAN decode the token (it is not encrypted, just signed).
  But a /me endpoint is the conventional REST pattern and allows the
  server to enrich the response with extra fields (e.g. display name)
  without reissuing a new token.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.models import LoginRequest, MeResponse, TokenResponse
from app.auth.service import authenticate_user
from app.config import get_settings
from app.core.security import create_access_token, get_current_user
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
    """
    Authentication flow:
    1. Look up user by email in users.csv.
    2. Verify the plain-text password against the stored bcrypt hash.
    3. Build a JWT payload that includes role and department_id.
    4. Sign and return the token.

    On failure (wrong email or password) always return HTTP 401 with the same
    generic message to prevent user-enumeration attacks.
    """
    settings = get_settings()
    user     = authenticate_user(body.email, body.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Build the JWT payload.
    # role and department_id are embedded so every subsequent request is
    # authorised WITHOUT re-reading users.csv.
    token_payload = {
        "sub":             user["Staff_ID"],
        "email":           user["Email"],
        "role":            user["Role"],
        "department_id":   user.get("Department_ID", "") or "",
        "department_name": user.get("Department_Name", "") or "",
    }

    access_token = create_access_token(
        data=token_payload,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    full_name = (
        f"{user.get('First_Name', '')} {user.get('Last_Name', '')}".strip()
        or user["Email"]
    )

    return TokenResponse(
        access_token=access_token,
        role=user["Role"],
        department_id=user.get("Department_ID") or None,
        department_name=user.get("Department_Name") or None,
        staff_id=user["Staff_ID"],
        full_name=full_name,
    )


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get the current user's profile",
    description="Returns the decoded JWT claims for the authenticated caller.",
)
def me(current_user: TokenUser = Depends(get_current_user)) -> MeResponse:
    """
    No database read needed — all information comes from the verified JWT.
    If the token is missing, expired, or invalid, get_current_user raises
    HTTP 401 automatically.
    """
    return MeResponse(
        staff_id        = current_user.staff_id,
        email           = current_user.email,
        role            = current_user.role.value,
        department_id   = current_user.department_id,
        department_name = current_user.department_name,
    )
