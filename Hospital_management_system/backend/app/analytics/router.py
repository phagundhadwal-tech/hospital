"""
app/analytics/router.py
========================
Analytics API endpoints backed by SQL Server.

All routes:
  - require a valid JWT (get_current_user)
  - enforce role-based access (require_roles)
  - apply department scoping from the JWT (get_department_scope); a
    department_id query parameter only works for full-access roles
  - accept optional filters: start_date, end_date (YYYY-MM-DD, both inclusive),
    department_id, visit_type, visit_status

ENDPOINTS
---------
GET /api/analytics/kpis              → Hospital Overview KPI cards
GET /api/analytics/monthly-trend     → Monthly admissions / discharges chart
GET /api/analytics/dept-activity     → Department activity bar chart
GET /api/analytics/patient-flow      → Patient Flow page (all-in-one)
GET /api/analytics/bed-availability  → Bed Availability page (all-in-one)
GET /api/analytics/departments       → Department list for filter dropdowns
GET /api/analytics/data-quality      → Read-only data-quality report (admin roles)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.analytics import service as svc
from app.analytics.filters import Filters, build_filters
from app.analytics.models import (
    BedAvailabilityResponse,
    DataQualityResponse,
    DeptActivityResponse,
    KPIResponse,
    MonthlyTrendResponse,
    PatientFlowResponse,
)
from app.core.permissions import (
    BED_AVAILABILITY_ROLES,
    FULL_ACCESS_ROLES,
    OVERVIEW_ROLES,
    PATIENT_FLOW_ROLES,
    get_department_scope,
    require_roles,
)
from app.db.database import get_db
from app.repositories import sql_repo
from app.users.models import TokenUser

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _filters(
    start_date:    str | None = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date:      str | None = Query(None, description="Inclusive end date YYYY-MM-DD"),
    department_id: str | None = Query(None, description="Department id (full-access roles only)"),
    visit_type:    str | None = Query(None, description="Inpatient | Outpatient | Emergency"),
    visit_status:  str | None = Query(None, description="Completed | Ongoing | Cancelled"),
    dept_scope:    str | None = Depends(get_department_scope),
) -> Filters:
    return build_filters(start_date, end_date, department_id, visit_type, visit_status, dept_scope)


@router.get("/kpis", response_model=KPIResponse, summary="Hospital Overview KPIs")
def get_kpis(
    _user: TokenUser = Depends(require_roles(*OVERVIEW_ROLES)),
    f: Filters = Depends(_filters),
    db=Depends(get_db),
):
    return KPIResponse(**svc.kpis(db, f))


@router.get("/monthly-trend", response_model=MonthlyTrendResponse,
            summary="Monthly admissions and discharges trend")
def get_monthly_trend(
    _user: TokenUser = Depends(require_roles(*OVERVIEW_ROLES)),
    f: Filters = Depends(_filters),
    db=Depends(get_db),
):
    return MonthlyTrendResponse(data=svc.monthly_trend(db, f))


@router.get("/dept-activity", response_model=DeptActivityResponse,
            summary="Visit and admission counts per department")
def get_dept_activity(
    _user: TokenUser = Depends(require_roles(*OVERVIEW_ROLES)),
    f: Filters = Depends(_filters),
    db=Depends(get_db),
):
    return DeptActivityResponse(data=svc.dept_activity(db, f))


@router.get("/patient-flow", response_model=PatientFlowResponse,
            summary="Patient Flow analytics (all metrics in one call)")
def get_patient_flow(
    _user: TokenUser = Depends(require_roles(*PATIENT_FLOW_ROLES)),
    f: Filters = Depends(_filters),
    db=Depends(get_db),
):
    return PatientFlowResponse(**svc.patient_flow(db, f))


@router.get("/bed-availability", response_model=BedAvailabilityResponse,
            summary="Bed availability snapshot (all metrics in one call)")
def get_bed_availability(
    _user: TokenUser = Depends(require_roles(*BED_AVAILABILITY_ROLES)),
    f: Filters = Depends(_filters),
    db=Depends(get_db),
):
    return BedAvailabilityResponse(**svc.bed_availability(db, f.department_id))


@router.get("/departments", summary="Departments the caller may see (for filter dropdowns)")
def get_departments(
    _user: TokenUser = Depends(require_roles(*OVERVIEW_ROLES)),
    dept_scope: str | None = Depends(get_department_scope),
    db=Depends(get_db),
) -> list[dict]:
    f = build_filters(dept_scope=dept_scope)          # validates the scope
    rows = sql_repo.departments(db, f.department_id)
    return [{"Department_ID": str(r["Department_ID"]), "Department_Name": r["Department_Name"]} for r in rows]


@router.get("/data-quality", response_model=DataQualityResponse,
            summary="Read-only data-quality report")
def get_data_quality(
    _user: TokenUser = Depends(require_roles(*FULL_ACCESS_ROLES)),
    db=Depends(get_db),
):
    return DataQualityResponse(checks=sql_repo.data_quality(db))
