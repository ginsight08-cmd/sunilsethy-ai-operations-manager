"""Configurable case-management analysis for the AI Operations Manager."""

from datetime import datetime, timezone

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "Case_ID",
    "Created_At",
    "Status",
    "Priority",
    "Owner",
    "Category",
    "SLA_Due_At",
]

OPTIONAL_COLUMNS = [
    "Customer",
    "Description",
    "Last_Updated_At",
    "Resolution_At",
    "Resolution_Notes",
]

CLOSED_STATUSES = {"resolved", "closed", "cancelled"}
STATUS_OPTIONS = ["New", "Assigned", "In Progress", "Pending", "Resolved", "Closed", "Cancelled"]
PRIORITY_OPTIONS = ["Critical", "High", "Medium", "Low"]


def sample_cases():
    now = pd.Timestamp.now(tz="UTC").floor("min").tz_localize(None)
    return pd.DataFrame([
        {
            "Case_ID": "CASE-1001", "Created_At": now - pd.Timedelta(hours=30),
            "Status": "In Progress", "Priority": "High", "Owner": "Agent 1",
            "Category": "Service Request", "SLA_Due_At": now + pd.Timedelta(hours=6),
            "Customer": "Customer A", "Description": "Example active case",
            "Last_Updated_At": now - pd.Timedelta(hours=2), "Resolution_At": pd.NaT,
            "Resolution_Notes": "",
        },
        {
            "Case_ID": "CASE-1002", "Created_At": now - pd.Timedelta(hours=55),
            "Status": "New", "Priority": "Critical", "Owner": "Unassigned",
            "Category": "Incident", "SLA_Due_At": now - pd.Timedelta(hours=7),
            "Customer": "Customer B", "Description": "Example breached case",
            "Last_Updated_At": now - pd.Timedelta(hours=20), "Resolution_At": pd.NaT,
            "Resolution_Notes": "",
        },
    ])


def normalize_cases(df, now=None, due_soon_hours=4, stale_hours=24):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("The case file contains no usable rows.")

    cases = df.copy()
    cases.columns = [str(column).replace("\ufeff", "").strip() for column in cases.columns]
    cases = cases.dropna(axis=0, how="all").dropna(axis=1, how="all")
    missing = [column for column in REQUIRED_COLUMNS if column not in cases.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))

    for column in OPTIONAL_COLUMNS:
        if column not in cases.columns:
            cases[column] = pd.NaT if column.endswith("_At") else ""

    for column in ["Created_At", "SLA_Due_At", "Last_Updated_At", "Resolution_At"]:
        cases[column] = pd.to_datetime(cases[column], errors="coerce", utc=True).dt.tz_localize(None)

    if cases["Created_At"].isna().any() or cases["SLA_Due_At"].isna().any():
        raise ValueError("Created_At and SLA_Due_At must contain valid dates and times.")

    for column in ["Case_ID", "Status", "Priority", "Owner", "Category", "Customer", "Description", "Resolution_Notes"]:
        cases[column] = cases[column].fillna("").astype(str).str.strip()

    if cases["Case_ID"].eq("").any() or cases["Case_ID"].duplicated().any():
        raise ValueError("Case_ID values must be present and unique.")

    now = pd.Timestamp(now or datetime.now(timezone.utc)).tz_localize(None)
    status_key = cases["Status"].str.lower()
    active = ~status_key.isin(CLOSED_STATUSES)
    cases["Is_Open"] = active
    cases["SLA_Breached"] = active & cases["SLA_Due_At"].lt(now)
    cases["Age_Hours"] = ((now - cases["Created_At"]).dt.total_seconds() / 3600).clip(lower=0).round(1)
    cases["SLA_Hours_Remaining"] = ((cases["SLA_Due_At"] - now).dt.total_seconds() / 3600).round(1)
    cases["Stale_Hours"] = (
        (now - cases["Last_Updated_At"].fillna(cases["Created_At"])).dt.total_seconds() / 3600
    ).clip(lower=0).round(1)

    priority_score = cases["Priority"].str.lower().map({"critical": 3, "high": 2, "medium": 1, "low": 0}).fillna(1)
    cases["Risk_Score"] = (
        priority_score
        + cases["SLA_Breached"].astype(int) * 3
        + (active & cases["SLA_Hours_Remaining"].between(0, due_soon_hours)).astype(int) * 2
        + (active & cases["Stale_Hours"].ge(stale_hours)).astype(int)
        + (active & cases["Owner"].str.lower().isin({"", "unassigned", "none"})).astype(int) * 2
    )
    cases["Risk_Level"] = np.select(
        [cases["Risk_Score"] >= 6, cases["Risk_Score"] >= 4, cases["Risk_Score"] >= 2],
        ["Critical", "High", "Watch"], default="Normal",
    )
    return cases


def analyze_cases(df, now=None, due_soon_hours=4, stale_hours=24):
    cases = normalize_cases(df, now=now, due_soon_hours=due_soon_hours, stale_hours=stale_hours)
    active = cases[cases["Is_Open"]]
    resolved = cases[~cases["Is_Open"]]
    valid_resolution = resolved.dropna(subset=["Resolution_At"])
    resolution_hours = (
        (valid_resolution["Resolution_At"] - valid_resolution["Created_At"]).dt.total_seconds() / 3600
    )

    overall = {
        "total": len(cases),
        "open": len(active),
        "resolved": len(resolved),
        "breached": int(active["SLA_Breached"].sum()),
        "due_soon": int((active["SLA_Hours_Remaining"].between(0, due_soon_hours)).sum()),
        "unassigned": int(active["Owner"].str.lower().isin({"", "unassigned", "none"}).sum()),
        "critical_risk": int(active["Risk_Level"].eq("Critical").sum()),
        "sla_compliance_pct": float(round((1 - active["SLA_Breached"].mean()) * 100, 1)) if len(active) else 100.0,
        "avg_resolution_hours": round(float(resolution_hours.mean()), 1) if len(resolution_hours) else None,
    }
    return {"cases": cases, "overall": overall}


def make_ai_prompt(result):
    overall = result["overall"]
    risky = result["cases"].sort_values(["Risk_Score", "SLA_Hours_Remaining"], ascending=[False, True]).head(100)
    return (
        "CASE MANAGEMENT ANALYSIS\n\n"
        f"Total: {overall['total']} | Open: {overall['open']} | Resolved: {overall['resolved']} | "
        f"SLA breached: {overall['breached']} | Due within 4 hours: {overall['due_soon']} | "
        f"Unassigned: {overall['unassigned']} | SLA compliance: {overall['sla_compliance_pct']}%\n\n"
        "Prioritized cases:\n" + risky.to_json(orient="records", date_format="iso")
    )
