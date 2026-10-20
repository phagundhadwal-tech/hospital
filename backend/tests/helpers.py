"""
tests/helpers.py
================
A stdlib-sqlite3 implementation of the Database interface, pre-loaded from the
V6 CSV files.  It lets the SAME repository SQL that runs on SQL Server be
exercised without a SQL Server instance (dialect fragments switch to SQLite).
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from app.db.csv_data import COLUMNS, LOAD_ORDER, read_table

DATA_DIR = Path(__file__).resolve().parents[2] / "database" / "data"

_SQLITE_TYPES = {"int": "INTEGER", "str": "TEXT", "date": "TEXT", "datetime": "TEXT"}


class Sqlite3Database:
    dialect = "sqlite"
    schema = ""
    suffix = ""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        for table in LOAD_ORDER:
            cols = COLUMNS[table]
            ddl = ", ".join(f"{c} {_SQLITE_TYPES[k]}" for c, k in cols)
            self.conn.execute(f"CREATE TABLE {table} ({ddl})")
            rows = read_table(table, data_dir)
            names = [c for c, _ in cols]
            self.conn.executemany(
                f"INSERT INTO {table} ({', '.join(names)}) VALUES ({', '.join(':' + n for n in names)})",
                [{n: _adapt(r[n]) for n in names} for r in rows],
            )
        self.conn.commit()

    def table(self, name: str) -> str:
        return name

    def query(self, sql: str, params: dict | None = None) -> list[dict]:
        bound = {k: _adapt(v) for k, v in (params or {}).items()}
        return [dict(r) for r in self.conn.execute(sql, bound).fetchall()]

    def execute(self, sql: str) -> None:
        self.conn.execute(sql)
        self.conn.commit()


def _adapt(v):
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    return v
