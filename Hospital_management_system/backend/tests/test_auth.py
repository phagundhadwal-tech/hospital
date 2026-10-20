"""
backend/tests/test_auth.py
===========================
Tests for the authentication layer:
  POST /api/auth/login
  GET  /api/auth/me
  Token integrity (payload claims)
  Access-denied scenarios

All tests use the session-scoped `client` and `test_credentials` fixtures
from conftest.py.  No real users.csv is required — conftest creates a temp
file with known bcrypt-hashed test passwords.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

# ── Helpers ───────────────────────────────────────────────────────────────────

def _login(client: TestClient, email: str, password: str):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════════════════════════
# Login — success cases
# ══════════════════════════════════════════════════════════════════════════════

class TestLoginSuccess:
    def test_admin_can_login(self, client, test_credentials):
        email, password = test_credentials["Hospital Admin"]
        resp = _login(client, email, password)
        assert resp.status_code == 200

    def test_login_returns_access_token(self, client, test_credentials):
        email, password = test_credentials["Hospital Admin"]
        data = _login(client, email, password).json()
        assert "access_token" in data
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 10

    def test_login_returns_bearer_type(self, client, test_credentials):
        email, password = test_credentials["Doctor"]
        data = _login(client, email, password).json()
        assert data["token_type"] == "bearer"

    def test_login_returns_correct_role(self, client, test_credentials):
        for role, (email, password) in test_credentials.items():
            data = _login(client, email, password).json()
            assert data["role"] == role, (
                f"Expected role '{role}' but got '{data['role']}' for {email}"
            )

    def test_login_returns_staff_id(self, client, test_credentials):
        email, password = test_credentials["Nurse"]
        data = _login(client, email, password).json()
        assert "staff_id" in data
        assert data["staff_id"].startswith("TEST-")

    def test_login_returns_full_name(self, client, test_credentials):
        email, password = test_credentials["Receptionist"]
        data = _login(client, email, password).json()
        assert "full_name" in data
        assert len(data["full_name"]) > 0

    def test_all_six_roles_can_login(self, client, test_credentials):
        """Every defined role must be able to authenticate."""
        for role, (email, password) in test_credentials.items():
            resp = _login(client, email, password)
            assert resp.status_code == 200, (
                f"Role '{role}' could not log in (status {resp.status_code})"
            )

    def test_login_case_insensitive_email(self, client, test_credentials):
        """Email matching should be case-insensitive."""
        email, password = test_credentials["Doctor"]
        resp = _login(client, email.upper(), password)
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# Login — failure cases
# ══════════════════════════════════════════════════════════════════════════════

class TestLoginFailure:
    def test_wrong_password_returns_401(self, client, test_credentials):
        email, _ = test_credentials["Nurse"]
        resp = _login(client, email, "definitely-wrong-password")
        assert resp.status_code == 401

    def test_unknown_email_returns_401(self, client):
        resp = _login(client, "nobody@test.internal", "any-password")
        assert resp.status_code == 401

    def test_empty_password_returns_401(self, client, test_credentials):
        email, _ = test_credentials["Receptionist"]
        resp = _login(client, email, "")
        assert resp.status_code == 401

    def test_wrong_password_error_message_is_generic(self, client, test_credentials):
        """
        Both 'wrong email' and 'wrong password' must return the SAME error
        message so attackers cannot enumerate valid email addresses.
        """
        # Wrong email (user does not exist at all)
        email_not_found_resp = _login(client, "notauser@test.internal", "pass")
        # Wrong password for a valid account
        valid_email, _ = test_credentials["Hospital Admin"]
        wrong_pw_resp = _login(client, valid_email, "wrong-password-123")
        # Both should be 401
        assert email_not_found_resp.status_code == 401
        assert wrong_pw_resp.status_code == 401
        # Both return the same generic message to prevent user enumeration
        assert (
            email_not_found_resp.json()["detail"]
            == wrong_pw_resp.json()["detail"]
        )

    def test_missing_body_fields_returns_422(self, client):
        """FastAPI validates required fields; missing keys return HTTP 422."""
        resp = client.post("/api/auth/login", json={"email": "only-email@test.internal"})
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# /me endpoint
# ══════════════════════════════════════════════════════════════════════════════

class TestMeEndpoint:
    def test_me_without_token_returns_401(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client):
        resp = client.get("/api/auth/me", headers=_auth_header("invalid.token.value"))
        assert resp.status_code == 401

    def test_me_with_valid_token_returns_200(self, client, test_credentials):
        email, password = test_credentials["Hospital Admin"]
        token = _login(client, email, password).json()["access_token"]
        resp  = client.get("/api/auth/me", headers=_auth_header(token))
        assert resp.status_code == 200

    def test_me_returns_correct_email(self, client, test_credentials):
        email, password = test_credentials["Department Head"]
        token = _login(client, email, password).json()["access_token"]
        data  = client.get("/api/auth/me", headers=_auth_header(token)).json()
        assert data["email"] == email

    def test_me_returns_correct_role(self, client, test_credentials):
        for role, (email, password) in test_credentials.items():
            token = _login(client, email, password).json()["access_token"]
            data  = client.get("/api/auth/me", headers=_auth_header(token)).json()
            assert data["role"] == role, f"Expected {role}, got {data['role']}"

    def test_me_full_access_roles_have_no_dept(self, client, test_credentials):
        """Hospital Admin and Operations Manager should have no department restriction."""
        for role in ("Hospital Admin", "Operations Manager"):
            email, password = test_credentials[role]
            token = _login(client, email, password).json()["access_token"]
            data  = client.get("/api/auth/me", headers=_auth_header(token)).json()
            assert data["department_id"] is None or data["department_id"] == "", (
                f"Full-access role '{role}' should have null/empty department_id"
            )

    def test_me_dept_scoped_roles_have_dept(self, client, test_credentials):
        """Department Head, Doctor, Nurse, Receptionist must carry a department_id."""
        for role in ("Department Head", "Doctor", "Nurse", "Receptionist"):
            email, password = test_credentials[role]
            token = _login(client, email, password).json()["access_token"]
            data  = client.get("/api/auth/me", headers=_auth_header(token)).json()
            assert data["department_id"], (
                f"Dept-scoped role '{role}' should have a non-empty department_id"
            )


# ══════════════════════════════════════════════════════════════════════════════
# JWT payload integrity
# ══════════════════════════════════════════════════════════════════════════════

class TestTokenPayload:
    """
    Verify that the JWT payload contains all claims required for
    server-side role and department scoping.
    Tokens are decoded with the same secret used to sign them.
    """

    def _decode(self, token: str) -> dict:
        from app.config import get_settings
        s = get_settings()
        # decode_complete=False means skip expiry check details;
        # we still verify the signature.
        return jose_jwt.decode(token, s.JWT_SECRET, algorithms=[s.JWT_ALGORITHM])

    def test_token_contains_sub(self, client, test_credentials):
        email, password = test_credentials["Hospital Admin"]
        token   = _login(client, email, password).json()["access_token"]
        payload = self._decode(token)
        assert "sub" in payload

    def test_token_contains_role(self, client, test_credentials):
        email, password = test_credentials["Doctor"]
        token   = _login(client, email, password).json()["access_token"]
        payload = self._decode(token)
        assert payload.get("role") == "Doctor"

    def test_token_contains_department_id(self, client, test_credentials):
        email, password = test_credentials["Nurse"]
        token   = _login(client, email, password).json()["access_token"]
        payload = self._decode(token)
        assert "department_id" in payload
        assert payload["department_id"] == "4"

    def test_token_contains_exp(self, client, test_credentials):
        """Tokens must carry an expiry claim so they are not valid forever."""
        email, password = test_credentials["Receptionist"]
        token   = _login(client, email, password).json()["access_token"]
        payload = self._decode(token)
        assert "exp" in payload

    def test_all_roles_have_role_claim(self, client, test_credentials):
        for role, (email, password) in test_credentials.items():
            token   = _login(client, email, password).json()["access_token"]
            payload = self._decode(token)
            assert payload.get("role") == role, (
                f"Token for '{role}' has wrong role claim: {payload.get('role')}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# Health check (no auth required)
# ══════════════════════════════════════════════════════════════════════════════

class TestHealthCheck:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_ok(self, client):
        data = client.get("/health").json()
        assert data.get("status") == "ok"
