# CarePulse – Metrics Guide (for presentation)

For every number on the three dashboard views this guide gives three things:

* **What it is**: the plain-English meaning.
* **How it is calculated**: the exact rule, taken from the SQL in `backend/app/repositories/sql_repo.py`.
* **Why it matters**: the decision or question it supports.

The technical reference is `docs/METRICS.md`. This file is the talking-points version.

---

## 0. Ground rules that apply to every view

### 0.1 Where the numbers come from
All numbers are computed live in **SQL Server**. Nothing is mock data and nothing is read from CSV at runtime. Two tables carry most of the story:

| Table | One row is… | Key columns used |
|---|---|---|
| `Patient_Visits` | one visit to the hospital | `Registration_Time`, `Triage_Time`, `Consultation_Start_Time`, `Consultation_End_Time`, `Admission_Time`, `Discharge_Time`, `Visit_Type`, `Visit_Status`, `Reason_for_cancellation`, `Department_ID` |
| `Beds` / `Wards` | one physical bed / one ward | `Bed_Status` (Available, Occupied, Maintenance), `Ward_ID`, `Ward_Type`, `Department_ID` |

Supporting tables: `Bed_Assignments` (who used which bed, from when to when), `Staff` (role and shift), `Patients` (date of birth) and `Departments`.

A visit moves through these timestamps in order. Most of the time metrics measure the gaps between them:

```
Registration → Triage → Consultation Start → Consultation End → Admission → Discharge
   (arrives)   (nurse     (doctor sees        (doctor done)     (given a    (leaves)
               assesses)   patient)                              bed)
```

### 0.2 Two kinds of metric: "period" vs "live snapshot"
This is the most important idea to explain, and it prevents most audience confusion.

| Kind | Meaning | Reacts to date filter? | Examples |
|---|---|---|---|
| **Period metric** | Counts events that happened in the chosen dates | Yes | Admissions, Discharges, Avg Wait, Arrivals |
| **Live snapshot** | Describes how things are right now | No | Bed Occupancy, Active Patients, Waiting to be Seen |

### 0.3 Which date each metric follows
A date range is applied to the timestamp that defines the metric, not to a single shared date:

* Admissions follow `Admission_Time`.
* Discharges follow `Discharge_Time`.
* Visits, waits and arrivals follow `Registration_Time`.

So an admission on 31 Jan appears in January even if the patient registered earlier.

### 0.4 Data-cleaning rules (these make the numbers trustworthy)
* **Averages use only valid pairs.** Both timestamps must exist and the duration must be ≥ 0. Every average shows its sample size, such as "1,234 patients seen", so the audience can see how much data is behind it.
* **Maintenance beds are never counted as capacity.** See the Occupancy formula below.
* **Percentages never divide by zero.** If the denominator is 0, the result is 0%, or "—" for averages.
* **Empty is shown as empty.** If no data matches the filters, the card shows "—" or "No data". Nothing is invented.
* **Date presets end on the latest day that has data**, not today. "Last 7 days" is therefore never half empty.
* **End dates include the whole end day.**

### 0.5 Who sees what
| Role | Overview | Patient Flow | Bed Availability | Department scope |
|---|---|---|---|---|
| Dean | ✅ | ✅ | ✅ | All departments, with a department filter |
| Doctor | ✅ | ✅ | ✅ | Own department only |
| Nurse | ✅ | ❌ | ✅ | Own department only |

Department scoping is enforced on the server from the login token, so it cannot be bypassed from the browser.

---

# VIEW 1: Hospital Overview

**Purpose:** a quick, role-tailored health check of the hospital. It combines the current bed picture with recent activity.

**Filters:** a period preset (Last 7, 14, 30 or 90 days, All time, or Custom dates; the default is 14 days) and, for the Dean, a department filter.

Each role sees four KPI cards chosen to fit its job:

| Role | Cards shown | Reasoning |
|---|---|---|
| **Dean** | Admissions · Discharges · Avg Wait Time · Bed Occupancy | Hospital-wide throughput and capacity |
| **Doctor** | Active Patients · Waiting to be Seen · Avg Wait Time · Bed Occupancy | Own patient load and how long patients wait |
| **Nurse** | Active Patients · Bed Occupancy · Discharges · Avg Bed Stay | Ward workload and bed turnover |

## 1.1 KPI cards

### Admissions *(period metric)*
* **What:** the number of patients admitted to a bed in the period.
* **Calculation:** count of visits where `Admission_Time` is not empty and falls inside the selected dates (and department).
* **Why it matters:** it is the demand side of hospital flow, meaning how many patients needed inpatient care. A rising trend signals growing demand and a need for staff and beds.

