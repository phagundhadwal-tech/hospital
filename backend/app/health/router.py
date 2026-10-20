"""
app/health/router.py
====================
GET /health     -> process is up (no auth)
GET /health/db  -> SQL Server reachable (503 with a clear message if not)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db.database import get_db
from app.health import controller

router = APIRouter(prefix="/health", tags=["Health"], include_in_schema=False)


@router.get("")
def health() -> dict:
    return controller.liveness()


@router.get("/db")
def health_db(db=Depends(get_db)) -> dict:
    return controller.database_status(db)
