"""
app/core/security.py
====================
JWT creation, decoding, and the FastAPI dependency that extracts the
current user from a Bearer token.

HOW JWT works (beginner-friendly):
  A JSON Web Token (JWT) is a signed string, split into three parts:
    header.payload.signature
  The server creates the token at login, embedding the user's role and
  department into the payload.  On every subsequent request the client
  sends the token in the Authorization header.  The server verifies the
  signature (using JWT_SECRET) — if it is valid, the payload is trusted
  without hitting the users.csv again.

WHY HS256?
  HS256 uses a single shared secret for both signing and verifying.
  It is the right choice for a single-server API where the same process
  that issues tokens also validates them.

Security notes
--------------
* The secret is read from the environment — never from source code.
* Tokens expire (ACCESS_TOKEN_EXPIRE_MINUTES); expired tokens are rejected.
* The role and department_id in the payload are used server-side to scope
  queries; the frontend cannot bypass this by sending a different department.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings
from app.users.models import TokenUser, UserRole

# Tells FastAPI where clients should POST to get a token.
# This is used by the interactive /docs UI only; the actual login logic
# lives in auth/router.py.
oauth2_scheme = HTTPBearer(auto_error=False)

# ── Token creation ────────────────────────────────────────────────────────────

def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Sign a JWT containing `data` plus an expiry claim (`exp`).

    Parameters
    ----------
    data          : A dict of claims to embed (e.g. sub, email, role).
    expires_delta : Custom lifetime. Falls back to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns
    -------
    A signed JWT string ready to be returned to the client.
    """
    settings  = get_settings()
    to_encode = data.copy()
    expire    = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# ── Token decoding ────────────────────────────────────────────────────────────

def _decode_raw(token: str) -> dict:
    """
    Decode and verify a JWT.  Raises HTTP 401 on any failure:
      - Invalid signature (tampered token)
      - Expired token
      - Malformed structure
    """
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_current_user(
    credentials = Depends(oauth2_scheme),
) -> TokenUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = _decode_raw(token)

    try:
        return TokenUser(
            staff_id=payload["sub"],
            email=payload["email"],
            role=UserRole(payload["role"]),
            department_id=payload.get("department_id") or None,
            department_name=payload.get("department_name") or None,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token payload is incomplete or invalid: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