### Discharges *(period metric)*
* **What:** the number of patients who left the hospital in the period.
* **Calculation:** count of visits where `Discharge_Time` is not empty and falls inside the selected dates.
* **Why it matters:** it is the supply side, because discharges free beds. Compare it with Admissions:
  * Admissions > Discharges means the hospital is filling up.
  * Admissions < Discharges means it is emptying.
  * Persistent imbalance leads to overcrowding or wasted capacity.

### Avg Wait Time *(period metric)*
* **What:** how long patients wait from arriving to seeing a doctor.
* **Calculation:** the mean of `Consultation_Start_Time − Registration_Time`, in minutes. It includes only visits registered in the period where a consultation actually started and the result is ≥ 0. The card sub-label shows how many patients that covers. It shows "—" if there are none.
* **Why it matters:** this is the main patient-experience and service-quality measure. Long waits mean worse satisfaction, more walk-outs and more clinical risk. It also exposes bottlenecks in doctor availability.
* **Talking point:** cancelled visits and patients not yet seen are excluded. That stops the average being dragged down by visits that never reached a doctor.

### Bed Occupancy *(live snapshot)*
* **What:** the share of usable beds that are in use right now.
* **Calculation:**
  ```
  Operational beds = Total beds − Maintenance beds
  Occupancy %      = Occupied beds ÷ Operational beds × 100
  ```
  The same formula and denominator are used on the Overview card, the Bed Availability gauge and every ward card, so the numbers always agree.
* **Why it matters:** it is the single best capacity indicator. The card turns red above 80%.
  * Too low means money is wasted on idle capacity.
  * Too high means no room for emergencies, longer ED boarding and higher risk. Around 85% is a common warning level in hospital management.
* **Talking point:** maintenance beds are excluded from the denominator because a bed that cannot be used is not capacity. Including it would understate how full the hospital really is.

### Active Patients *(live snapshot)*
* **What:** patients currently admitted in the hospital.
* **Calculation:** count of visits where `Visit_Status = 'Ongoing'`, `Admission_Time` exists and `Discharge_Time` is empty. Only the department filter applies, not the dates.
* **Why it matters:** it is the real-time patient load, which drives staffing and workload. For doctors it means "how many patients are under care now".

### Waiting to be Seen *(live snapshot, Doctor only)*
* **What:** patients who have registered but have not yet been seen.
* **Calculation:** count of visits where `Visit_Status = 'Ongoing'`, `Consultation_Start_Time` is empty and `Admission_Time` is empty. The card turns amber when it is above 0.
* **Why it matters:** it is the live queue. Avg Wait Time looks backward at completed visits, while this shows who is waiting right now and lets staff react immediately.

### Avg Bed Stay *(period metric, Nurse only)*
* **What:** how long a patient typically occupies a bed once placed in it.
* **Calculation:** the mean of `Assignment_End − Assignment_Start` from `Bed_Assignments`. It uses only finished assignments that ended in the period, for beds in the nurse's department. It is shown in hours, or in days from 48 h upward, with the number of stays.
* **Why it matters:** it measures bed turnover. Shorter stays free beds faster, and unusually long stays can point to delayed discharges or complications. It helps nurses plan bed availability.
* **Note:** it differs from Length of Stay on Patient Flow. Bed Stay is time in a bed, which can be several moves within one hospital stay. Length of Stay is time from admission to discharge.

## 1.2 Charts and panels

### Arrivals (stacked bar chart)
* **What:** how many visits were registered per day, split by visit type (Inpatient, Outpatient, Emergency).
* **Calculation:** count of visits grouped by day of `Registration_Time` and `Visit_Type`.
  * Days with no visits show 0.
  * Windows longer than 92 days are summed per week (Monday start) so the chart stays readable.
  * The window is capped at 366 days.
  * With no dates, it shows the 14 days ending on the latest day that has data.
* **Why it matters:** it shows demand trends and the mix of care types. A growing share of Emergency arrivals means more unplanned, resource-heavy demand.

### Beds by Department (Dean) / Beds by Ward (Doctor, Nurse)
* **What:** a stacked bar per department or ward showing Occupied, Available and Maintenance beds.
* **Calculation:** counts of `Bed_Status` from the `Beds` table, grouped by ward. For the Dean they are rolled up to department level.
* **Why it matters:** it shows where free capacity actually is, so staff can see at a glance which unit can take another patient and which is full.

