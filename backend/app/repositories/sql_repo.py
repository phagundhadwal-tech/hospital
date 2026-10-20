"""
app/repositories/sql_repo.py
============================
All SQL Server queries for the dashboard.  Every function takes a Database
handle and a validated Filters object and returns plain Python rows.

SAFETY
  * User-controlled values are bound parameters (:dept, :start, ...), never
    concatenated into SQL text.
  * The only text interpolated into SQL are table names (from settings,
    validated as identifiers) and column names/fragments written in this file.

DATA RULES (see docs/METRICS.md)
  * Admissions  = visits with Admission_Time, counted by Admission_Time date.
  * Discharges  = visits with Discharge_Time, counted by Discharge_Time date.
  * Wait time   = Consultation_Start_Time - Registration_Time in minutes, only
                  when both exist and the result is >= 0.
  * Occupancy   = Occupied beds / (all beds - Maintenance beds) * 100.
  * Current admissions = Visit_Status 'Ongoing' with Admission_Time and no
                  Discharge_Time (a snapshot; not date filtered).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.analytics.filters import Filters
from app.core.constants import (
    BED_AVAILABLE,
    BED_MAINTENANCE,
    BED_OCCUPIED,
    BED_RESERVED,
    REASON_NOT_APPLICABLE,
    STATUS_CANCELLED,
    STATUS_ONGOING,
    T_BED_ASSIGNMENTS,
    T_BEDS,
    T_DEPARTMENTS,
    T_PATIENTS,
    T_STAFF,
    T_VISITS,
    T_WARDS,
    UNASSIGNED_DEPARTMENT,
)
from app.db.dialect import day_bucket, hour_of_day, minutes_between, year_month


# ── small SQL builders ────────────────────────────────────────────────────────

def _and(*conds: str) -> str:
    return " AND ".join(c for c in conds if c) or "1=1"


def _in_range(col: str, f: Filters) -> str:
    parts = []
    if f.start is not None:
        parts.append(f"{col} >= :start")
    if f.end_exclusive is not None:
        parts.append(f"{col} < :end_excl")
    return " AND ".join(parts)


def _visit_base(f: Filters, alias: str = "", include_dept: bool = True) -> str:
    p = f"{alias}." if alias else ""
    parts = []
    if include_dept and f.department_id is not None:
        parts.append(f"{p}Department_ID = :dept")
    if f.visit_type is not None:
        parts.append(f"{p}Visit_Type = :vtype")
    if f.visit_status is not None:
        parts.append(f"{p}Visit_Status = :vstatus")
    return " AND ".join(parts)


def _params(f: Filters) -> dict[str, Any]:
    p: dict[str, Any] = {}
    if f.start is not None:
        p["start"] = f.start
    if f.end_exclusive is not None:
        p["end_excl"] = f.end_exclusive
    if f.department_id is not None:
        p["dept"] = f.department_id
    if f.visit_type is not None:
        p["vtype"] = f.visit_type
    if f.visit_status is not None:
        p["vstatus"] = f.visit_status
    return p


def _i(v: Any) -> int:
    return int(v) if v is not None else 0


# ── Departments ───────────────────────────────────────────────────────────────

def departments(db, department_id: int | None = None) -> list[dict]:
    sql = f"SELECT Department_ID, Department_Name FROM {db.table('Departments')}"
    params: dict[str, Any] = {}
    if department_id is not None:
        sql += " WHERE Department_ID = :dept"
        params["dept"] = department_id
    sql += " ORDER BY Department_Name"
    return db.query(sql, params)


# ── Visit KPIs ────────────────────────────────────────────────────────────────

def visit_kpis(db, f: Filters) -> dict[str, Any]:
    vt = db.table(T_VISITS)
    wait = minutes_between(db.dialect, "Registration_Time", "Consultation_Start_Time")

    adm  = _and("Admission_Time IS NOT NULL", _in_range("Admission_Time", f))
    dis  = _and("Discharge_Time IS NOT NULL", _in_range("Discharge_Time", f))
    reg  = _and(_in_range("Registration_Time", f))
    wcnd = _and("Consultation_Start_Time IS NOT NULL", f"{wait} >= 0", _in_range("Registration_Time", f))
    cur  = f"Visit_Status = '{STATUS_ONGOING}' AND Admission_Time IS NOT NULL AND Discharge_Time IS NULL"
    waiting = (f"Visit_Status = '{STATUS_ONGOING}' AND Consultation_Start_Time IS NULL "
               f"AND Admission_Time IS NULL")

    sql = f"""
        SELECT
            SUM(CASE WHEN {reg}  THEN 1 ELSE 0 END)                         AS total_visits,
            SUM(CASE WHEN {adm}  THEN 1 ELSE 0 END)                         AS admissions,
            SUM(CASE WHEN {dis}  THEN 1 ELSE 0 END)                         AS discharges,
            AVG(CASE WHEN {wcnd} THEN CAST({wait} AS FLOAT) END)            AS avg_wait_minutes,
            SUM(CASE WHEN {wcnd} THEN 1 ELSE 0 END)                         AS wait_samples,
            SUM(CASE WHEN {cur}  THEN 1 ELSE 0 END)                         AS current_admissions,
            SUM(CASE WHEN {waiting} THEN 1 ELSE 0 END)                      AS waiting_now
        FROM {vt}
        WHERE {_and(_visit_base(f))}
    """
    row = db.query(sql, _params(f))[0]
    avg = row["avg_wait_minutes"]
    return {
        "total_visits":       _i(row["total_visits"]),
        "admissions":         _i(row["admissions"]),
        "discharges":         _i(row["discharges"]),
        "avg_wait_minutes":   round(float(avg), 1) if avg is not None else None,
        "wait_samples":       _i(row["wait_samples"]),
        "current_admissions": _i(row["current_admissions"]),
        "waiting_now":        _i(row["waiting_now"]),
    }


def _avg(v: Any, places: int = 1) -> float | None:
    return round(float(v), places) if v is not None else None


def care_timings(db, f: Filters) -> dict[str, Any]:
    """
    Average durations for the doctor view. Each average only uses rows where both
    timestamps exist and the duration is >= 0; the matching *_samples count says how
    many rows that was (Triage_Time is empty for many visits, so it is much smaller).
    Stage metrics follow Registration_Time in range; length of stay follows Discharge_Time.
    """
    vt, d = db.table(T_VISITS), db.dialect
    to_triage  = minutes_between(d, "Registration_Time", "Triage_Time")
    triage_to  = minutes_between(d, "Triage_Time", "Consultation_Start_Time")
    consult    = minutes_between(d, "Consultation_Start_Time", "Consultation_End_Time")
    stay       = minutes_between(d, "Admission_Time", "Discharge_Time")

    reg = _in_range("Registration_Time", f)
    c_tri  = _and(f"{to_triage} >= 0", reg)
    c_wait = _and(f"{triage_to} >= 0", reg)
    c_cons = _and(f"{consult} >= 0", reg)
    c_stay = _and(f"{stay} >= 0", _in_range("Discharge_Time", f))

    sql = f"""
        SELECT
            AVG(CASE WHEN {c_tri}  THEN CAST({to_triage} AS FLOAT) END) AS reg_to_triage,
            SUM(CASE WHEN {c_tri}  THEN 1 ELSE 0 END)                   AS reg_to_triage_n,
            AVG(CASE WHEN {c_wait} THEN CAST({triage_to} AS FLOAT) END) AS triage_to_consult,
            SUM(CASE WHEN {c_wait} THEN 1 ELSE 0 END)                   AS triage_to_consult_n,
            AVG(CASE WHEN {c_cons} THEN CAST({consult} AS FLOAT) END)   AS consult_len,
            SUM(CASE WHEN {c_cons} THEN 1 ELSE 0 END)                   AS consult_len_n,
            AVG(CASE WHEN {c_stay} THEN CAST({stay} AS FLOAT) END)      AS stay_minutes,
            SUM(CASE WHEN {c_stay} THEN 1 ELSE 0 END)                   AS stay_n
        FROM {vt}
        WHERE {_and(_visit_base(f))}
    """
    r = db.query(sql, _params(f))[0]
    stay_min = _avg(r["stay_minutes"], 4)
    return {
        "reg_to_triage_min":     _avg(r["reg_to_triage"]),
        "reg_to_triage_n":       _i(r["reg_to_triage_n"]),
        "triage_to_consult_min": _avg(r["triage_to_consult"]),
        "triage_to_consult_n":   _i(r["triage_to_consult_n"]),
        "consultation_min":      _avg(r["consult_len"]),
        "consultation_n":        _i(r["consult_len_n"]),
        "avg_stay_hours":        round(stay_min / 60, 1) if stay_min is not None else None,
        "stay_n":                _i(r["stay_n"]),
    }


def visits_by_hour(db, f: Filters) -> list[dict]:
    vt   = db.table(T_VISITS)
    hour = hour_of_day(db.dialect, "Registration_Time")
    sql = f"""
        SELECT {hour} AS hr, COUNT(*) AS cnt
        FROM {vt}
        WHERE {_and(_in_range('Registration_Time', f), _visit_base(f))}
        GROUP BY {hour}
    """
    counts = {int(r["hr"]): _i(r["cnt"]) for r in db.query(sql, _params(f))}
    return [{"hour": h, "count": counts.get(h, 0)} for h in range(24)]


def cancellation_reasons(db, f: Filters) -> list[dict]:
    vt = db.table(T_VISITS)
    label = (f"CASE WHEN Reason_for_cancellation IS NULL OR Reason_for_cancellation = '{REASON_NOT_APPLICABLE}' "
             f"THEN 'Not recorded' ELSE Reason_for_cancellation END")
    where = _and(f"Visit_Status = '{STATUS_CANCELLED}'", _in_range("Registration_Time", f), _visit_base(f))
    sql = f"""
        SELECT {label} AS label, COUNT(*) AS cnt
        FROM {vt}
        WHERE {where}
        GROUP BY {label}
        ORDER BY cnt DESC, label
    """
    return [{"label": r["label"], "count": _i(r["cnt"])} for r in db.query(sql, _params(f))]


def _to_date(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return datetime.fromisoformat(str(v).replace("T", " ")).date()


def data_range(db, department_id: int | None) -> dict[str, str | None]:
    """First and last day that has a registered visit (used to anchor the date presets)."""
    vt = db.table(T_VISITS)
    dep = "WHERE Department_ID = :dept" if department_id is not None else ""
    params = {"dept": department_id} if department_id is not None else {}
    r = db.query(f"SELECT MIN(Registration_Time) AS lo, MAX(Registration_Time) AS hi FROM {vt} {dep}", params)[0]
    lo, hi = _to_date(r["lo"]), _to_date(r["hi"])
    return {"earliest": lo.isoformat() if lo else None, "latest": hi.isoformat() if hi else None}


MAX_ARRIVAL_DAYS = 366      # longest window returned
WEEKLY_AFTER_DAYS = 92      # longer windows are summed per week so the chart stays readable


def recent_arrivals(db, f: Filters, default_days: int = 14) -> dict[str, Any]:
    """
    Visits registered per day (or per week for long windows), split by visit type.
    Without dates the window is the `default_days` days ending on the most recent
    Registration_Time in scope (not on the wall clock), so a department whose data stops
    a few days ago still shows its latest activity. With start/end dates it follows them.
    """
    vt  = db.table(T_VISITS)
    dep = "Department_ID = :dept" if f.department_id is not None else ""
    params: dict[str, Any] = {"dept": f.department_id} if f.department_id is not None else {}
    latest = _to_date(db.query(f"SELECT MAX(Registration_Time) AS m FROM {vt} WHERE {_and(dep)}", params)[0]["m"])
    if latest is None:
        return {"through": None, "bucket": "day", "days": []}

    last = (f.end_exclusive - timedelta(days=1)).date() if f.end_exclusive else latest
    first = f.start.date() if f.start else last - timedelta(days=default_days - 1)
    first = max(first, last - timedelta(days=MAX_ARRIVAL_DAYS - 1))
    if first > last:
        return {"through": last.isoformat(), "bucket": "day", "days": []}

    day = day_bucket(db.dialect, "Registration_Time")
    sql = f"""
        SELECT {day} AS d, Visit_Type AS vtype, COUNT(*) AS cnt
        FROM {vt}
        WHERE {_and('Registration_Time >= :s', 'Registration_Time < :e', dep)}
        GROUP BY {day}, Visit_Type
    """
    params.update(s=datetime.combine(first, datetime.min.time()),
                  e=datetime.combine(last + timedelta(days=1), datetime.min.time()))
    by_day: dict[str, dict[str, int]] = {}
    for r in db.query(sql, params):
        by_day.setdefault(str(r["d"]), {})[r["vtype"]] = _i(r["cnt"])

    span = (last - first).days + 1
    weekly = span > WEEKLY_AFTER_DAYS
    buckets: dict[str, dict[str, int]] = {}
    for n in range(span):
        d = first + timedelta(days=n)
        key = (d - timedelta(days=d.weekday())).isoformat() if weekly else d.isoformat()
        slot = buckets.setdefault(key, {})
        for t, c in by_day.get(d.isoformat(), {}).items():
            slot[t] = slot.get(t, 0) + c
    return {
        "through": last.isoformat(),
        "bucket":  "week" if weekly else "day",
        "days":    [{"date": k, "total": sum(v.values()), "by_type": v} for k, v in buckets.items()],
    }


# ── Nurse view: staffing, current patients, bed stays ─────────────────────────

def staff_by_shift(db, department_id: int | None) -> list[dict]:
    st = db.table(T_STAFF)
    where = "AND Department_ID = :dept" if department_id is not None else ""
    sql = f"""
        SELECT Staff_Shift AS shift, Staff_Role AS role, COUNT(*) AS cnt
        FROM {st}
        WHERE Staff_Shift IS NOT NULL AND Staff_Role IN ('Nurse', 'Doctor') {where}
        GROUP BY Staff_Shift, Staff_Role
    """
    params = {"dept": department_id} if department_id is not None else {}
    return [{"shift": r["shift"], "role": r["role"], "count": _i(r["cnt"])} for r in db.query(sql, params)]


def current_patient_birthdates(db, department_id: int | None) -> list[Any]:
    """Date_Of_Birth of every patient currently admitted (same rule as Active Patients)."""
    vt, pt = db.table(T_VISITS), db.table(T_PATIENTS)
    where = "AND v.Department_ID = :dept" if department_id is not None else ""
    sql = f"""
        SELECT p.Date_Of_Birth AS dob
        FROM {vt} v
        JOIN {pt} p ON p.Patient_ID = v.Patient_ID
        WHERE v.Visit_Status = '{STATUS_ONGOING}' AND v.Admission_Time IS NOT NULL
          AND v.Discharge_Time IS NULL {where}
    """
    params = {"dept": department_id} if department_id is not None else {}
    return [r["dob"] for r in db.query(sql, params)]


def bed_stay(db, f: Filters) -> dict[str, Any]:
    """Average length of a finished bed assignment, for beds in the caller's department wards."""
    ba, beds, wards = db.table(T_BED_ASSIGNMENTS), db.table(T_BEDS), db.table(T_WARDS)
    stay = minutes_between(db.dialect, "a.Assignment_Start", "a.Assignment_End")
    cond = _and("a.Assignment_End IS NOT NULL", f"{stay} >= 0", _in_range("a.Assignment_End", f),
                "w.Department_ID = :dept" if f.department_id is not None else "")
    sql = f"""
        SELECT AVG(CAST({stay} AS FLOAT)) AS avg_min, COUNT(*) AS n
        FROM {ba} a
        JOIN {beds}  b ON b.Bed_ID  = a.Bed_ID
        JOIN {wards} w ON w.Ward_ID = b.Ward_ID
        WHERE {cond}
    """
    params = {k: v for k, v in _params(f).items() if k in ("start", "end_excl", "dept")}
    r = db.query(sql, params)[0]
    avg = _avg(r["avg_min"], 4)
    return {"avg_hours": round(avg / 60, 1) if avg is not None else None, "samples": _i(r["n"])}


