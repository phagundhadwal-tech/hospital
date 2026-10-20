"""
app/analytics/models.py
========================
Pydantic response schemas for all analytics API endpoints.

WHY define response schemas?
  FastAPI uses them to:
    1. Validate that the service layer returns the right shape.
    2. Auto-generate accurate OpenAPI documentation.
    3. Strip out any extra fields accidentally included.

  The schemas also serve as a contract between frontend and backend:
  the frontend TypeScript interfaces should mirror these exactly.
"""

from __future__ import annotations

from pydantic import BaseModel


# ── Shared primitives ─────────────────────────────────────────────────────────

class DepartmentInfo(BaseModel):
    department_id:   str
    department_name: str


# ── Hospital Overview KPIs ────────────────────────────────────────────────────

class KPIResponse(BaseModel):
    """
    Top-level KPI card values for the Hospital Overview page.

    admissions         : Visits with an Admission_Time inside the selected range.
    discharges         : Visits with a Discharge_Time inside the selected range.
    avg_wait_minutes   : Mean (Consultation_Start_Time − Registration_Time)
                         in minutes, across all visits where both exist and
                         result is non-negative.
    bed_occupancy_pct  : Occupied / (all beds − Maintenance beds) × 100, from the
                         current Bed_Status snapshot — NOT from historical assignments.
    current_admissions : Patients currently in hospital (Visit_Status = Ongoing,
                         Admission_Time set, no Discharge_Time).
    """
    admissions:         int
    discharges:         int
    avg_wait_minutes:   float | None      # None when no valid registration→consultation pair exists
    bed_occupancy_pct:  float
    current_admissions: int
    wait_samples:       int = 0           # number of visits that contributed to avg_wait_minutes


# ── Monthly trend chart ───────────────────────────────────────────────────────

class MonthlyPoint(BaseModel):
    """One data point in the monthly admissions/discharges trend chart."""
    month:      str   # "YYYY-MM"
    admissions: int
    discharges: int


class MonthlyTrendResponse(BaseModel):
    data: list[MonthlyPoint]


# ── Department activity chart ─────────────────────────────────────────────────

class DeptActivityPoint(BaseModel):
    """One bar in the department activity chart."""
    department_id:   str
    department_name: str
    visit_count:     int
    admission_count: int


class DeptActivityResponse(BaseModel):
    data: list[DeptActivityPoint]


# ── Patient Flow ──────────────────────────────────────────────────────────────

class VisitTypeBreakdown(BaseModel):
    visit_type: str   # "Inpatient" | "Outpatient" | "Emergency"
    count:      int
    pct:        float


class StatusBreakdown(BaseModel):
    status: str
    count:  int
    pct:    float


class PatientFlowResponse(BaseModel):
    """
    Response for GET /api/analytics/patient-flow.

    total_visits         : Filtered visit count.
    admissions           : Visits with Admission_Time.
    discharges           : Visits with Discharge_Time.
    avg_wait_minutes     : Mean waiting time (minutes).
    visit_type_breakdown : Count + % per visit type.
    status_breakdown     : Count + % per Visit_Status.
    monthly_trend        : Admissions + discharges per month.
    dept_activity        : Per-department visit + admission counts.
    """
    total_visits:          int
    admissions:            int
    discharges:            int
    avg_wait_minutes:      float | None
    visit_type_breakdown:  list[VisitTypeBreakdown]
    status_breakdown:      list[StatusBreakdown]
    monthly_trend:         list[MonthlyPoint]
    dept_activity:         list[DeptActivityPoint]


# ── Bed Availability ──────────────────────────────────────────────────────────

class BedStatusBreakdown(BaseModel):
    status: str
    count:  int
    pct:    float


class WardOccupancy(BaseModel):
    ward_id:        str
    ward_name:      str
    ward_type:      str
    department_id:  str
    department_name: str
    total_beds:     int
    operational_beds: int = 0     # total_beds − maintenance (occupancy denominator)
    occupied:       int
    available:      int
    maintenance:    int = 0
    reserved:       int = 0
    occupancy_pct:  float


class BedAvailabilityResponse(BaseModel):
    """
    Response for GET /api/analytics/bed-availability.

    total_beds         : Beds in scope (all or filtered by department).
    operational_beds   : total_beds − maintenance; the denominator of every occupancy %.
    occupied           : Beds with Bed_Status = Occupied.
    available          : Beds with Bed_Status = Available.
    maintenance        : Beds with Bed_Status = Maintenance.
    reserved           : Beds with Bed_Status = Reserved.
    occupancy_pct      : Occupied / Operational × 100.
    status_breakdown   : Count + % per status.
    ward_occupancy     : Per-ward breakdown.
    """
    total_beds:       int
    operational_beds: int
    occupied:         int
    available:        int
    maintenance:      int
    reserved:         int
    occupancy_pct:    float
    status_breakdown: list[BedStatusBreakdown]
    ward_occupancy:   list[WardOccupancy]


# ── Data quality ──────────────────────────────────────────────────────────────

class DataQualityCheck(BaseModel):
    check:       str
    description: str
    count:       int


class DataQualityResponse(BaseModel):
    checks: list[DataQualityCheck]
