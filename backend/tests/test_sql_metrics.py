"""
Repository / service SQL checked against an independent pandas calculation on
the V6 CSV files.  Runs the same SQL the API uses (SQLite dialect fragments).
"""

from __future__ import annotations

import pandas as pd
import pytest

import csv_expected as ce
from app.analytics import service as svc
from app.analytics.filters import build_filters
from app.core.exceptions import BadRequestError, ForbiddenError
from app.repositories import sql_repo as repo
from tests.helpers import DATA_DIR, Sqlite3Database

CASES = [
    (None, None, None),
    ("2026-06-01", "2026-06-30", None),
    ("2026-05-01", None, 1),
    (None, "2026-08-31", 3),
    ("2026-10-19", "2026-10-19", None),      # single day, end date must be inclusive
    ("2030-01-01", "2030-12-31", None),      # empty result
    ("2026-07-15", "2026-07-15", 2),
]


@pytest.fixture(scope="module")
def db():
    return Sqlite3Database()


@pytest.fixture(scope="module")
def csv():
    return ce.load(DATA_DIR)


@pytest.mark.parametrize("start,end,dept", CASES)
def test_visit_kpis_match_csv(db, csv, start, end, dept):
    v = csv[0]
    f = build_filters(start, end, str(dept) if dept else None)
    got, exp = repo.visit_kpis(db, f), ce.expected_visit_metrics(v, start, end, dept)
    for key in ("total_visits", "admissions", "discharges", "avg_wait_minutes", "wait_samples", "current_admissions"):
        assert got[key] == exp[key], key


@pytest.mark.parametrize("start,end,dept", CASES)
def test_trend_and_breakdowns_match_csv(db, csv, start, end, dept):
    v = csv[0]
    f = build_filters(start, end, str(dept) if dept else None)
    exp = ce.expected_visit_metrics(v, start, end, dept)
    trend = {r["month"]: (r["admissions"], r["discharges"]) for r in repo.monthly_trend(db, f)}
    assert trend == exp["trend"]
    pf = svc.patient_flow(db, f)
    assert {r["visit_type"]: r["count"] for r in pf["visit_type_breakdown"]} == exp["visit_type"]
    assert {r["status"]: r["count"] for r in pf["status_breakdown"]} == exp["visit_status"]


@pytest.mark.parametrize("dept", [None, 1, 2, 3, 4])
def test_bed_metrics_match_csv(db, csv, dept):
    _, beds, wards, _, _ = csv
    got, exp = svc.bed_availability(db, dept), ce.expected_bed_metrics(beds, wards, dept)
    for key, value in exp.items():
        assert got[key] == value, key
    assert sum(w["total_beds"] for w in got["ward_occupancy"]) == exp["total_beds"]
    assert sum(s["count"] for s in got["status_breakdown"]) == exp["total_beds"]


def test_maintenance_beds_never_counted_available(db):
    b = svc.bed_availability(db, None)
    assert b["available"] + b["occupied"] + b["maintenance"] + b["reserved"] == b["total_beds"]
    assert b["operational_beds"] == b["total_beds"] - b["maintenance"]


def test_current_admissions_equal_occupied_beds(db):
    assert repo.visit_kpis(db, build_filters())["current_admissions"] == svc.bed_availability(db, None)["occupied"]


def test_negative_wait_is_excluded_and_flagged(csv):
    """Inject one visit whose consultation starts before registration."""
    local = Sqlite3Database()
    local.execute(
        "INSERT INTO Patient_Visits (Visit_ID, Patient_ID, Department_ID, Visit_Type, Registration_Time, "
        "Consultation_Start_Time, Visit_Status) VALUES (999999, 1, 1, 'Emergency', '2026-06-10 10:00:00', "
        "'2026-06-10 09:00:00', 'Completed')")
    f = build_filters("2026-06-10", "2026-06-10")
    k = repo.visit_kpis(local, f)
    assert k["wait_samples"] == repo.visit_kpis(Sqlite3Database(), f)["wait_samples"]      # not counted
    assert {r["check"]: r["count"] for r in repo.data_quality(local)}["negative_wait_duration"] == 1


def test_percentages_never_divide_by_zero():
    assert svc.pct(0, 0) == 0.0
    assert svc.occupancy_pct(0, 5, 5) == 0.0


