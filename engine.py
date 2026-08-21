import json

import numpy as np
import pandas as pd


REQUIRED = [
    "Employee_ID",
    "Team",
    "Target",
    "Production",
    "AHT_Actual",
    "Quality_%",
    "SLA_%",
    "Attendance",
    "Error_Count",
]


def _clean_column_names(df):
    df = df.copy()
    df.columns = [str(column).replace("\ufeff", "").strip() for column in df.columns]
    return df


def _normalize_numeric_columns(df):
    df = df.copy()
    numeric_columns = ["Target", "Production", "AHT_Actual", "AHT_Target", "Quality_%", "SLA_%", "Error_Count"]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def _normalize_text_columns(df):
    df = df.copy()
    text_columns = ["Employee_ID", "Employee_Name", "Team", "Attendance", "Error_Category"]
    for column in text_columns:
        if column in df.columns:
            df[column] = df[column].fillna("").astype(str).str.strip()
    return df


def _safe_percentage(numerator, denominator):
    numerator = pd.to_numeric(numerator, errors="coerce").fillna(0)
    denominator = pd.to_numeric(denominator, errors="coerce").fillna(0)
    result = np.where(denominator != 0, (numerator / denominator) * 100, 0)
    return pd.Series(result, index=numerator.index)


def analyze_data(df, productivity_target=90, quality_target=95, sla_target=97, aht_target=50):
    if df is None:
        raise ValueError("No dataframe was provided.")
    if not isinstance(df, pd.DataFrame):
        raise ValueError("Invalid data format. Expected a pandas DataFrame.")
    if df.empty:
        raise ValueError("The uploaded file contains no usable rows.")

    df = df.copy()
    df = _clean_column_names(df)
    df = _normalize_text_columns(df)
    df = _normalize_numeric_columns(df)
    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")

    if df.empty:
        raise ValueError("The uploaded file contains no usable data after cleaning.")

    missing = [column for column in REQUIRED if column not in df.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing) + ". Please verify the uploaded file headers.")

    numeric_defaults = {"Target": 0, "Production": 0, "AHT_Actual": 0, "Quality_%": 0, "SLA_%": 0, "Error_Count": 0}
    for column, default in numeric_defaults.items():
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(default)

    df["Employee_ID"] = df["Employee_ID"].fillna("Unknown").astype(str).str.strip()
    df["Team"] = df["Team"].fillna("Unknown Team").astype(str).str.strip()
    df["Attendance"] = df["Attendance"].fillna("").astype(str).str.strip()

    if "Productivity_%" not in df.columns:
        df["Productivity_%"] = _safe_percentage(df["Production"], df["Target"]).round(1)
    else:
        df["Productivity_%"] = pd.to_numeric(df["Productivity_%"], errors="coerce")
        calculated_productivity = _safe_percentage(df["Production"], df["Target"])
        df["Productivity_%"] = df["Productivity_%"].fillna(calculated_productivity).fillna(0).round(1)

    team = (
        df.groupby("Team", dropna=False)
        .agg(
            Records=("Employee_ID", "count"),
            Target=("Target", "sum"),
            Production=("Production", "sum"),
            Avg_AHT=("AHT_Actual", "mean"),
            Avg_Quality=("Quality_%", "mean"),
            Avg_SLA=("SLA_%", "mean"),
            Absences=("Attendance", lambda s: (s.astype(str).str.strip().str.lower().isin(["absent", "absence", "a"])).sum()),
            Errors=("Error_Count", "sum"),
        )
        .reset_index()
    )

    team["Productivity_%"] = _safe_percentage(team["Production"], team["Target"]).round(1)
    team["Absence_%"] = np.where(team["Records"] != 0, (team["Absences"] / team["Records"] * 100), 0).round(1)
    team["AHT_Gap"] = (team["Avg_AHT"] - aht_target).round(1)
    team["Avg_AHT"] = team["Avg_AHT"].fillna(0).round(1)
    team["Avg_Quality"] = team["Avg_Quality"].fillna(0).round(1)
    team["Avg_SLA"] = team["Avg_SLA"].fillna(0).round(1)

    # Group by Employee_Name too when it's present, so the employee-level
    # table can actually show names, not just IDs. Falls back to grouping
    # by ID + Team only if Employee_Name wasn't supplied — this column is
    # not in REQUIRED, so the engine must not assume it's always there.
    group_cols = ["Employee_ID", "Team"]
    if "Employee_Name" in df.columns:
        group_cols = ["Employee_ID", "Employee_Name", "Team"]

    employees = (
        df.groupby(group_cols, dropna=False)
        .agg(
            Avg_Productivity=("Productivity_%", "mean"),
            Avg_AHT=("AHT_Actual", "mean"),
            Avg_Quality=("Quality_%", "mean"),
            Avg_SLA=("SLA_%", "mean"),
            Absences=("Attendance", lambda s: (s.astype(str).str.strip().str.lower().isin(["absent", "absence", "a"])).sum()),
            Errors=("Error_Count", "sum"),
        )
        .reset_index()
    )

    employees["Avg_Productivity"] = employees["Avg_Productivity"].fillna(0).round(1)
    employees["Avg_AHT"] = employees["Avg_AHT"].fillna(0).round(1)
    employees["Avg_Quality"] = employees["Avg_Quality"].fillna(0).round(1)
    employees["Avg_SLA"] = employees["Avg_SLA"].fillna(0).round(1)
    employees["AHT_Gap"] = (employees["Avg_AHT"] - aht_target).round(1)

    employees["Risk_Score"] = (
        (employees["Avg_Productivity"] < productivity_target).astype(int)
        + (employees["Avg_Quality"] < quality_target).astype(int)
        + (employees["Avg_SLA"] < sla_target).astype(int)
        + (employees["AHT_Gap"] > 10).astype(int)
    )

    employees["Risk_Level"] = np.select(
        [employees["Risk_Score"] >= 3, employees["Risk_Score"] == 2, employees["Risk_Score"] == 1],
        ["Critical", "High", "Watch"],
        default="Normal",
    )

    findings = []
    actions = []

    for _, row in team.iterrows():
        evidence = []
        if row["Productivity_%"] < productivity_target:
            evidence.append(f"Productivity {row['Productivity_%']:.1f}% < {productivity_target}%")
        if row["Avg_Quality"] < quality_target:
            evidence.append(f"Quality {row['Avg_Quality']:.1f}% < {quality_target}%")
        if row["Avg_SLA"] < sla_target:
            evidence.append(f"SLA {row['Avg_SLA']:.1f}% < {sla_target}%")
        if row["AHT_Gap"] > 0:
            evidence.append(f"AHT {row['AHT_Gap']:.1f} above target")
        if row["Absence_%"] > 8:
            evidence.append(f"Absence {row['Absence_%']:.1f}% > 8%")

        if evidence:
            findings.append(["High", row["Team"], "; ".join(evidence), "Evidence indicates a performance gap; causal root cause requires validation."])
            action = "Investigate workload/task mix and review targeted coaching opportunities."
            if row["AHT_Gap"] > 10:
                action = "Review high-AHT workflow and run process-efficiency coaching."
            if row["Productivity_%"] < productivity_target and row["Avg_Quality"] >= quality_target:
                action = "Review productivity blockers, workload distribution, and process efficiency."
            if row["Avg_Quality"] < quality_target:
                action = "Conduct quality root-cause analysis and targeted quality coaching."
            if row["Avg_SLA"] < sla_target:
                action = "Review SLA misses, queue management, work allocation, and turnaround time."
            actions.append([row["Team"], "; ".join(evidence), action, "Operations Manager / Team Lead", "High", "Within 2 business days", "Improve KPI performance without reducing quality/SLA."])

    findings = pd.DataFrame(findings, columns=["Severity", "Team", "Finding", "Root_Cause_Position"])
    actions = pd.DataFrame(actions, columns=["Team", "Issue", "Recommended_Action", "Owner_Role", "Priority", "Due", "Success_Metric"])

    total_target = float(df["Target"].sum())
    total_production = float(df["Production"].sum())
    overall_productivity = (total_production / total_target * 100) if total_target > 0 else 0
    overall_quality = float(df["Quality_%"].mean())
    overall_sla = float(df["SLA_%"].mean())
    overall_aht = float(df["AHT_Actual"].mean())

    overall = {
        "productivity": round(overall_productivity, 2),
        "quality": round(overall_quality, 2),
        "sla": round(overall_sla, 2),
        "aht": round(overall_aht, 2),
    }

    return {"team": team, "employees": employees, "findings": findings, "actions": actions, "overall": overall}


def make_ai_prompt(result):
    if not isinstance(result, dict):
        raise ValueError("Invalid analysis result supplied to AI prompt.")
    payload = {
        "team_performance": result.get("team", pd.DataFrame()).to_dict(orient="records"),
        "employee_risk": result.get("employees", pd.DataFrame()).to_dict(orient="records"),
        "findings": result.get("findings", pd.DataFrame()).to_dict(orient="records"),
        "actions": result.get("actions", pd.DataFrame()).to_dict(orient="records"),
    }
    return "PROMPT_HEADER\n\nDATA:\n" + json.dumps(payload, indent=2, default=str)
