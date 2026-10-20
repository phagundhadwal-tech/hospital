"""
app/analytics/controller.py
===========================
Request handling logic for the analytics endpoints.

A controller receives already-validated inputs (Filters, a Database handle),
calls the service / repository layers and returns response models. It knows
nothing about routing, URLs, roles or HTTP dependencies — those live in router.py.
"""

from __future__ import annotations

from app.analytics import service as svc
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
from app.repositories import sql_repo


def get_kpis(db, f: Filters) -> KPIResponse:
    return KPIResponse(**svc.kpis(db, f))


def get_monthly_trend(db, f: Filters) -> MonthlyTrendResponse:
    return MonthlyTrendResponse(data=svc.monthly_trend(db, f))


def get_dept_activity(db, f: Filters) -> DeptActivityResponse:
    return DeptActivityResponse(data=svc.dept_activity(db, f))


def get_patient_flow(db, f: Filters) -> PatientFlowResponse:
    return PatientFlowResponse(**svc.patient_flow(db, f))


def get_bed_availability(db, f: Filters) -> BedAvailabilityResponse:
    return BedAvailabilityResponse(**svc.bed_availability(db, f.department_id))


def get_nurse_insights(db, f: Filters) -> NurseInsightsResponse:
    return NurseInsightsResponse(**svc.nurse_insights(db, f))


def get_recent_arrivals(db, f: Filters) -> RecentArrivalsResponse:
    return RecentArrivalsResponse(**svc.recent_arrivals(db, f))


def get_data_range(db, f: Filters) -> DataRangeResponse:
    return DataRangeResponse(**svc.data_range(db, f))


def get_departments(db, f: Filters) -> list[dict]:
    rows = sql_repo.departments(db, f.department_id)
    return [
        {"Department_ID": str(r["Department_ID"]), "Department_Name": r["Department_Name"]}
        for r in rows
    ]


def get_data_quality(db) -> DataQualityResponse:
    return DataQualityResponse(checks=sql_repo.data_quality(db))
