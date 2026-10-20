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
    }


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