def test_filter_validation():
    with pytest.raises(BadRequestError):
        build_filters("2026-13-45")
    with pytest.raises(BadRequestError):
        build_filters("2026-07-02", "2026-07-01")
    with pytest.raises(BadRequestError):
        build_filters(department_id="abc")
    with pytest.raises(ForbiddenError):
        build_filters(dept_scope="DEPT-001")
    # scoped role: the query-string department can never override the token's department
    assert build_filters(department_id="1", dept_scope="3").department_id == 3


def test_injection_string_is_just_a_value(db):
    f = build_filters(visit_type="x'; DROP TABLE Patient_Visits;--")
    assert repo.visit_kpis(db, f)["total_visits"] == 0
    assert db.query("SELECT COUNT(*) AS n FROM Patient_Visits")[0]["n"] == 3905


# ── doctor / nurse insights ────────────────────────────────────────────────────

@pytest.mark.parametrize("dept", [None, 1, 2])
def test_care_timings_and_hours_match_csv(db, csv, dept):
    v = csv[0].copy()
    if dept:
        v = v[v["Department_ID"] == dept]
    f = build_filters(None, None, str(dept) if dept else None)
    t = repo.care_timings(db, f)

    def mean_n(a, b):
        d = (pd.to_datetime(v[b]) - pd.to_datetime(v[a])).dt.total_seconds() / 60
        d = d[d >= 0]
        return round(d.mean(), 1), len(d)

    assert (t["consultation_min"], t["consultation_n"]) == mean_n("Consultation_Start_Time", "Consultation_End_Time")
    assert (t["reg_to_triage_min"], t["reg_to_triage_n"]) == mean_n("Registration_Time", "Triage_Time")
    hours = repo.visits_by_hour(db, f)
    assert len(hours) == 24 and sum(h["count"] for h in hours) == len(v)


def test_cancellation_reasons_sum_to_cancelled_visits(db, csv):
    v = csv[0]
    f = build_filters()
    reasons = svc.patient_flow(db, f)["cancellation_reasons"]
    assert sum(r["count"] for r in reasons) == int((v["Visit_Status"] == "Cancelled").sum())
    assert "Not Applicable" not in {r["reason"] for r in reasons}


@pytest.mark.parametrize("dept", [None, 2])
def test_nurse_insights_shape_and_totals(db, dept):
    f = build_filters(None, None, str(dept) if dept else None)
    n = svc.nurse_insights(db, f)
    assert sum(a["count"] for a in n["age_groups"]) == repo.visit_kpis(db, f)["current_admissions"]
    assert len(n["busiest_wards"]) <= 5
    pcts = [w["occupancy_pct"] for w in n["busiest_wards"]]
    assert pcts == sorted(pcts, reverse=True)
    assert [s["shift"] for s in n["staff_by_shift"]] == ["Morning", "Evening", "Night"]


@pytest.mark.parametrize("dept", [None, 1, 3])
def test_recent_arrivals_match_csv(db, csv, dept):
    v = csv[0].copy()
    if dept:
        v = v[v["Department_ID"] == dept]
    r = repo.recent_arrivals(db, build_filters(None, None, str(dept) if dept else None))
    reg = pd.to_datetime(v["Registration_Time"])
    last = reg.max().normalize()
    assert r["through"] == last.date().isoformat()
    assert len(r["days"]) == 14
    window = reg[reg >= last - pd.Timedelta(days=13)]
    assert sum(d["total"] for d in r["days"]) == len(window)
    assert all(d["total"] == sum(d["by_type"].values()) for d in r["days"])


def test_recent_arrivals_follow_dates_and_go_weekly_when_long(db, csv):
    v = csv[0]
    reg = pd.to_datetime(v["Registration_Time"])
    short = repo.recent_arrivals(db, build_filters("2026-09-01", "2026-09-10"))
    assert short["bucket"] == "day" and len(short["days"]) == 10
    assert sum(d["total"] for d in short["days"]) == int(((reg >= "2026-09-01") & (reg < "2026-09-11")).sum())

    everything = repo.recent_arrivals(db, build_filters(reg.min().date().isoformat(), reg.max().date().isoformat()))
    assert everything["bucket"] == "week"
    assert sum(d["total"] for d in everything["days"]) == len(v)

    assert repo.recent_arrivals(db, build_filters("2030-01-01", "2030-01-07"))["days"][0]["total"] == 0


def test_data_range_matches_csv(db, csv):
    reg = pd.to_datetime(csv[0]["Registration_Time"])
    r = repo.data_range(db, None)
    assert r == {"earliest": reg.min().date().isoformat(), "latest": reg.max().date().isoformat()}
