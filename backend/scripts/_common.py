"""Shared helpers for the command-line scripts (no FastAPI settings required)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
DEFAULT_DATA_DIR = PROJECT_DIR / "database" / "data"
SCHEMA_SQL = PROJECT_DIR / "database" / "01_schema.sql"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

_KEYS = ("DATABASE_URL", "DB_SCHEMA", "DB_TABLE_SUFFIX")


def read_env() -> dict[str, str]:
    """Environment variables win; otherwise values come from backend/.env."""
    env: dict[str, str] = {}
    dotenv = BACKEND_DIR / ".env"
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            env[key.strip()] = value
    for k in _KEYS:
        if k in os.environ:
            env[k] = os.environ[k]
    return env


def make_database(fast_executemany: bool = False):
    """Return a SQLAlchemyDatabase built from DATABASE_URL (exit with a clear message if unusable)."""
    from sqlalchemy import create_engine

    from app.core.exceptions import DatabaseUnavailableError
    from app.db.database import SQLAlchemyDatabase, build_engine_url

    env = read_env()
    try:
        url = build_engine_url(env.get("DATABASE_URL", ""))
    except DatabaseUnavailableError as exc:
        sys.exit(f"ERROR: {exc.detail}")
    engine = create_engine(url, pool_pre_ping=True)
    return SQLAlchemyDatabase(engine, schema=env.get("DB_SCHEMA", "dbo") or "dbo",
                              suffix=env.get("DB_TABLE_SUFFIX", ""))


def explain_connection_error(exc: Exception) -> str:
    return (
        "Could not connect to SQL Server.\n"
        f"  Driver message: {str(exc).splitlines()[0][:300]}\n"
        "  Check: (1) SQL Server is running, (2) the server name / instance in DATABASE_URL,\n"
        "         (3) the database exists (run database/00_create_database.sql in SSMS),\n"
        "         (4) 'ODBC Driver 18 for SQL Server' is installed,\n"
        "         (5) for a local server with a self-signed certificate add TrustServerCertificate=yes\n"
        "             (development only - use a real certificate in production)."
    )
