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
    waiting_now:        int = 0           # Ongoing, not admitted, consultation not started (live snapshot)


# ── Monthly trend chart ───────────────────────────────────────────────────────

class MonthlyPoint(BaseModel):
    """One data point in the monthly admissions/discharges trend chart."""
    month:      str   # "YYYY-MM"
    admissions: int
    discharges: int


class MonthlyTrendResponse(BaseModel):
    data: list[MonthlyPoint]


# ── Recent arrivals ────────────────────────────────────

class ArrivalDay(BaseModel):
    date:    str               # "YYYY-MM-DD"
    total:   int
    by_type: dict[str, int]    # visit type -> visits registered that day


class RecentArrivalsResponse(BaseModel):
    through: str | None        # last day of the window
    bucket:  str = "day"       # "day", or "week" (date = the Monday) for windows over ~3 months
    days:    list[ArrivalDay]


class DataRangeResponse(BaseModel):
    earliest: str | None       # first / last day with a registered visit
    latest:   str | None


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


class CareTimings(BaseModel):
    """Average durations; each *_n is how many visits the average is based on."""
    reg_to_triage_min:     float | None
    reg_to_triage_n:       int
    triage_to_consult_min: float | None
    triage_to_consult_n:   int
    consultation_min:      float | None
    consultation_n:        int
    avg_stay_hours:        float | None
    stay_n:                int


class HourCount(BaseModel):
    hour:  int   # 0-23, by Registration_Time
    count: int


class CancellationReason(BaseModel):
    reason: str
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
    timings:               CareTimings
    visits_by_hour:        list[HourCount]
    cancellation_reasons:  list[CancellationReason]


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


# ── Nurse insights ────────────────────────────────────────────────────────────

class BusyWard(BaseModel):
    ward_id:          str
    ward_name:        str
    ward_type:        str
    occupied:         int
    operational_beds: int
    available:        int
    occupancy_pct:    float


class AgeGroupCount(BaseModel):
    group: str
    count: int
    pct:   float


class ShiftStaff(BaseModel):
    shift:   str
    nurses:  int
    doctors: int


class NurseInsightsResponse(BaseModel):
    """
    busiest_wards      : top 5 wards by occupancy (same formula as bed availability).
    age_groups         : currently admitted patients by age group.
    staff_by_shift     : nurses and doctors rostered per shift (Staff.Staff_Shift).
    avg_bed_stay_hours : mean length of finished bed assignments in the caller's wards.
    """
    busiest_wards:      list[BusyWard]
    age_groups:         list[AgeGroupCount]
    staff_by_shift:     list[ShiftStaff]
    avg_bed_stay_hours: float | None
    bed_stay_samples:   int


# ── Data quality ──────────────────────────────────────────────────────────────

class DataQualityCheck(BaseModel):
    check:       str
    description: str
    count:       int


class DataQualityResponse(BaseModel):
    checks: list[DataQualityCheck]