def monthly_trend(db, f: Filters) -> list[dict]:
    vt   = db.table(T_VISITS)
    base = _visit_base(f)
    a_m  = year_month(db.dialect, "Admission_Time")
    d_m  = year_month(db.dialect, "Discharge_Time")
    sql = f"""
        SELECT m AS month, SUM(a) AS admissions, SUM(d) AS discharges
        FROM (
            SELECT {a_m} AS m, 1 AS a, 0 AS d FROM {vt}
             WHERE {_and('Admission_Time IS NOT NULL', _in_range('Admission_Time', f), base)}
            UNION ALL
            SELECT {d_m} AS m, 0 AS a, 1 AS d FROM {vt}
             WHERE {_and('Discharge_Time IS NOT NULL', _in_range('Discharge_Time', f), base)}
        ) x
        GROUP BY m
        ORDER BY m
    """
    return [
        {"month": r["month"], "admissions": _i(r["admissions"]), "discharges": _i(r["discharges"])}
        for r in db.query(sql, _params(f))
    ]


def dept_activity(db, f: Filters) -> list[dict]:
    dep = db.table(T_DEPARTMENTS)
    vt  = db.table(T_VISITS)
    other = _visit_base(f, alias="v", include_dept=False)
    visit_cond = _and("v.Visit_ID IS NOT NULL", _in_range("v.Registration_Time", f), other)
    adm_cond   = _and("v.Admission_Time IS NOT NULL", _in_range("v.Admission_Time", f), other)
    where = "WHERE d.Department_ID = :dept" if f.department_id is not None else ""
    sql = f"""
        SELECT d.Department_ID AS department_id,
               d.Department_Name AS department_name,
               SUM(CASE WHEN {visit_cond} THEN 1 ELSE 0 END) AS visit_count,
               SUM(CASE WHEN {adm_cond}   THEN 1 ELSE 0 END) AS admission_count
        FROM {dep} d
        LEFT JOIN {vt} v ON v.Department_ID = d.Department_ID
        {where}
        GROUP BY d.Department_ID, d.Department_Name
        ORDER BY visit_count DESC, d.Department_Name
    """
    return [
        {"department_id": str(r["department_id"]), "department_name": r["department_name"],
         "visit_count": _i(r["visit_count"]), "admission_count": _i(r["admission_count"])}
        for r in db.query(sql, _params(f))
    ]