### Current Patients by Age (Nurse only)
* **What:** how the currently admitted patients split into age groups: Under 18, 18–39, 40–64 and 65+.
* **Calculation:** the age of each currently admitted patient is worked out from `Date_Of_Birth` as of today. Patients are counted into the four bands, and the share of each band is shown. The population is the same one used for Active Patients.
* **Why it matters:** the age mix drives nursing workload. Elderly patients usually need more care, falls prevention and mobility help, and paediatric patients need different skills. It supports ward staffing and skill planning.

### Staff on Each Shift (Nurse only)
* **What:** the number of nurses and doctors rostered in each shift: Morning, Evening and Night.
* **Calculation:** count of `Staff` rows with role Nurse or Doctor, grouped by `Staff_Shift`, for the nurse's department.
* **Why it matters:** it shows whether coverage is balanced across the day. A thin night shift is a safety risk, so this supports rota planning.
* **Limit to mention:** the data has only a shift label per person, not a roster with hours. So this is headcount per shift and not a staffing-versus-workload ratio.

---

# VIEW 2: Patient Flow Analytics

**Audience:** Dean and Doctor.

**Purpose:** it answers "how do patients move through the hospital, and where do they get stuck?" The Dean sees all departments, and a Doctor sees only their own.

**Filters:** a date range (or "All dates"). Every metric on this page is a period metric.

## 2.1 Top KPI row

### Total Visits
* **What:** the number of visits registered in the period.
* **Calculation:** count of visits where `Registration_Time` is in range. This counts visits, not unique patients, so one patient who came three times counts three times.
* **Why it matters:** it is the overall demand and workload volume, and the baseline that percentages like the cancellation rate are measured against.

### Admissions
* **Calculation:** count of visits with `Admission_Time` in range (same as on the Overview).
* **Why it matters:** it shows how many visits turned into inpatient care. Compared with Total Visits, it shows how many visits needed a bed.

### Discharges
* **Calculation:** count of visits with `Discharge_Time` in range.
* **Why it matters:** it shows how many patients completed their stay, and it is the bed-release side of flow.

### Avg Wait Time
* **Calculation:** the mean of `Consultation_Start_Time − Registration_Time`, in minutes, for valid visits registered in range (see 1.1).
* **Why it matters:** it is the headline service-speed measure.

## 2.2 Clinical efficiency row

### Avg Consultation
* **What:** how long a doctor's consultation lasts.
* **Calculation:** the mean of `Consultation_End_Time − Consultation_Start_Time`, in minutes, for visits registered in the period. Only valid, non-negative pairs count, and the card shows the number of visits.
* **Why it matters:** it shows doctor time per patient, which feeds capacity planning. Consultations that are too short may risk quality, and ones that are too long create queues.

### Avg Length of Stay
* **What:** how long admitted patients stay in the hospital from admission to discharge.
* **Calculation:** the mean of `Discharge_Time − Admission_Time` for visits **discharged** in the period, in hours (shown as days from 48 h upward), with the number of stays.
* **Why it matters:** it is one of the most widely used hospital efficiency measures. A shorter stay at the same quality of care means more patients treated per bed, lower cost and a lower infection risk. A longer stay can point to delays in tests, in discharge planning or in care.

### Cancelled Visits
* **What:** the number of visits that were cancelled, and the share of all visits.
* **Calculation:** the count of visits with `Visit_Status = 'Cancelled'` in the period. The share is `Cancelled ÷ Total Visits × 100`.
* **Why it matters:** cancellations mean wasted slots and lost revenue. A high rate points to scheduling, access or communication problems. The reasons chart below shows what to fix.

## 2.3 Charts

### Monthly Trend (Admissions vs Discharges)
* **What:** two bars per month showing admissions and discharges.
* **Calculation:** admissions are grouped by the month of `Admission_Time` and discharges by the month of `Discharge_Time`. Months with no events are not invented.
* **Why it matters:** it shows seasonality and long-term direction. It also shows whether the hospital is accumulating patients (more admissions than discharges) or draining.

### Department Activity (Dean only)
* **What:** visits and admissions for each department side by side.
* **Calculation:** for every department, visits are counted by `Registration_Time` in range and admissions by `Admission_Time` in range. A department with no activity shows 0 and is not dropped. Departments are ordered by visit count.
* **Why it matters:** it compares workload across departments, which supports resource allocation. Comparing visits with admissions also shows each department's conversion to inpatient care.
* **Note:** it is hidden for Doctors, because comparing departments only makes sense across all of them.

