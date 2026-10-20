"""
app/auth/controller.py
======================
Request handling logic for the authentication endpoints (no routing here).
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException, status

from app.auth.models import LoginRequest, MeResponse, TokenResponse
from app.auth.service import authenticate_user
from app.config import get_settings
from app.core.security import create_access_token
from app.users.models import TokenUser

INVALID_CREDENTIALS_DETAIL = "Incorrect email or password."


def login(body: LoginRequest) -> TokenResponse:
    """
    1. Look up the user by email and verify the bcrypt password.
    2. Embed role + department in the JWT so later requests need no user lookup.
    3. Return the signed token with the profile fields the UI needs.

    A wrong email and a wrong password produce the SAME 401 (no user enumeration).
    """
    settings = get_settings()
    user = authenticate_user(body.email, body.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={
            "sub":             user["Staff_ID"],
            "email":           user["Email"],
            "role":            user["Role"],
            "department_id":   user.get("Department_ID", "") or "",
            "department_name": user.get("Department_Name", "") or "",
        },
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


def me(current_user: TokenUser) -> MeResponse:
    """Profile of the caller, taken entirely from the verified JWT."""
    return MeResponse(
        staff_id        = current_user.staff_id,
        email           = current_user.email,
        role            = current_user.role.value,
        department_id   = current_user.department_id,
        department_name = current_user.department_name,
    )
