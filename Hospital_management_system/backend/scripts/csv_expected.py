"""
scripts/csv_expected.py
=======================
INDEPENDENT pandas implementation of the dashboard metrics, computed straight
from the V6 CSV files.  It deliberately shares no code with the SQL layer, so
comparing the two catches mistakes in either one.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

FMT = "%m/%d/%Y %H:%M"
TIME_COLS = ["Registration_Time", "Triage_Time", "Consultation_Start_Time",
             "Consultation_End_Time", "Admission_Time", "Discharge_Time"]


def load(data_dir: Path):
    rd = lambda n: pd.read_csv(Path(data_dir) / n, dtype=str, keep_default_na=False)
    v = rd("PATIENT_VISITS_V6.csv")
    for c in TIME_COLS:
        v[c] = pd.to_datetime(v[c].replace("", None), format=FMT)
    v["Department_ID"] = v["Department_ID"].astype(int)
    beds, wards = rd("BEDS_V6.csv"), rd("WARDS_V6.csv")
    beds["Ward_ID"] = beds["Ward_ID"].astype(int)
    wards["Ward_ID"] = wards["Ward_ID"].astype(int)
    wards["Department_ID"] = wards["Department_ID"].astype(int)
    return v, beds, wards, rd("DEPARTMENTS_V6.csv"), rd("BED_ASSIGNMENTS_V6.csv")


def expected_visit_metrics(v, start=None, end=None, dept=None):
    """start/end: 'YYYY-MM-DD' strings, both inclusive. Returns the numbers the API must show."""
    lo = pd.Timestamp(start) if start else None
    hi = (pd.Timestamp(end) + pd.Timedelta(days=1)) if end else None

    def inr(s):
        m = pd.Series(True, index=s.index)
        if lo is not None: m &= s >= lo
        if hi is not None: m &= s < hi
        return m

    d = v if dept is None else v[v.Department_ID == dept]
    wait = (d.Consultation_Start_Time - d.Registration_Time).dt.total_seconds() / 60
    wmask = wait.notna() & (wait >= 0) & inr(d.Registration_Time)
    adm = d.Admission_Time.notna() & inr(d.Admission_Time)
    dis = d.Discharge_Time.notna() & inr(d.Discharge_Time)
    cur = (d.Visit_Status == "Ongoing") & d.Admission_Time.notna() & d.Discharge_Time.isna()
    months_a = d.loc[adm, "Admission_Time"].dt.strftime("%Y-%m").value_counts()
    months_d = d.loc[dis, "Discharge_Time"].dt.strftime("%Y-%m").value_counts()
    trend = {m: (int(months_a.get(m, 0)), int(months_d.get(m, 0))) for m in sorted(set(months_a.index) | set(months_d.index))}
    reg = inr(d.Registration_Time)
    return {
        "total_visits": int(reg.sum()),
        "admissions": int(adm.sum()),
        "discharges": int(dis.sum()),
        "avg_wait_minutes": round(float(wait[wmask].mean()), 1) if wmask.any() else None,
        "wait_samples": int(wmask.sum()),
        "current_admissions": int(cur.sum()),
        "trend": trend,
        "visit_type": d[reg].Visit_Type.value_counts().to_dict(),
        "visit_status": d[reg].Visit_Status.value_counts().to_dict(),
    }


def expected_bed_metrics(beds, wards, dept=None):
    m = beds.merge(wards[["Ward_ID", "Department_ID"]], on="Ward_ID", how="inner")
    if dept is not None:
        m = m[m.Department_ID == dept]
    total = len(m)
    occ = int((m.Bed_Status == "Occupied").sum())
    mnt = int((m.Bed_Status == "Maintenance").sum())
    avl = int((m.Bed_Status == "Available").sum())
    oper = total - mnt
    return {"total_beds": total, "occupied": occ, "available": avl, "maintenance": mnt,
            "operational_beds": oper, "occupancy_pct": round(occ / oper * 100, 1) if oper else 0.0}
