"""
app/db/dialect.py
=================
The few SQL fragments that differ between SQL Server (production) and SQLite
(used only by the automated tests).  Everything else is plain ANSI SQL.
Only trusted constants and column names written in this code base are ever
passed in here; user-supplied values are ALWAYS bound parameters (:name).
"""

from __future__ import annotations


def minutes_between(dialect: str, start_col: str, end_col: str) -> str:
    """Whole minutes from start_col to end_col (NULL when either is NULL)."""
    if dialect == "mssql":
        return f"DATEDIFF(MINUTE, {start_col}, {end_col})"
    return f"CAST(ROUND((julianday({end_col}) - julianday({start_col})) * 1440.0) AS INTEGER)"


def year_month(dialect: str, col: str) -> str:
    """'YYYY-MM' bucket label for a datetime column."""
    if dialect == "mssql":
        return f"CONVERT(VARCHAR(7), {col}, 23)"
    return f"strftime('%Y-%m', {col})"
