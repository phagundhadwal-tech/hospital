#!/usr/bin/env python3
"""
scripts/check_db.py
===================
READ-ONLY diagnostics.  Run from the backend folder:   python scripts/check_db.py

1. Connects to SQL Server using DATABASE_URL.
2. Confirms every table and column the dashboard needs exists, and that the
   timestamp columns are real date/time types.
3. Prints row counts and the headline KPIs.
4. Prints the data-quality report.
"""

from __future__ import annotations

import sys

from _common import explain_connection_error, make_database

from app.analytics.filters import Filters
from app.db.csv_data import COLUMNS, LOAD_ORDER
from app.repositories import sql_repo as repo

DATETIME_TYPES = {"datetime", "datetime2", "smalldatetime", "date", "datetimeoffset"}


def main() -> None:
    db = make_database()
    try:
        db.query("SELECT 1 AS ok")
    except Exception as exc:                              # noqa: BLE001
        cause = exc.__cause__ or exc
        sys.exit(explain_connection_error(cause))
    print("[OK] Connected to SQL Server.\n")

    problems = 0
    for table in LOAD_ORDER:
        name = f"{table}{db.suffix}"
        cols = db.query(
            "SELECT COLUMN_NAME AS c, DATA_TYPE AS t FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = :s AND TABLE_NAME = :t", {"s": db.schema, "t": name})
        if not cols:
            print(f"[MISSING] table {db.schema}.{name}")
            problems += 1
            continue
        have = {r["c"].lower(): r["t"].lower() for r in cols}
        for col, kind in COLUMNS[table]:
            if col.lower() not in have:
                print(f"[MISSING] column {name}.{col}")
                problems += 1
            elif kind in ("datetime", "date") and have[col.lower()] not in DATETIME_TYPES:
                print(f"[TYPE] {name}.{col} is {have[col.lower()]} but must be a date/time type "
                      f"(text dates break filtering and wait-time maths)")
                problems += 1
        n = db.query(f"SELECT COUNT(*) AS n FROM {db.table(table)}")[0]["n"]
        print(f"[OK] {name:<18} {n:>6} rows")
    if problems:
        sys.exit(f"\n{problems} problem(s) found - fix them before starting the API.")

    k = repo.visit_kpis(db, Filters())
    print("\nHeadline KPIs (all time, all departments):")
    for key, value in k.items():
        print(f"  {key:<20} {value}")
    print("\nData-quality report:")
    for r in repo.data_quality(db):
        flag = "  " if r["count"] == 0 else "! "
        print(f"  {flag}{r['count']:>5}  {r['description']}")
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
