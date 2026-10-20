"""
app/analytics/router.py
========================
Analytics routes. Each route only declares the URL, the allowed roles and the
dependencies, then delegates to app/analytics/controller.py.

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
GET /api/analytics/nurse-insights    → Busiest wards, staff per shift, age mix, bed stay
GET /api/analytics/recent-arrivals    → Arrivals per day/week for the chosen dates (default: last 14 days of data)
GET /api/analytics/data-range        → First/last day with visit data
GET /api/analytics/departments       → Department list for filter dropdowns
GET /api/analytics/data-quality      → Read-only data-quality report (admin roles)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.analytics import controller
from app.analytics.dependencies import get_filters, get_scope_filters
from app.analytics.filters import Filters
from app.analytics.models import (
    BedAvailabilityResponse,
    DataQualityResponse,
    DataRangeResponse,
    DeptActivityResponse,
    KPIResponse,
    MonthlyTrendResponse,
    NurseInsightsResponse,
    PatientFlowResponse,
    RecentArrivalsResponse,
)
from app.core.permissions import (
    BED_AVAILABILITY_ROLES,
    FULL_ACCESS_ROLES,
    OVERVIEW_ROLES,
    PATIENT_FLOW_ROLES,
    require_roles,
)
from app.db.database import get_db
from app.users.models import TokenUser

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/kpis", response_model=KPIResponse, summary="Hospital Overview KPIs")
def kpis(
    _user: TokenUser = Depends(require_roles(*OVERVIEW_ROLES)),
    f: Filters = Depends(get_filters),
    db=Depends(get_db),
):
    return controller.get_kpis(db, f)


@router.get("/monthly-trend", response_model=MonthlyTrendResponse,
            summary="Monthly admissions and discharges trend")
def monthly_trend(
    _user: TokenUser = Depends(require_roles(*OVERVIEW_ROLES)),
    f: Filters = Depends(get_filters),
    db=Depends(get_db),
):
    return controller.get_monthly_trend(db, f)


@router.get("/dept-activity", response_model=DeptActivityResponse,
            summary="Visit and admission counts per department")
def dept_activity(
    _user: TokenUser = Depends(require_roles(*OVERVIEW_ROLES)),
    f: Filters = Depends(get_filters),
    db=Depends(get_db),
):
    return controller.get_dept_activity(db, f)


@router.get("/patient-flow", response_model=PatientFlowResponse,
            summary="Patient Flow analytics (all metrics in one call)")
def patient_flow(
    _user: TokenUser = Depends(require_roles(*PATIENT_FLOW_ROLES)),
    f: Filters = Depends(get_filters),
    db=Depends(get_db),
):
    return controller.get_patient_flow(db, f)


@router.get("/bed-availability", response_model=BedAvailabilityResponse,
            summary="Bed availability snapshot (all metrics in one call)")
def bed_availability(
    _user: TokenUser = Depends(require_roles(*BED_AVAILABILITY_ROLES)),
    f: Filters = Depends(get_filters),
    db=Depends(get_db),
):
    return controller.get_bed_availability(db, f)


@router.get("/nurse-insights", response_model=NurseInsightsResponse,
            summary="Ward load, staffing, age mix and bed stay for the nurse view")
def nurse_insights(
    _user: TokenUser = Depends(require_roles(*BED_AVAILABILITY_ROLES)),
    f: Filters = Depends(get_filters),
    db=Depends(get_db),
):
    return controller.get_nurse_insights(db, f)


@router.get("/recent-arrivals", response_model=RecentArrivalsResponse,
            summary="Visits registered per day (or week) for the chosen dates, default last 14 days of data")
def recent_arrivals(
    _user: TokenUser = Depends(require_roles(*OVERVIEW_ROLES)),
    f: Filters = Depends(get_filters),
    db=Depends(get_db),
):
    return controller.get_recent_arrivals(db, f)


@router.get("/data-range", response_model=DataRangeResponse,
            summary="First and last day with visit data (anchors the date presets)")
def data_range(
    _user: TokenUser = Depends(require_roles(*OVERVIEW_ROLES)),
    f: Filters = Depends(get_filters),
    db=Depends(get_db),
):
    return controller.get_data_range(db, f)


@router.get("/departments", summary="Departments the caller may see (for filter dropdowns)")
def departments(
    _user: TokenUser = Depends(require_roles(*OVERVIEW_ROLES)),
    f: Filters = Depends(get_scope_filters),
    db=Depends(get_db),
) -> list[dict]:
    return controller.get_departments(db, f)


@router.get("/data-quality", response_model=DataQualityResponse,
            summary="Read-only data-quality report")
def data_quality(
    _user: TokenUser = Depends(require_roles(*FULL_ACCESS_ROLES)),
    db=Depends(get_db),
):
    return controller.get_data_quality(db)