### Time at Each Stage (average minutes)
* **What:** the three average durations that make up a patient's journey: Registration → Triage, Triage → Consultation, and Consultation length.
* **Calculation:** the mean of the gap between each pair of timestamps for visits registered in the period, using only valid non-negative pairs. The tooltip shows the sample size.
* **Why it matters:** this is the **bottleneck finder**. Total wait is a single number, but this chart shows which stage is slow: triage, waiting for a doctor or the consultation itself. That tells management exactly where to add staff.
* **Caveat to mention:** `Triage_Time` is recorded for only part of the visits, so the first two bars use fewer rows than the third. The page states the exact count under the chart.

### Arrivals by Hour of Day
* **What:** the number of visits registered in each of the 24 hours.
* **Calculation:** count of visits grouped by the hour of `Registration_Time`. There are always 24 bars, and empty hours show 0.
* **Why it matters:** it reveals the daily demand pattern and the peak hours. This is the evidence for shift scheduling, so the busiest hours get the most staff.

### Visit Type Breakdown
* **What:** the share of Inpatient, Outpatient and Emergency visits.
* **Calculation:** count per `Visit_Type` for visits registered in range. Each percentage is `type count ÷ total count × 100`.
* **Why it matters:** it shows the case mix, which drives resource needs. Emergency care needs immediate capacity, while outpatient care is schedulable.

### Visit Status Breakdown
* **What:** the share of visits that are Completed, Ongoing or Cancelled.
* **Calculation:** count per `Visit_Status` for visits registered in range, with percentages of the total.
* **Why it matters:** it is a health check on outcomes. A high Completed share is healthy, and a high Cancelled share is a problem to investigate.

### Why Visits Were Cancelled
* **What:** the reasons given for cancelled visits.
* **Calculation:** cancelled visits registered in range are grouped by `Reason_for_cancellation`. Empty or "Not Applicable" becomes "Not recorded". The top 6 reasons are shown and the rest are folded into "Other reasons". Each percentage is the share of all cancellations.
* **Why it matters:** it turns the cancellation count into an action list. If one reason dominates, fixing it has the biggest payoff.
* **Talking point:** a large "Not recorded" share is itself a finding, because it means the hospital is not capturing why visits fail.

---

# VIEW 3: Bed Availability

**Audience:** Dean, Doctor and Nurse.

**Purpose:** a **live snapshot** of bed capacity. Nothing on this page depends on dates. The Dean sees every ward, and Doctors and Nurses see their own department's wards.

## 3.1 KPI cards

### Total Beds
* **Calculation:** count of all rows in `Beds` for the wards in scope. The sub-label shows the operational beds (`total − maintenance`).
* **Why it matters:** it is the physical capacity baseline.

### Occupied
* **Calculation:** count of beds with `Bed_Status = 'Occupied'`. The sub-label shows `occupied ÷ operational × 100`.
* **Why it matters:** it shows how much capacity is in use right now.

### Available
* **Calculation:** count of beds with `Bed_Status = 'Available'`.
* **Why it matters:** it is the room to admit new patients, the number that matters most in an emergency surge.

### Maintenance
* **Calculation:** count of beds with `Bed_Status = 'Maintenance'`. The card is labelled "Excluded from occupancy".
* **Why it matters:** these beds cannot be used. A large maintenance count quietly cuts real capacity, so it flags repair backlogs.

## 3.2 Charts and panels

### Status Breakdown
* **What:** the share of beds that are Occupied, Available or Maintenance.
* **Calculation:** the count of each `Bed_Status` divided by the total number of beds, as a percentage. Statuses with no beds, such as Reserved, are not shown.
* **Why it matters:** it is a one-glance picture of capacity mix.
* **Note:** here the percentages use **all** beds as the denominator, because they describe the mix of statuses. The occupancy percentage elsewhere uses operational beds. Both are correct and answer different questions.

### Occupancy Gauge
* **What:** one large percentage for the whole scope, with a progress bar.
* **Calculation:** `Occupied ÷ (Total − Maintenance) × 100`.
* **Colour thresholds:**
  * green when it is 60% or below
  * amber above 60% and up to 80%
  * red above 80%
* **Why it matters:** it gives an instant capacity signal, and the colour tells non-experts whether action is needed.

