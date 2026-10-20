#!/usr/bin/env python3
"""
scripts/load_csv_to_sqlserver.py
================================
Creates the CarePulse tables (database/01_schema.sql) and loads the seven V6 CSV
files into SQL Server.  Run from the backend folder:

    python scripts/load_csv_to_sqlserver.py

SAFETY
  * Tables are created only if missing.
  * A table that already contains rows is SKIPPED - existing data is never
    modified, duplicated or deleted.
  * To start over deliberately:  --drop-and-reload  (asks you to type YES).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import (DEFAULT_DATA_DIR, SCHEMA_SQL, explain_connection_error, make_database, read_env)

from app.db.csv_data import COLUMNS, LOAD_ORDER, read_table


def run_schema(db) -> None:
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    batches = [b.strip() for b in re.split(r"^\s*GO\s*$", sql, flags=re.MULTILINE | re.IGNORECASE) if b.strip()]
    with db.engine.begin() as conn:
        for batch in batches:
            conn.exec_driver_sql(batch)
    print(f"Schema ready ({len(batches)} batches executed).")


def row_count(db, table: str) -> int | None:
    from sqlalchemy import text
    try:
        with db.engine.connect() as conn:
            return int(conn.execute(text(f"SELECT COUNT(*) FROM {db.table(table)}")).scalar_one())
    except Exception:
        return None


def drop_all(db) -> None:
    with db.engine.begin() as conn:
        for table in reversed(LOAD_ORDER):
            conn.exec_driver_sql(f"IF OBJECT_ID(N'dbo.{table}', N'U') IS NOT NULL DROP TABLE dbo.{table}")
    print("Dropped all CarePulse tables.")


def load_table(db, table: str, data_dir: Path) -> None:
    from sqlalchemy import text

    existing = row_count(db, table)
    if existing:
        print(f"  {table:<16} already has {existing} rows -> skipped (not modified)")
        return
    rows = read_table(table, data_dir)
    cols = [c for c, _ in COLUMNS[table]]
    sql = text(f"INSERT INTO {db.table(table)} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})")
    with db.engine.begin() as conn:                      # one transaction per table
        for i in range(0, len(rows), 500):
            conn.execute(sql, rows[i:i + 500])
    print(f"  {table:<16} loaded {len(rows)} rows")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="folder with the *_V6.csv files")
    ap.add_argument("--drop-and-reload", action="store_true", help="DESTRUCTIVE: drop the CarePulse tables first")
    args = ap.parse_args()

    env = read_env()
    if env.get("DB_SCHEMA", "dbo") != "dbo" or env.get("DB_TABLE_SUFFIX", ""):
        sys.exit("This loader creates the standard table names in schema dbo. Your .env points at a custom schema/"
                 "suffix, which means your tables already exist - skip the loader and run scripts/check_db.py.")

    db = make_database()
    try:
        with db.engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as exc:                              # noqa: BLE001
        sys.exit(explain_connection_error(exc))

    print(f"Data folder: {args.data_dir}")
    if args.drop_and_reload:
        if input("This DELETES all CarePulse tables and data. Type YES to continue: ").strip() != "YES":
            sys.exit("Cancelled - nothing was changed.")
        drop_all(db)

    run_schema(db)
    print("Loading CSV files:")
    for table in LOAD_ORDER:
        load_table(db, table, args.data_dir)

    print("\nRow counts now in SQL Server:")
    for table in LOAD_ORDER:
        print(f"  {table:<16} {row_count(db, table)}")
    print("\nDone. Next: python scripts/check_db.py")


if __name__ == "__main__":
    main()
