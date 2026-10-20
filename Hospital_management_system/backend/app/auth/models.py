"""
app/auth/models.py
==================
Pydantic schemas for authentication request and response bodies.

These are the "contract" shapes that the API accepts and returns.
Pydantic validates incoming JSON automatically; if a field is missing
or the wrong type, FastAPI returns HTTP 422 with a helpful error message.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """
    Body expected by POST /api/auth/login.

    Fields
    ------
    email    : The staff member's login email address.
    password : Plain-text password submitted by the client.
               It is compared against the bcrypt hash in users.csv and then
               IMMEDIATELY DISCARDED — it is never stored or logged.
    """
    email:    str
    password: str


class TokenResponse(BaseModel):
    """
    Body returned on successful login.

    Fields
    ------
    access_token   : Signed JWT string. Client stores this and sends it in
                     every subsequent request as: Authorization: Bearer <token>
    token_type     : Always "bearer" (OAuth2 convention).
    role           : Human-readable role string, e.g. "Hospital Admin".
    department_id  : FK to departments (e.g. "3") or null for full-access roles.
    department_name: E.g. "Cardiology" or null for full-access roles.
    staff_id       : Unique staff identifier.
    full_name      : Display name for the UI.
    """
    access_token:   str
    token_type:     str        = "bearer"
    role:           str
    department_id:  str | None = None
    department_name: str | None = None
    staff_id:       str
    full_name:      str


class MeResponse(BaseModel):
    """
    Body returned by GET /api/auth/me — the current user's profile.
    Derived entirely from the JWT payload (no CSV read needed).
    """
    staff_id:        str
    email:           str
    role:            str
    department_id:   str | None = None
    department_name: str | None = None
