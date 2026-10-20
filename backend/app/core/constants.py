"""
app/core/constants.py
=====================
Domain constants shared by the repository, service and controller layers.
Anything deployment-specific (names, limits, URLs) lives in app/config.py instead.
"""

from __future__ import annotations

# ── Logical table names (mapped to physical names by Settings.DB_TABLE_NAMES) ──
T_VISITS          = "Patient_Visits"
T_DEPARTMENTS     = "Departments"
T_PATIENTS        = "Patients"
T_STAFF           = "Staff"
T_BEDS            = "Beds"
T_WARDS           = "Wards"
T_BED_ASSIGNMENTS = "Bed_Assignments"

# Default physical table names (override with Settings.DB_TABLE_NAMES).
DEFAULT_TABLE_NAMES: dict[str, str] = {
    T_VISITS:          "patient_visits",
    T_DEPARTMENTS:     "departments",
    T_PATIENTS:        "patients",
    T_STAFF:           "staff",
    T_BEDS:            "beds",
    T_WARDS:           "wards",
    T_BED_ASSIGNMENTS: "bed_assignments",
}

# ── Visit_Status values ───────────────────────────────────────────────────────
STATUS_ONGOING   = "Ongoing"
STATUS_CANCELLED = "Cancelled"

# Placeholder the V6 data uses for visits that were not cancelled.
REASON_NOT_APPLICABLE = "Not Applicable"

# ── Bed_Status values ─────────────────────────────────────────────────────────
BED_OCCUPIED    = "Occupied"
BED_AVAILABLE   = "Available"
BED_MAINTENANCE = "Maintenance"
BED_RESERVED    = "Reserved"

# Label for wards that have no matching department row.
UNASSIGNED_DEPARTMENT = "Unassigned"

# ── Calculation precision ─────────────────────────────────────────────────────
PERCENT_DECIMALS = 1