def _visit_breakdown(db, f: Filters, column: str) -> list[dict]:
    vt = db.table(T_VISITS)
    where = _and(_in_range("Registration_Time", f), _visit_base(f))
    sql = f"""
        SELECT {column} AS label, COUNT(*) AS cnt
        FROM {vt}
        WHERE {where}
        GROUP BY {column}
        ORDER BY cnt DESC, {column}
    """
    return [{"label": r["label"], "count": _i(r["cnt"])} for r in db.query(sql, _params(f))]


def visit_type_counts(db, f: Filters) -> list[dict]:
    return _visit_breakdown(db, f, "Visit_Type")


def visit_status_counts(db, f: Filters) -> list[dict]:
    return _visit_breakdown(db, f, "Visit_Status")


# ── Beds & wards (current snapshot) ───────────────────────────────────────────

def ward_bed_rows(db, department_id: int | None) -> list[dict]:
    wards, beds, dep = db.table(T_WARDS), db.table(T_BEDS), db.table(T_DEPARTMENTS)
    where = "WHERE w.Department_ID = :dept" if department_id is not None else ""
    sql = f"""
        SELECT w.Ward_ID AS ward_id, w.Ward_Name AS ward_name, w.Ward_Type AS ward_type,
               w.Department_ID AS department_id,
               COALESCE(dep.Department_Name, '{UNASSIGNED_DEPARTMENT}') AS department_name,
               COUNT(b.Bed_ID) AS total_beds,
               SUM(CASE WHEN b.Bed_Status = '{BED_OCCUPIED}'    THEN 1 ELSE 0 END) AS occupied,
               SUM(CASE WHEN b.Bed_Status = '{BED_AVAILABLE}'   THEN 1 ELSE 0 END) AS available,
               SUM(CASE WHEN b.Bed_Status = '{BED_MAINTENANCE}' THEN 1 ELSE 0 END) AS maintenance,
               SUM(CASE WHEN b.Bed_Status = '{BED_RESERVED}'    THEN 1 ELSE 0 END) AS reserved
        FROM {wards} w
        LEFT JOIN {dep}  dep ON dep.Department_ID = w.Department_ID
        LEFT JOIN {beds} b   ON b.Ward_ID = w.Ward_ID
        {where}
        GROUP BY w.Ward_ID, w.Ward_Name, w.Ward_Type, w.Department_ID, dep.Department_Name
        ORDER BY w.Ward_ID
    """
    params = {"dept": department_id} if department_id is not None else {}
    out = []
    for r in db.query(sql, params):
        out.append({
            "ward_id": str(r["ward_id"]), "ward_name": r["ward_name"], "ward_type": r["ward_type"],
            "department_id": str(r["department_id"]), "department_name": r["department_name"],
            "total_beds": _i(r["total_beds"]), "occupied": _i(r["occupied"]),
            "available": _i(r["available"]), "maintenance": _i(r["maintenance"]),
            "reserved": _i(r["reserved"]),
        })
    return out


