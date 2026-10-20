"""
backend/tests/conftest.py
==========================
Shared pytest fixtures for all backend tests.

CRITICAL ORDER OF OPERATIONS
-----------------------------
1. Set environment variables at the TOP of this file (before any app imports).
2. Clear the lru_cache on get_settings() so the test env is picked up.
3. Create a temporary users.csv with known bcrypt-hashed passwords.
4. Import the FastAPI app AFTER the above steps.
5. Expose a session-scoped TestClient fixture.

WHY not use a real .env for tests?
  Tests must be hermetic — they must not depend on a developer having run
  create_demo_users.py first.  The conftest creates its own isolated user
  store with known credentials so tests are 100 % reproducible.

WHY session scope?
  Bcrypt hashing is intentionally slow.  Hashing six passwords once per
  test session (instead of once per test function) keeps the suite fast.
"""

from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path

import pytest

# ── Step 1: set env vars BEFORE any app module is imported ───────────────────
# A test-only secret that satisfies the ≥ 32-character requirement.
_TEST_JWT_SECRET = "pytest-only-secret-not-for-production-use-64-chars-exactly!!"
assert len(_TEST_JWT_SECRET) >= 32

os.environ["JWT_SECRET"]                   = _TEST_JWT_SECRET
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"]  = "60"
os.environ["DATABASE_URL"]                 = ""      # tests inject a SQLite handle instead

import sys                                                       # noqa: E402
_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND / "scripts"))                    # csv_expected.py
# USERS_CSV_PATH will be set below after the temp file is created.

# ── Step 2: hash test passwords (must happen before app import) ───────────────
# Import bcrypt directly here (not from app) to avoid circular-import risks.
import bcrypt as _bcrypt  # noqa: E402

# One demo credential per role — known only to the test suite.
TEST_CREDENTIALS: dict[str, tuple[str, str]] = {
    "Hospital Admin":     ("admin@test.internal",     "test-admin-password-only"),
    "Operations Manager": ("ops@test.internal",       "test-ops-password-only"),
    "Department Head":    ("depthead@test.internal",  "test-depthead-password"),
    "Doctor":             ("doctor@test.internal",    "test-doctor-password-ok"),
    "Nurse":              ("nurse@test.internal",     "test-nurse-password-ok!"),
    "Receptionist":       ("reception@test.internal", "test-reception-password"),
}

_DEPT_MAP: dict[str, tuple[str, str]] = {
    "Hospital Admin":     ("", ""),
    "Operations Manager": ("", ""),
    "Department Head":    ("3", "Cardiology"),
    "Doctor":             ("1", "Emergency"),
    "Nurse":              ("4", "Orthopedics"),
    "Receptionist":       ("2", "General Medicine"),
}

# Build user rows with bcrypt hashes
_test_user_rows: list[dict] = []
for _i, (_role, (_email, _password)) in enumerate(TEST_CREDENTIALS.items(), start=1):
    _did, _dname = _DEPT_MAP[_role]
    _test_user_rows.append({
        "Staff_ID":        f"TEST-{_i:03d}",
        "First_Name":      _role.split()[0],
        "Last_Name":       "Test",
        "Email":           _email,
        "Role":            _role,
        "Department_ID":   _did,
        "Department_Name": _dname,
        "Hashed_Password": _bcrypt.hashpw(_password.encode(), _bcrypt.gensalt(rounds=10)).decode(),
        "Is_Active":       "true",
    })

# ── Step 3: write temp users.csv ─────────────────────────────────────────────
_tmp_dir      = tempfile.mkdtemp(prefix="carepulse_tests_")
_users_csv    = Path(_tmp_dir) / "users.csv"
_FIELDNAMES   = [
    "Staff_ID", "First_Name", "Last_Name", "Email",
    "Role", "Department_ID", "Department_Name",
    "Hashed_Password", "Is_Active",
]

with open(_users_csv, "w", newline="", encoding="utf-8") as _f:
    _writer = csv.DictWriter(_f, fieldnames=_FIELDNAMES)
    _writer.writeheader()
    _writer.writerows(_test_user_rows)

os.environ["USERS_CSV_PATH"] = str(_users_csv)

# ── Step 4: import app AFTER env vars are set ─────────────────────────────────
from app.config import get_settings  # noqa: E402

get_settings.cache_clear()           # force re-read with test env vars

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app                   # noqa: E402


# ── Step 5: shared fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    A single TestClient instance shared across all tests in the session.
    Uses the in-memory app configured with test env vars and temp users.csv.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def test_credentials() -> dict[str, tuple[str, str]]:
    """
    Returns: { "Role Name": ("email@test.internal", "plain_password") }
    Tests use this to log in with each role and verify behaviour.
    """
    return TEST_CREDENTIALS
