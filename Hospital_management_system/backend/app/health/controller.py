"""
app/health/controller.py
========================
Liveness and database-reachability checks.
"""

from __future__ import annotations

from app.config import get_settings


def liveness() -> dict:
    return {"status": "ok", "service": get_settings().APP_TITLE}


def database_status(db) -> dict:
    rows = db.query("SELECT 1 AS ok")
    return {"status": "ok", "database": "reachable", "result": rows[0]["ok"]}
