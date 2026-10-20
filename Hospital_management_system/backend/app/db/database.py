"""
app/db/database.py
==================
Database access seam.

* Repositories talk to the tiny `Database` interface: db.query(sql, params).
* SQLAlchemyDatabase is the production implementation (SQL Server via pyodbc,
  pooled connections, parameterised text queries).
* Tests use a stdlib-sqlite3 implementation of the same interface.

Credentials are read ONLY from the DATABASE_URL environment variable
(see backend/.env.example) and never leave the server.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.config import get_settings
from app.core.exceptions import DatabaseQueryError, DatabaseUnavailableError

log = logging.getLogger("carepulse.db")



def build_engine_url(raw: str):
    from sqlalchemy.engine import URL

    raw = (raw or "").strip()

    if not raw:
        raise DatabaseUnavailableError(
            "DATABASE_URL is not configured. Set it in backend/.env."
        )

    if "://" in raw:
        return raw

    if "DRIVER=" in raw.upper():
        return URL.create(
            "mssql+pyodbc",
            query={"odbc_connect": raw},
        )

    raise DatabaseUnavailableError(
        "DATABASE_URL must be a SQLAlchemy URL or ODBC connection string."
    )



class SQLAlchemyDatabase:
    """Production database handle (SQL Server)."""

    def __init__(self, engine, schema: str = "dbo", suffix: str = "") -> None:
        self.engine = engine
        self.dialect: str = engine.dialect.name        # "mssql"
        self.schema = schema
        self.suffix = suffix

    # -- naming -------------------------------------------------------------
    def table(self, name: str) -> str:
        table_names = {
                "Patient_Visits": "visits",
                "Departments": "departments",
                "Patients": "patients",
                "Staff": "staff",
                "Beds": "beds",
                "Wards": "wards",
                "Bed_Assignments": "bed_assignments",
            }
        
        actual_name = table_names.get(name, name)

        if self.dialect == "mssql":
            return f"[{self.schema}].[{actual_name}{self.suffix}]"

        return f"{actual_name}{self.suffix}"

    # -- execution ----------------------------------------------------------
    def query(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        from sqlalchemy import text
        from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError, SQLAlchemyError

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                return [dict(row) for row in result.mappings().all()]
        except (OperationalError, InterfaceError) as exc:
            log.error("SQL Server connection problem: %s", exc.__class__.__name__, exc_info=True)
            raise DatabaseUnavailableError(
                "Cannot connect to SQL Server. Check that the server is running and DATABASE_URL is correct."
            ) from exc
        except (DBAPIError, SQLAlchemyError) as exc:
            log.error("SQL query failed: %s", exc.__class__.__name__, exc_info=True)
            raise DatabaseQueryError() from exc


@lru_cache
def get_database() -> SQLAlchemyDatabase:
    """Create the pooled engine once per process."""
    from sqlalchemy import create_engine

    s = get_settings()
    url = build_engine_url(s.DATABASE_URL)
    kwargs: dict[str, Any] = {"pool_pre_ping": True}
    if str(url).startswith("mssql"):
        kwargs.update(
            pool_size=s.DB_POOL_SIZE,
            max_overflow=s.DB_MAX_OVERFLOW,
            pool_recycle=s.DB_POOL_RECYCLE_SECONDS,
            connect_args={"timeout": s.DB_CONNECT_TIMEOUT_SECONDS},
        )
    engine = create_engine(url, **kwargs)
    return SQLAlchemyDatabase(engine, schema=s.DB_SCHEMA, suffix=s.DB_TABLE_SUFFIX)


def get_db() -> SQLAlchemyDatabase:
    """FastAPI dependency (overridden in tests)."""
    return get_database()
