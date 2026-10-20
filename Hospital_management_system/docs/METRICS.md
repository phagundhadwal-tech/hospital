# CarePulse – metric definitions (SQL Server)

All numbers come from SQL Server aggregates (`backend/app/repositories/sql_repo.py`).
The API never computes a KPI from mock data. Source tables are the V6 dataset.

## Filters and date behaviour
| Filter | Behaviour |
|---|---|
| `start_date` | inclusive, 00:00:00 of that day |
| `end_date` | inclusive of the **whole** day (SQL: `< end_date + 1 day`) |
| `department_id` | full-access roles only; department-scoped roles are always forced to the department in their login token |
| `visit_type`, `visit_status` | optional exact match (supported by the API; the current UI has no controls for them) |
| Time zone | none – the data has no offsets; wall-clock hospital time is used everywhere |

Each date range is applied to the timestamp that defines the metric:

| Metric | Table | Columns | Formula |
|---|---|---|---|
| Total Admissions | Patient_Visits | Admission_Time | rows with `Admission_Time` in range |
| Discharges | Patient_Visits | Discharge_Time | rows with `Discharge_Time` in range |
| Total Visits (Patient Flow) | Patient_Visits | Registration_Time | rows with `Registration_Time` in range (visits, not unique patients) |
| Avg Wait Time | Patient_Visits | Registration_Time, Consultation_Start_Time | mean minutes of `Consultation_Start_Time − Registration_Time`, only when both exist and result ≥ 0, visit registered in range. `null` (shown “—”) when no valid pair |
| Active Patients / “currently admitted” | Patient_Visits | Visit_Status, Admission_Time, Discharge_Time | `Visit_Status='Ongoing'` AND admitted AND not discharged. A **snapshot** – not date filtered (department filter applies) |
| Monthly Admissions & Discharges | Patient_Visits | Admission_Time / Discharge_Time | admissions grouped by admission month, discharges by discharge month; months without events are not invented |
| Department Activity | Departments ⟕ Patient_Visits | Department_ID, Registration_Time, Admission_Time | visits registered in range; admissions with `Admission_Time` in range; departments with none show 0 |
| Visit Type / Status breakdown | Patient_Visits | Visit_Type, Visit_Status | counts of visits registered in range; % of that total |
| Total / Occupied / Available / Maintenance / Reserved beds | Beds ⟕ Wards | Bed_Status, Ward_ID, Department_ID | counts of the **current** `Bed_Status` snapshot |
| Operational beds | Beds | Bed_Status | all beds − `Maintenance` beds |
| **Bed Occupancy %** | Beds | Bed_Status | `Occupied ÷ Operational × 100` – the same denominator for the KPI card, gauge and every ward card; 0 when there are no operational beds |
| Ward occupancy | Wards ⟕ Beds | | per ward, same formula |

Status values in the V6 data: `Visit_Status` = Completed / Cancelled / Ongoing; `Bed_Status` = Available / Occupied / Maintenance (no `Reserved` beds exist, so that card correctly shows 0).

## Data-quality rules
* Negative waiting durations are excluded from averages and counted in `GET /api/analytics/data-quality`.
* Visits without a consultation start (cancelled / not yet seen) are excluded from wait averages.
* Maintenance beds are never counted as available or occupied-capacity.
* No joins can multiply rows: every aggregate is computed on a single table or a one-to-many join counted from the "many" side.

## Findings in the supplied V6 files (reported, not altered)
| Finding | Count |
|---|---|
| Bed assignments whose `Bed_ID` is not in BEDS_V6 (Bed_IDs 5, 18, 48, 71, 158, 171, 181, 217, 287 are missing) | 44 |
| Wards where number of beds ≠ `Capacity` (300 capacity vs 291 beds) | 9 |
| Visits with no `Consultation_Start_Time` | 337 |
| Negative durations / discharge before admission | 0 |

Because of the missing Bed_IDs, `Bed_Assignments.Bed_ID` has **no foreign key** to `Beds`.

## Metrics that are NOT available (schema gaps)
The dataset has no revenue, cost, satisfaction, outcome or forecast fields, and no patient-level readmission flag is exposed, so none of those are shown.
`Staff` has no shift-roster/time data beyond `Staff_Shift`, so no staffing-vs-load metric is produced. If you want an MD/Dean page, average length of stay (`Discharge_Time − Admission_Time`) and a 30-day readmission rate (same `Patient_ID` re-admitted within 30 days) can be computed from existing columns – they are not wired into the UI because the existing dashboard has no such page.