### Ward Breakdown (cards, with an optional filter by ward type)
* **What:** one card per ward showing its department, ward type, a bar, "occupied / operational" and the occupancy %.
* **Calculation:** the same occupancy formula computed per ward: `ward occupied ÷ (ward beds − ward maintenance) × 100`. Wards are sorted busiest first. The ward-type filter (such as Emergency, Pediatric or Private) only narrows what is shown.
* **Why it matters:** hospital-wide occupancy can hide problems. An overall 70% could include a 100%-full ICU next to half-empty general wards. Ward cards show exactly where pressure is, so patients can be redirected before a ward overflows.

---

## Summary table: every metric at a glance

| # | Metric | View(s) | Type | One-line formula |
|---|---|---|---|---|
| 1 | Admissions | Overview, Patient Flow | Period | Visits with `Admission_Time` in range |
| 2 | Discharges | Overview, Patient Flow | Period | Visits with `Discharge_Time` in range |
| 3 | Avg Wait Time | Overview, Patient Flow | Period | Mean (`Consultation_Start − Registration`) in minutes, valid pairs only |
| 4 | Bed Occupancy % | Overview, Bed Availability | Live | Occupied ÷ (Total − Maintenance) × 100 |
| 5 | Active Patients | Overview | Live | Ongoing visits, admitted, not discharged |
| 6 | Waiting to be Seen | Overview (Doctor) | Live | Ongoing visits, no consultation start, no admission |
| 7 | Avg Bed Stay | Overview (Nurse) | Period | Mean (`Assignment_End − Assignment_Start`), finished stays |
| 8 | Arrivals | Overview | Period | Visits per day (or week) by visit type |
| 9 | Beds by Dept / Ward | Overview | Live | Occupied / Available / Maintenance counts |
| 10 | Current Patients by Age | Overview (Nurse) | Live | Admitted patients grouped by age today |
| 11 | Staff on Each Shift | Overview (Nurse) | Live | Nurses and doctors counted per shift |
| 12 | Total Visits | Patient Flow | Period | Visits with `Registration_Time` in range |
| 13 | Avg Consultation | Patient Flow | Period | Mean (`Consultation_End − Consultation_Start`) |
| 14 | Avg Length of Stay | Patient Flow | Period | Mean (`Discharge − Admission`) for discharges in range |
| 15 | Cancelled Visits (and %) | Patient Flow | Period | Cancelled count; ÷ Total Visits × 100 |
| 16 | Monthly Trend | Patient Flow | Period | Admissions and discharges per month |
| 17 | Department Activity | Patient Flow (Dean) | Period | Visits and admissions per department |
| 18 | Time at Each Stage | Patient Flow | Period | Mean gap: Reg→Triage, Triage→Consult, Consult length |
| 19 | Arrivals by Hour | Patient Flow | Period | Visits by hour of `Registration_Time` (24 buckets) |
| 20 | Visit Type Breakdown | Patient Flow | Period | Count and % per `Visit_Type` |
| 21 | Visit Status Breakdown | Patient Flow | Period | Count and % per `Visit_Status` |
| 22 | Cancellation Reasons | Patient Flow | Period | Top 6 reasons plus "Other", as % of cancellations |
| 23 | Total / Occupied / Available / Maintenance beds | Bed Availability | Live | Counts by `Bed_Status` |
| 24 | Status Breakdown | Bed Availability | Live | Bed count per status ÷ all beds |
| 25 | Occupancy Gauge | Bed Availability | Live | Occupied ÷ operational × 100, with colour bands |
| 26 | Ward Breakdown | Bed Availability | Live | Occupancy per ward, busiest first |

---

## Suggested story for the presentation

1. **Bed Availability** answers "do we have room right now?" through capacity and occupancy.
2. **Overview** answers "how is the hospital doing today?" through throughput, waits and load, tailored per role.
3. **Patient Flow** answers "where and why do patients get delayed, and what can we improve?" through stages, peak hours, length of stay and cancellations.

Together they cover **capacity → activity → efficiency**.

## Honest limitations (good to state up front)

* **Triage time is incomplete.** It is missing for many visits, so the first two stage averages use fewer visits. The sample size is always shown.
* **Not all bed assignments match a bed.** 44 bed assignments point to Bed_IDs that do not exist in the bed list, so they are excluded from Avg Bed Stay. This is reported, not hidden.
* **No data on revenue, cost, satisfaction, outcomes or readmissions.** The dataset has none, so no such metrics are shown.
* **Staffing is headcount per shift only.** There are no roster hours, so no staff-to-patient ratio is possible.
* **No Reserved beds exist in the data.** The status is supported but currently always 0 and is hidden from the breakdown.
* **Ages use today's date.** The age bands are calculated as of the day the page is viewed.
