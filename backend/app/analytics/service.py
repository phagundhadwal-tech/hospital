"""
app/analytics/service.py
========================
Business logic between the SQL repository and the API layer.

The repository returns counts straight from SQL Server aggregates; this layer
only does the arithmetic that must be identical everywhere (percentages,
occupancy denominator) and shapes rows into the response models.
No HTTP and no FastAPI in here.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.analytics.filters import Filters
from app.repositories import sql_repo as repo


def pct(part: int, total: int) -> float:
    """Percentage rounded to 1 decimal; 0.0 when the denominator is 0 (no ZeroDivisionError)."""
    return round(part / total * 100, 1) if total else 0.0


def occupancy_pct(occupied: int, total: int, maintenance: int) -> float:
    """Occupied ÷ operational beds × 100, where operational = total − maintenance."""
    return pct(occupied, max(total - maintenance, 0))


# ── Overview / patient flow ───────────────────────────────────────────────────

def kpis(db, f: Filters) -> dict[str, Any]:
    k = repo.visit_kpis(db, f)
    beds = bed_availability(db, f.department_id)
    return {
        "admissions":         k["admissions"],
        "discharges":         k["discharges"],
        "avg_wait_minutes":   k["avg_wait_minutes"],
        "bed_occupancy_pct":  beds["occupancy_pct"],
        "current_admissions": k["current_admissions"],
        "wait_samples":       k["wait_samples"],
        "waiting_now":        k["waiting_now"],
    }


def recent_arrivals(db, f: Filters) -> dict[str, Any]:
    return repo.recent_arrivals(db, f)


def data_range(db, f: Filters) -> dict[str, str | None]:
    return repo.data_range(db, f.department_id)


def monthly_trend(db, f: Filters) -> list[dict]:
    return repo.monthly_trend(db, f)


def dept_activity(db, f: Filters) -> list[dict]:
    return repo.dept_activity(db, f)


def _with_pct(rows: list[dict], key: str) -> list[dict]:
    total = sum(r["count"] for r in rows)
    return [{key: r["label"], "count": r["count"], "pct": pct(r["count"], total)} for r in rows]


def patient_flow(db, f: Filters) -> dict[str, Any]:
    k = repo.visit_kpis(db, f)
    return {
        "total_visits":         k["total_visits"],
        "admissions":           k["admissions"],
        "discharges":           k["discharges"],
        "avg_wait_minutes":     k["avg_wait_minutes"],
        "visit_type_breakdown": _with_pct(repo.visit_type_counts(db, f), "visit_type"),
        "status_breakdown":     _with_pct(repo.visit_status_counts(db, f), "status"),
        "monthly_trend":        repo.monthly_trend(db, f),
        "dept_activity":        repo.dept_activity(db, f),
        "timings":              repo.care_timings(db, f),
        "visits_by_hour":       repo.visits_by_hour(db, f),
        "cancellation_reasons": _top_reasons(repo.cancellation_reasons(db, f)),
    }


def _top_reasons(rows: list[dict], keep: int = 6) -> list[dict]:
    """Top `keep` reasons with the long tail folded into 'Other', each with its share of cancellations."""
    total = sum(r["count"] for r in rows)
    head, tail = rows[:keep], rows[keep:]
    if tail:
        head = head + [{"label": "Other reasons", "count": sum(r["count"] for r in tail)}]
    return [{"reason": r["label"], "count": r["count"], "pct": pct(r["count"], total)} for r in head]


# ── Nurse view ────────────────────────────────────────────────────────────────

AGE_GROUPS = ("Under 18", "18–39", "40–64", "65+")
SHIFT_ORDER = ("Morning", "Evening", "Night")


def _age_group(dob: Any, today: date) -> str | None:
    if dob is None:
        return None
    if isinstance(dob, datetime):
        dob = dob.date()
    elif isinstance(dob, str):
        try:
            dob = date.fromisoformat(dob[:10])
        except ValueError:
            return None
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 0:
        return None
    return AGE_GROUPS[0] if age < 18 else AGE_GROUPS[1] if age < 40 else AGE_GROUPS[2] if age < 65 else AGE_GROUPS[3]


def nurse_insights(db, f: Filters) -> dict[str, Any]:
    beds = bed_availability(db, f.department_id)
    busiest = [
        {k: w[k] for k in ("ward_id", "ward_name", "ward_type", "occupied", "operational_beds",
                           "available", "occupancy_pct")}
        for w in beds["ward_occupancy"][:5]          # already sorted busiest first
    ]

    counts = {g: 0 for g in AGE_GROUPS}
    today = date.today()
    for dob in repo.current_patient_birthdates(db, f.department_id):
        g = _age_group(dob, today)
        if g:
            counts[g] += 1
    total = sum(counts.values())

    by_shift: dict[str, dict[str, int]] = {s: {"nurses": 0, "doctors": 0} for s in SHIFT_ORDER}
    for r in repo.staff_by_shift(db, f.department_id):
        slot = by_shift.setdefault(r["shift"], {"nurses": 0, "doctors": 0})
        slot["nurses" if r["role"] == "Nurse" else "doctors"] += r["count"]

    stay = repo.bed_stay(db, f)
    return {
        "busiest_wards":  busiest,
        "age_groups":     [{"group": g, "count": c, "pct": pct(c, total)} for g, c in counts.items()],
        "staff_by_shift": [{"shift": s, **v} for s, v in by_shift.items()],
        "avg_bed_stay_hours": stay["avg_hours"],
        "bed_stay_samples":   stay["samples"],
    }


# ── Beds ──────────────────────────────────────────────────────────────────────

def bed_availability(db, department_id: int | None) -> dict[str, Any]:
    wards = repo.ward_bed_rows(db, department_id)
    for w in wards:
        w["operational_beds"] = max(w["total_beds"] - w["maintenance"], 0)
        w["occupancy_pct"] = occupancy_pct(w["occupied"], w["total_beds"], w["maintenance"])
    wards.sort(key=lambda w: (-w["occupancy_pct"], w["ward_name"]))

    total       = sum(w["total_beds"]  for w in wards)
    occupied    = sum(w["occupied"]    for w in wards)
    available   = sum(w["available"]   for w in wards)
    maintenance = sum(w["maintenance"] for w in wards)
    reserved    = sum(w["reserved"]    for w in wards)

    status_rows = repo.bed_status_counts(db, department_id)
    status_total = sum(r["count"] for r in status_rows)
    return {
        "total_beds":       total,
        "operational_beds": max(total - maintenance, 0),
        "occupied":         occupied,
        "available":        available,
        "maintenance":      maintenance,
        "reserved":         reserved,
        "occupancy_pct":    occupancy_pct(occupied, total, maintenance),
        "status_breakdown": [
            {"status": r["label"], "count": r["count"], "pct": pct(r["count"], status_total)}
            for r in status_rows
        ],
        "ward_occupancy":   wards,
    }
