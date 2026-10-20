"""
app/db/csv_data.py
==================
Reads the V6 CSV files into typed Python rows.  Used by the SQL Server loader,
the verification script and the automated tests, so the date parsing is defined
exactly once.

The visit timestamps in PATIENT_VISITS_V6.csv look like "5/23/2026 12:05"
(month/day/year, no leading zeros, no seconds).  A value that cannot be parsed
raises an error that names the file, row and column — it is never silently
turned into NULL.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any

# SQL table name -> CSV file name
TABLE_FILES: dict[str, str] = {
    "Departments":     "DEPARTMENTS_V6.csv",
    "Patients":        "PATIENTS_V6.csv",
    "Wards":           "WARDS_V6.csv",
    "Beds":            "BEDS_V6.csv",
    "Staff":           "STAFF_V6.csv",
    "Patient_Visits":  "PATIENT_VISITS_V6.csv",
    "Bed_Assignments": "BED_ASSIGNMENTS_V6.csv",
}
# Load order respects foreign keys.
LOAD_ORDER = list(TABLE_FILES)

COLUMNS: dict[str, list[tuple[str, str]]] = {
    "Departments": [("Department_ID", "int"), ("Department_Name", "str")],
    "Patients": [("Patient_ID", "int"), ("Date_Of_Birth", "date"), ("Gender", "str"),
                 ("Registration_Date", "datetime")],
    "Wards": [("Ward_ID", "int"), ("Ward_Name", "str"), ("Department_ID", "int"),
              ("Ward_Type", "str"), ("Capacity", "int")],
    "Beds": [("Bed_ID", "int"), ("Ward_ID", "int"), ("Bed_Status", "str")],
    "Staff": [("Staff_ID", "int"), ("Staff_Name", "str"), ("Staff_Shift", "str"),
              ("Staff_Role", "str"), ("Department_ID", "int")],
    "Patient_Visits": [
        ("Visit_ID", "int"), ("Patient_ID", "int"), ("Department_ID", "int"), ("Visit_Type", "str"),
        ("Registration_Time", "datetime"), ("Triage_Time", "datetime"),
        ("Consultation_Start_Time", "datetime"), ("Consultation_End_Time", "datetime"),
        ("Admission_Time", "datetime"), ("Discharge_Time", "datetime"),
        ("Visit_Status", "str"), ("Reason_for_cancellation", "str"),
    ],
    "Bed_Assignments": [("Assignment_ID", "int"), ("Visit_ID", "int"), ("Bed_ID", "int"),
                        ("Assignment_Start", "datetime"), ("Assignment_End", "datetime")],
}

_DT_FORMATS = (
    "%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
)


def parse_datetime(text: str) -> datetime:
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised date/time value {text!r}")


def _convert(value: str | None, kind: str) -> Any:
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    if kind == "int":
        return int(value)
    if kind == "datetime":
        return parse_datetime(value)
    if kind == "date":
        return parse_datetime(value).date()
    return value


def read_table(table: str, data_dir: Path) -> list[dict[str, Any]]:
    path = Path(data_dir) / TABLE_FILES[table]
    if not path.exists():
        raise FileNotFoundError(f"Missing data file: {path}")
    spec = COLUMNS[table]
    rows: list[dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c, _ in spec if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name}: missing expected columns {missing}")
        for line_no, raw in enumerate(reader, start=2):
            row: dict[str, Any] = {}
            for col, kind in spec:
                try:
                    row[col] = _convert(raw.get(col), kind)
                except ValueError as exc:
                    raise ValueError(f"{path.name} line {line_no}, column {col}: {exc}") from exc
            rows.append(row)
    return rows
