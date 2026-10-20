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

from typing import Any

from app.analytics.filters import Filters
from app.db.dialect import minutes_between, year_month

STATUS_ONGOING = "Ongoing"
BED_OCCUPIED = "Occupied"
BED_AVAILABLE = "Available"
BED_MAINTENANCE = "Maintenance"
BED_RESERVED = "Reserved"


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
    vt = db.table("Patient_Visits")
    wait = minutes_between(db.dialect, "Registration_Time", "Consultation_Start_Time")

    adm  = _and("Admission_Time IS NOT NULL", _in_range("Admission_Time", f))
    dis  = _and("Discharge_Time IS NOT NULL", _in_range("Discharge_Time", f))
    reg  = _and(_in_range("Registration_Time", f))
    wcnd = _and("Consultation_Start_Time IS NOT NULL", f"{wait} >= 0", _in_range("Registration_Time", f))
    cur  = f"Visit_Status = '{STATUS_ONGOING}' AND Admission_Time IS NOT NULL AND Discharge_Time IS NULL"

    sql = f"""
        SELECT
            SUM(CASE WHEN {reg}  THEN 1 ELSE 0 END)                         AS total_visits,
            SUM(CASE WHEN {adm}  THEN 1 ELSE 0 END)                         AS admissions,
            SUM(CASE WHEN {dis}  THEN 1 ELSE 0 END)                         AS discharges,
            AVG(CASE WHEN {wcnd} THEN CAST({wait} AS FLOAT) END)            AS avg_wait_minutes,
            SUM(CASE WHEN {wcnd} THEN 1 ELSE 0 END)                         AS wait_samples,
            SUM(CASE WHEN {cur}  THEN 1 ELSE 0 END)                         AS current_admissions
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
    }


def monthly_trend(db, f: Filters) -> list[dict]:
    vt   = db.table("Patient_Visits")
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
    dep = db.table("Departments")
    vt  = db.table("Patient_Visits")
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
    vt = db.table("Patient_Visits")
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
    wards, beds, dep = db.table("Wards"), db.table("Beds"), db.table("Departments")
    where = "WHERE w.Department_ID = :dept" if department_id is not None else ""
    sql = f"""
        SELECT w.Ward_ID AS ward_id, w.Ward_Name AS ward_name, w.Ward_Type AS ward_type,
               w.Department_ID AS department_id,
               COALESCE(dep.Department_Name, 'Unassigned') AS department_name,
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
    wards, beds = db.table("Wards"), db.table("Beds")
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
    vt, ba, beds, wards = (db.table(n) for n in ("Patient_Visits", "Bed_Assignments", "Beds", "Wards"))
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

def patient_flow(db, f):
    visits = db.table("Patient_Visits")
    departments = db.table("Departments")

    sql = f"""
        SELECT
            d.Department_ID AS department_id,
            d.Department_Name AS department_name,
            COUNT(v.Visit_ID) AS patient_count,
            AVG(
                CASE
                    WHEN v.Registration_Time IS NOT NULL
                     AND v.Triage_Time IS NOT NULL
                     AND v.Triage_Time >= v.Registration_Time
                    THEN DATEDIFF(
                        MINUTE,
                        v.Registration_Time,
                        v.Triage_Time
                    )
                END
            ) AS avg_wait_minutes
        FROM {visits} v
        LEFT JOIN {departments} d
            ON v.Department_ID = d.Department_ID
        WHERE 1 = 1
    """

    params = {}

    if getattr(f, "department_id", None):
        sql += " AND v.Department_ID = :dept"
        params["dept"] = f.department_id

    sql += """
        GROUP BY d.Department_ID, d.Department_Name
        ORDER BY patient_count DESC
    """

    return db.query(sql, params)
