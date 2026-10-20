"""
app/analytics/dependencies.py
=============================
FastAPI dependencies shared by the analytics routes.
"""

from __future__ import annotations

from fastapi import Depends, Query

from app.analytics.filters import Filters, build_filters
from app.core.permissions import get_department_scope


def get_filters(
    start_date:    str | None = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date:      str | None = Query(None, description="Inclusive end date YYYY-MM-DD"),
    department_id: str | None = Query(None, description="Department id (full-access roles only)"),
    visit_type:    str | None = Query(None, description="Inpatient | Outpatient | Emergency"),
    visit_status:  str | None = Query(None, description="Completed | Ongoing | Cancelled"),
    dept_scope:    str | None = Depends(get_department_scope),
) -> Filters:
    return build_filters(start_date, end_date, department_id, visit_type, visit_status, dept_scope)


def get_scope_filters(dept_scope: str | None = Depends(get_department_scope)) -> Filters:
    """Filters carrying only the caller's department scope (validates it)."""
    return build_filters(dept_scope=dept_scope)
