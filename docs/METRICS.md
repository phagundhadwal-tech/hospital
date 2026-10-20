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

### Doctor / nurse metrics
Averages use only rows where both timestamps exist and the duration is ≥ 0; the response carries the sample size (`*_n`).

| Metric | Table | Formula |
|---|---|---|
| Waiting to be Seen | Patient_Visits | `Visit_Status='Ongoing'` AND no `Consultation_Start_Time` AND no `Admission_Time`. Live snapshot, department filter only |
| Time at each stage | Patient_Visits | Registration→Triage, Triage→Consultation start, Consultation start→end; visits registered in range. `Triage_Time` is empty for many visits, so the first two use fewer rows |
| Avg Length of Stay | Patient_Visits | mean `Discharge_Time − Admission_Time`, discharges in range (hours; shown as days from 48 h) |
| Arrivals by hour | Patient_Visits | count of visits by hour of `Registration_Time`, always 24 buckets |
| Cancellation reasons | Patient_Visits | cancelled visits registered in range grouped by `Reason_for_cancellation` (`Not Applicable`/empty → "Not recorded"); top 6 plus "Other reasons" |
| Arrivals (Overview) | Patient_Visits | visits per day by `Visit_Type` for the chosen dates; days with no visits show 0. Windows over 92 days are summed per week (Monday start), and the window is capped at 366 days. With no dates it is the 14 days ending on the latest `Registration_Time` in scope (not the wall clock) |
| Overview date presets | Patient_Visits | "Last N days" end on the latest day that has data (`GET /analytics/data-range`), not on today. "All time" sends no limit to the cards. The period filter changes Admissions, Discharges, Avg Wait, Avg Bed Stay and the arrivals chart; beds, Active Patients and Waiting to be Seen stay live |
| Beds by Ward / Department | Wards ⟕ Beds | occupied, free and maintenance bed counts of the current snapshot (no percentage) |
| Busiest wards | Wards ⟕ Beds | top 5 wards by occupancy (same formula as above) |
| Current patients by age | Patient_Visits ⋈ Patients | age today (from `Date_Of_Birth`) of every currently admitted patient, in 4 groups |
| Staff on each shift | Staff | count of Nurses and Doctors per `Staff_Shift`, in the caller's department |
| Avg Bed Stay | Bed_Assignments ⋈ Beds ⋈ Wards | mean `Assignment_End − Assignment_Start` for finished assignments ending in range, beds in the caller's department wards (assignments to unknown Bed_IDs are excluded by the join) |

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
