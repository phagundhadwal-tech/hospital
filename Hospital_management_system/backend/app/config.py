"""
app/config.py
=============
All application settings come from environment variables or backend/.env.
No credential ever lives in source code.

get_settings() is cached; in tests call get_settings.cache_clear() after
changing environment variables.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import DEFAULT_TABLE_NAMES

_BACKEND_DIR = Path(__file__).resolve().parent.parent          # .../backend
_DEFAULT_USERS_CSV = str(_BACKEND_DIR / "data" / "users.csv")
_IDENT = re.compile(r"^[A-Za-z0-9_]*$")                         # safe SQL identifier part


class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────────────────────
    APP_TITLE: str = "CarePulse Hospital Management API"
    APP_DESCRIPTION: str = (
        "REST API for the CarePulse HMS dashboard. "
        "All endpoints require a valid JWT Bearer token except POST /api/auth/login."
    )
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    LOG_LEVEL: str = "INFO"

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET: str                                   # REQUIRED
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BCRYPT_ROUNDS: int = 12

    # ── Request validation ────────────────────────────────────────────────────
    DATE_FORMAT: str = "%Y-%m-%d"
    FILTER_TEXT_MAX_LENGTH: int = 40

    # ── Database (SQL Server) ─────────────────────────────────────────────────
    # Either a SQLAlchemy URL  (mssql+pyodbc://...)  or a raw ODBC string
    # (DRIVER={ODBC Driver 18 for SQL Server};SERVER=...;DATABASE=...).
    # Required by the API server; see backend/.env.example.
    DATABASE_URL: str = ""
    DB_SCHEMA: str = "dbo"            # schema that owns the tables
    DB_TABLE_SUFFIX: str = ""         # e.g. "_V6" if your tables are named PATIENT_VISITS_V6
    # Logical table name -> physical table name (before DB_TABLE_SUFFIX).
    # Override with a JSON object in .env, e.g. DB_TABLE_NAMES={"Beds":"BEDS"}
    DB_TABLE_NAMES: dict[str, str] = dict(DEFAULT_TABLE_NAMES)
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE_SECONDS: int = 1800
    DB_CONNECT_TIMEOUT_SECONDS: int = 10

    # ── Auth user store ───────────────────────────────────────────────────────
    USERS_CSV_PATH: str = _DEFAULT_USERS_CSV

    # ── CORS (comma-separated) ────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",               # unknown keys in .env must not crash startup
    )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def users_csv_file(self) -> Path:
        p = Path(self.USERS_CSV_PATH)
        return p if p.is_absolute() else (_BACKEND_DIR / p)

    @field_validator("JWT_SECRET")
    @classmethod
    def jwt_secret_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 characters long.\n"
                'Generate one: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        return v

    @field_validator("DB_SCHEMA", "DB_TABLE_SUFFIX")
    @classmethod
    def identifiers_must_be_safe(cls, v: str) -> str:
        if not _IDENT.match(v):
            raise ValueError("Only letters, digits and underscore are allowed here.")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
