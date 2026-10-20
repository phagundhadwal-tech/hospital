"""HTTP-level tests: authentication, role scoping, filters and error handling."""

from __future__ import annotations

import pytest

import csv_expected as ce
from app.core.exceptions import DatabaseUnavailableError
from app.db.database import get_db
from app.main import app
from tests.helpers import DATA_DIR, Sqlite3Database

ENDPOINTS = ["kpis", "monthly-trend", "dept-activity", "patient-flow", "bed-availability", "departments"]


@pytest.fixture(scope="module", autouse=True)
def sqlite_db():
    db = Sqlite3Database()
    app.dependency_overrides[get_db] = lambda: db
    yield db
    app.dependency_overrides.pop(get_db, None)


def _auth(client, creds, role):
    email, password = creds[role]
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("name", ENDPOINTS + ["data-quality"])
def test_endpoints_require_authentication(client, name):
    assert client.get(f"/api/analytics/{name}").status_code == 401


def test_admin_kpis_match_csv(client, test_credentials):
    h = _auth(client, test_credentials, "Hospital Admin")
    body = client.get("/api/analytics/kpis", headers=h).json()
    exp = ce.expected_visit_metrics(ce.load(DATA_DIR)[0])
    assert body["admissions"] == exp["admissions"] == 1182
    assert body["discharges"] == exp["discharges"] == 1130
    assert body["avg_wait_minutes"] == exp["avg_wait_minutes"]
    assert body["current_admissions"] == 52
    assert body["bed_occupancy_pct"] == 18.6


def test_date_filter_changes_results_and_end_date_is_inclusive(client, test_credentials):
    h = _auth(client, test_credentials, "Hospital Admin")
    one_day = client.get("/api/analytics/patient-flow", headers=h,
                         params={"start_date": "2026-10-19", "end_date": "2026-10-19"}).json()
    assert one_day["total_visits"] == 15


def test_empty_range_returns_zeros_and_null_wait(client, test_credentials):
    h = _auth(client, test_credentials, "Hospital Admin")
    body = client.get("/api/analytics/kpis", headers=h,
                      params={"start_date": "2030-01-01", "end_date": "2030-12-31"}).json()
    assert body["admissions"] == 0 and body["discharges"] == 0 and body["avg_wait_minutes"] is None


def test_department_filter_for_admin(client, test_credentials):
    h = _auth(client, test_credentials, "Hospital Admin")
    rows = client.get("/api/analytics/dept-activity", headers=h, params={"department_id": "1"}).json()["data"]
    assert [r["department_id"] for r in rows] == ["1"]


def test_scoped_role_cannot_widen_department(client, test_credentials):
    h = _auth(client, test_credentials, "Department Head")           # token department = 3 (Cardiology)
    rows = client.get("/api/analytics/dept-activity", headers=h, params={"department_id": "1"}).json()["data"]
    assert [r["department_id"] for r in rows] == ["3"]
    assert len(client.get("/api/analytics/departments", headers=h).json()) == 1
    beds = client.get("/api/analytics/bed-availability", headers=h).json()
    assert beds["total_beds"] == 55


def test_admin_sees_all_departments(client, test_credentials):
    h = _auth(client, test_credentials, "Hospital Admin")
    assert len(client.get("/api/analytics/departments", headers=h).json()) == 4


def test_role_restrictions_still_enforced(client, test_credentials):
    assert client.get("/api/analytics/patient-flow", headers=_auth(client, test_credentials, "Nurse")).status_code == 403
    assert client.get("/api/analytics/bed-availability", headers=_auth(client, test_credentials, "Receptionist")).status_code == 403
    assert client.get("/api/analytics/data-quality", headers=_auth(client, test_credentials, "Doctor")).status_code == 403
    assert client.get("/api/analytics/data-quality", headers=_auth(client, test_credentials, "Hospital Admin")).status_code == 200


def test_bad_filters_return_400(client, test_credentials):
    h = _auth(client, test_credentials, "Hospital Admin")
    assert client.get("/api/analytics/kpis", headers=h, params={"start_date": "nope"}).status_code == 400
    assert client.get("/api/analytics/kpis", headers=h,
                      params={"start_date": "2026-07-02", "end_date": "2026-07-01"}).status_code == 400


def test_database_outage_returns_clear_503(client, test_credentials):
    class BrokenDb:
        dialect = "mssql"
        def table(self, name): return name
        def query(self, sql, params=None): raise DatabaseUnavailableError()

    h = _auth(client, test_credentials, "Hospital Admin")
    app.dependency_overrides[get_db] = lambda: BrokenDb()
    try:
        r = client.get("/api/analytics/kpis", headers=h)
    finally:
        app.dependency_overrides[get_db] = lambda: Sqlite3Database()
    assert r.status_code == 503
    assert "database" in r.json()["detail"].lower()