def bed_status_counts(db, department_id: int | None) -> list[dict]:
    wards, beds = db.table(T_WARDS), db.table(T_BEDS)
    where = "WHERE w.Department_ID = :dept" if department_id is not None else ""
    sql = f"""
        SELECT b.Bed_Status AS label, COUNT(*) AS cnt
        FROM {beds} b
        JOIN {wards} w ON w.Ward_ID = b.Ward_ID
        {where}
        GROUP BY b.Bed_Status
        ORDER BY cnt DESC, b.Bed_Status
    """
    params = {"dept": department_id} if department_id is not None else {}
    return [{"label": r["label"], "count": _i(r["cnt"])} for r in db.query(sql, params)]


# ── Data-quality checks (read-only) ───────────────────────────────────────────

def data_quality(db) -> list[dict]:
    vt, ba, beds, wards = (db.table(n) for n in (T_VISITS, T_BED_ASSIGNMENTS, T_BEDS, T_WARDS))
    d = db.dialect
    wait   = minutes_between(d, "Registration_Time", "Consultation_Start_Time")
    tri    = minutes_between(d, "Triage_Time", "Consultation_Start_Time")
    reg_tr = minutes_between(d, "Registration_Time", "Triage_Time")
    stay   = minutes_between(d, "Admission_Time", "Discharge_Time")

    checks = [
        ("negative_wait_duration",
         "Visits where consultation starts BEFORE registration (excluded from wait averages)",
         f"SELECT COUNT(*) AS n FROM {vt} WHERE {wait} < 0"),
        ("negative_triage_to_consultation",
         "Visits where consultation starts BEFORE triage",
         f"SELECT COUNT(*) AS n FROM {vt} WHERE {tri} < 0"),
        ("triage_before_registration",
         "Visits where triage is BEFORE registration",
         f"SELECT COUNT(*) AS n FROM {vt} WHERE {reg_tr} < 0"),
        ("discharge_before_admission",
         "Visits where discharge is BEFORE admission",
         f"SELECT COUNT(*) AS n FROM {vt} WHERE {stay} < 0"),
        ("discharge_without_admission",
         "Visits with a Discharge_Time but no Admission_Time",
         f"SELECT COUNT(*) AS n FROM {vt} WHERE Discharge_Time IS NOT NULL AND Admission_Time IS NULL"),
        ("visits_without_consultation_start",
         "Visits with no Consultation_Start_Time (cancelled / not yet seen; excluded from wait averages)",
         f"SELECT COUNT(*) AS n FROM {vt} WHERE Consultation_Start_Time IS NULL"),
        ("bed_assignments_unknown_bed",
         "Bed assignments whose Bed_ID does not exist in Beds",
         f"SELECT COUNT(*) AS n FROM {ba} a LEFT JOIN {beds} b ON b.Bed_ID = a.Bed_ID WHERE b.Bed_ID IS NULL"),
        ("occupied_beds_without_active_assignment",
         "Beds marked Occupied that have no open (Assignment_End IS NULL) assignment",
         f"SELECT COUNT(*) AS n FROM {beds} b WHERE b.Bed_Status = '{BED_OCCUPIED}' AND NOT EXISTS "
         f"(SELECT 1 FROM {ba} a WHERE a.Bed_ID = b.Bed_ID AND a.Assignment_End IS NULL)"),
        ("wards_bed_count_differs_from_capacity",
         "Wards whose number of Beds rows differs from Wards.Capacity",
         f"SELECT COUNT(*) AS n FROM (SELECT w.Ward_ID FROM {wards} w LEFT JOIN {beds} b ON b.Ward_ID = w.Ward_ID "
         f"GROUP BY w.Ward_ID, w.Capacity HAVING COUNT(b.Bed_ID) <> COALESCE(w.Capacity, 0)) t"),
    ]
    return [{"check": key, "description": desc, "count": _i(db.query(sql)[0]["n"])}
            for key, desc, sql in checks]
