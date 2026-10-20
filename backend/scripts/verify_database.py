#!/usr/bin/env python3
"""
scripts/verify_database.py
==========================
Compares what the dashboard SQL returns from YOUR SQL Server database with an
independent pandas calculation on the V6 CSV files.  Run from the backend folder:

    python scripts/verify_database.py

It only makes sense when the database holds the same V6 data as the CSV files.
Read-only.
"""

from __future__ import annotations

import sys

from _common import DEFAULT_DATA_DIR, make_database

import csv_expected as ce
from app.analytics.filters import build_filters
from app.analytics import service as svc
from app.repositories import sql_repo as repo

CASES = [(None, None, None), ("2026-06-01", "2026-06-30", None), ("2026-05-01", None, 1),
         (None, "2026-08-31", 3), ("2026-10-19", "2026-10-19", None), ("2030-01-01", "2030-12-31", None)]


def main() -> None:
    db = make_database()
    v, beds, wards, _deps, _asg = ce.load(DEFAULT_DATA_DIR)
    failures = 0

    def check(label, got, exp):
        nonlocal failures
        ok = got == exp
        failures += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {label}" + ("" if ok else f"   sql={got} expected={exp}"))

    for s, e, d in CASES:
        f = build_filters(s, e, str(d) if d else None)
        got, exp = repo.visit_kpis(db, f), ce.expected_visit_metrics(v, s, e, d)
        for key in ("total_visits", "admissions", "discharges", "avg_wait_minutes", "wait_samples", "current_admissions"):
            check(f"[{s}..{e} dept={d}] {key} = {got[key]}", got[key], exp[key])
        trend = {r["month"]: (r["admissions"], r["discharges"]) for r in repo.monthly_trend(db, f)}
        check(f"[{s}..{e} dept={d}] monthly trend", trend, exp["trend"])
    for d in (None, 1, 2, 3, 4):
        got, exp = svc.bed_availability(db, d), ce.expected_bed_metrics(beds, wards, d)
        for key, value in exp.items():
            check(f"beds dept={d} {key} = {got[key]}", got[key], value)

    print("\nALL CHECKS PASSED" if not failures else f"\n{failures} CHECK(S) FAILED")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
