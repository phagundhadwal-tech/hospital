"""
app/auth/service.py
===================
Authentication business logic: password hashing and user lookup.

WHY bcrypt directly instead of passlib?
  passlib 1.7.4's bcrypt bridge is incompatible with bcrypt >= 4.x on
  Python 3.13 (bcrypt removed its __about__ attribute that passlib reads).
  Using the bcrypt package directly is simpler, supported, and correct.

SEPARATION OF CONCERNS:
  This module knows about users.csv and passwords.
  It does NOT know about HTTP, JWT tokens, or FastAPI.
  That keeps business logic independently testable.

USER STORE:
  Dashboard logins live in backend/data/users.csv (bcrypt hashes only, created by
  data/create_demo_users.py).  The hospital data itself is read from SQL Server.
"""

from __future__ import annotations

import csv
from pathlib import Path

import bcrypt

from app.config import get_settings


# ── Password helpers ──────────────────────────────────────────────────────────

def verify_password(plain_text: str, hashed: str) -> bool:
    """
    Return True if `plain_text` matches the stored bcrypt `hashed` value.
    bcrypt.checkpw is constant-time to prevent timing attacks.
    """
    return bcrypt.checkpw(
        plain_text.encode("utf-8"),
        hashed.encode("utf-8"),
    )


def hash_password(plain_text: str) -> str:
    """
    Hash a plain-text password with bcrypt (work factor = Settings.BCRYPT_ROUNDS).
    Used by create_demo_users.py to pre-hash passwords for users.csv.
    """
    salt = bcrypt.gensalt(rounds=get_settings().BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain_text.encode("utf-8"), salt).decode("utf-8")


# ── User loading ──────────────────────────────────────────────────────────────

def _load_users() -> list[dict]:
    """
    Read users.csv from the path configured in Settings.USERS_CSV_PATH.
    Returns an empty list if the file does not exist (so tests that override
    the path do not crash the import).
    """
    path = get_settings().users_csv_file
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Authentication ────────────────────────────────────────────────────────────

def authenticate_user(email: str, password: str) -> dict | None:
    """
    Look up a user by email and verify the password.

    Returns the user dict (from users.csv) on success, or None on failure.
    Always returns None (never raises) so the caller decides the HTTP status.

    Security note: the same code path executes for "wrong email" and
    "wrong password" — this prevents user-enumeration attacks where an
    attacker deduces valid email addresses from differing error messages.
    """
    users = _load_users()
    for user in users:
        email_match    = user.get("Email", "").lower() == email.lower()
        is_active      = user.get("Is_Active", "true").lower() == "true"
        hashed         = user.get("Hashed_Password", "")

        if email_match and is_active and hashed:
            if verify_password(password, hashed):
                return user

    return None
