
import json

import pandas as pd
import numpy as np
import json
import pandas as pd


# ============================================================
# GENERATIVE INSIGHT | AI OPERATIONS COPILOT
# ENGINE
# ============================================================

REQUIRED = [
    "Employee_ID","Team","Target","Production","AHT_Actual",
    "Quality_%","SLA_%","Attendance","Error_Count"
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

def analyze_data(df, productivity_target=90, quality_target=95, sla_target=97, aht_target=50):

# ============================================================
# DATA CLEANING HELPERS
# ============================================================

def _clean_column_names(df):
    """
    Normalize uploaded dataframe column names.

    Handles:
    - Leading/trailing spaces
    - BOM characters
    - Accidental whitespace
    - Excel/CSV column formatting issues
    """

    df = df.copy()

    df.columns = [
        str(column)
        .replace("\ufeff", "")
        .strip()
        for column in df.columns
    ]

    return df


def _normalize_numeric_columns(df):
    """
    Safely convert operational KPI columns to numeric values.
    Invalid values are converted to NaN and then filled where appropriate.
    """

    df = df.copy()

    numeric_columns = [
        "Target",
        "Production",
        "AHT_Actual",
        "AHT_Target",
        "Quality_%",
        "SLA_%",
        "Error_Count",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df


def _normalize_text_columns(df):
    """
    Clean important text columns.
    """

    df = df.copy()
    missing = [c for c in REQUIRED if c not in df.columns]

    text_columns = [
        "Employee_ID",
        "Employee_Name",
        "Team",
        "Attendance",
        "Error_Category",
    ]

    for column in text_columns:
        if column in df.columns:
            df[column] = (
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    return df


def _safe_percentage(numerator, denominator):
    """
    Safely calculate percentage without division-by-zero errors.
    """

    numerator = pd.to_numeric(
        numerator,
        errors="coerce",
    ).fillna(0)

    denominator = pd.to_numeric(
        denominator,
        errors="coerce",
    ).fillna(0)

    result = np.where(
        denominator != 0,
        (numerator / denominator) * 100,
        0,
    )

    return pd.Series(
        result,
        index=numerator.index,
    )


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_data(
    df,
    productivity_target=90,
    quality_target=95,
    sla_target=97,
    aht_target=50,
):
    """
    Analyze operational Excel/CSV data.

    Returns:
        team
        employees
        findings
        actions
        overall
    """

    # --------------------------------------------------------
    # BASIC VALIDATION
    # --------------------------------------------------------

    if df is None:
        raise ValueError("No dataframe was provided.")

    if not isinstance(df, pd.DataFrame):
        raise ValueError(
            "Invalid data format. Expected a pandas DataFrame."
        )

    if df.empty:
        raise ValueError(
            "The uploaded file contains no usable rows."
        )

    # --------------------------------------------------------
    # CLEAN DATA
    # --------------------------------------------------------

    df = df.copy()

    df = _clean_column_names(df)
    df = _normalize_text_columns(df)
    df = _normalize_numeric_columns(df)

    # Remove completely empty rows
    df = df.dropna(
        axis=0,
        how="all",
    )

    # Remove completely empty columns
    df = df.dropna(
        axis=1,
        how="all",
    )

    if df.empty:
        raise ValueError(
            "The uploaded file contains no usable data after cleaning."
        )

    # --------------------------------------------------------
    # REQUIRED COLUMN CHECK
    # --------------------------------------------------------

    missing = [
        column
        for column in REQUIRED
        if column not in df.columns
    ]

    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))
        raise ValueError(
            "Missing columns: "
            + ", ".join(missing)
            + ". "
            "Please verify the uploaded file headers."
        )

    # --------------------------------------------------------
    # SAFE NUMERIC DEFAULTS
    # --------------------------------------------------------

    numeric_defaults = {
        "Target": 0,
        "Production": 0,
        "AHT_Actual": 0,
        "Quality_%": 0,
        "SLA_%": 0,
        "Error_Count": 0,
    }

    for column, default in numeric_defaults.items():
        df[column] = (
            pd.to_numeric(
                df[column],
                errors="coerce",
            )
            .fillna(default)
        )

    # --------------------------------------------------------
    # SAFE TEXT DEFAULTS
    # --------------------------------------------------------

    df["Employee_ID"] = (
        df["Employee_ID"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    df["Team"] = (
        df["Team"]
        .fillna("Unknown Team")
        .astype(str)
        .str.strip()
    )

    df["Attendance"] = (
        df["Attendance"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # PRODUCTIVITY
    # --------------------------------------------------------

    if "Productivity_%" not in df.columns:
        df["Productivity_%"] = (df["Production"] / df["Target"].replace(0, np.nan) * 100).fillna(0).round(1)

    team = df.groupby("Team").agg(
        Records=("Employee_ID","count"),
        Target=("Target","sum"),
        Production=("Production","sum"),
        Avg_AHT=("AHT_Actual","mean"),
        Avg_Quality=("Quality_%","mean"),
        Avg_SLA=("SLA_%","mean"),
        Absences=("Attendance", lambda s: (s.astype(str).str.lower()=="absent").sum()),
        Errors=("Error_Count","sum")
    ).reset_index()

    team["Productivity_%"] = (team["Production"] / team["Target"].replace(0,np.nan) * 100).fillna(0).round(1)
    team["Absence_%"] = (team["Absences"] / team["Records"] * 100).round(1)
    team["AHT_Gap"] = (team["Avg_AHT"] - aht_target).round(1)
    team["Avg_AHT"] = team["Avg_AHT"].round(1)
    team["Avg_Quality"] = team["Avg_Quality"].round(1)
    team["Avg_SLA"] = team["Avg_SLA"].round(1)

    employees = df.groupby(["Employee_ID","Team"]).agg(
        Avg_Productivity=("Productivity_%","mean"),
        Avg_AHT=("AHT_Actual","mean"),
        Avg_Quality=("Quality_%","mean"),
        Avg_SLA=("SLA_%","mean"),
        Absences=("Attendance", lambda s: (s.astype(str).str.lower()=="absent").sum()),
        Errors=("Error_Count","sum")
    ).reset_index()

    employees["AHT_Gap"]=(employees["Avg_AHT"]-aht_target).round(1)

        df["Productivity_%"] = _safe_percentage(
            df["Production"],
            df["Target"],
        ).round(1)

    else:

        df["Productivity_%"] = pd.to_numeric(
            df["Productivity_%"],
            errors="coerce",
        )

        calculated_productivity = _safe_percentage(
            df["Production"],
            df["Target"],
        )

        df["Productivity_%"] = (
            df["Productivity_%"]
            .fillna(calculated_productivity)
            .fillna(0)
            .round(1)
        )

    # ========================================================
    # TEAM ANALYSIS
    # ========================================================

    team = (
        df.groupby(
            "Team",
            dropna=False,
        )
        .agg(
            Records=("Employee_ID", "count"),
            Target=("Target", "sum"),
            Production=("Production", "sum"),
            Avg_AHT=("AHT_Actual", "mean"),
            Avg_Quality=("Quality_%", "mean"),
            Avg_SLA=("SLA_%", "mean"),
            Absences=(
                "Attendance",
                lambda s: (
                    s.astype(str)
                    .str.strip()
                    .str.lower()
                    .isin(
                        [
                            "absent",
                            "absence",
                            "a",
                        ]
                    )
                ).sum(),
            ),
            Errors=("Error_Count", "sum"),
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # TEAM KPI CALCULATIONS
    # --------------------------------------------------------

    team["Productivity_%"] = _safe_percentage(
        team["Production"],
        team["Target"],
    ).round(1)

    team["Absence_%"] = np.where(
        team["Records"] != 0,
        (
            team["Absences"]
            / team["Records"]
            * 100
        ),
        0,
    ).round(1)

    team["AHT_Gap"] = (
        team["Avg_AHT"]
        - aht_target
    ).round(1)

    team["Avg_AHT"] = (
        team["Avg_AHT"]
        .fillna(0)
        .round(1)
    )

    team["Avg_Quality"] = (
        team["Avg_Quality"]
        .fillna(0)
        .round(1)
    )

    team["Avg_SLA"] = (
        team["Avg_SLA"]
        .fillna(0)
        .round(1)
    )

    # ========================================================
    # EMPLOYEE ANALYSIS
    # ========================================================

    employees = (
        df.groupby(
            [
                "Employee_ID",
                "Team",
            ],
            dropna=False,
        )
        .agg(
            Avg_Productivity=(
                "Productivity_%",
                "mean",
            ),
            Avg_AHT=(
                "AHT_Actual",
                "mean",
            ),
            Avg_Quality=(
                "Quality_%",
                "mean",
            ),
            Avg_SLA=(
                "SLA_%",
                "mean",
            ),
            Absences=(
                "Attendance",
                lambda s: (
                    s.astype(str)
                    .str.strip()
                    .str.lower()
                    .isin(
                        [
                            "absent",
                            "absence",
                            "a",
                        ]
                    )
                ).sum(),
            ),
            Errors=(
                "Error_Count",
                "sum",
            ),
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # EMPLOYEE KPI CLEANING
    # --------------------------------------------------------

    employees["Avg_Productivity"] = (
        employees["Avg_Productivity"]
        .fillna(0)
        .round(1)
    )

    employees["Avg_AHT"] = (
        employees["Avg_AHT"]
        .fillna(0)
        .round(1)
    )

    employees["Avg_Quality"] = (
        employees["Avg_Quality"]
        .fillna(0)
        .round(1)
    )

    employees["Avg_SLA"] = (
        employees["Avg_SLA"]
        .fillna(0)
        .round(1)
    )

    employees["AHT_Gap"] = (
        employees["Avg_AHT"]
        - aht_target
    ).round(1)

    # ========================================================
    # EMPLOYEE RISK SCORE
    # ========================================================

    employees["Risk_Score"] = (
        (employees["Avg_Productivity"] < productivity_target).astype(int)
        + (employees["Avg_Quality"] < quality_target).astype(int)
        + (employees["Avg_SLA"] < sla_target).astype(int)
        + (employees["AHT_Gap"] > 10).astype(int)
        (
            employees["Avg_Productivity"]
            < productivity_target
        ).astype(int)

        + (
            employees["Avg_Quality"]
            < quality_target
        ).astype(int)

        + (
            employees["Avg_SLA"]
            < sla_target
        ).astype(int)

        + (
            employees["AHT_Gap"]
            > 10
        ).astype(int)
    )

    employees["Risk_Level"] = np.select(
        [employees["Risk_Score"]>=3, employees["Risk_Score"]==2, employees["Risk_Score"]==1],
        ["Critical","High","Watch"], default="Normal"
    )

    findings=[]
    actions=[]
    for _,r in team.iterrows():
        evidence=[]
        if r["Productivity_%"] < productivity_target:
            evidence.append(f"Productivity {r['Productivity_%']:.1f}% < {productivity_target}%")
        if r["Avg_Quality"] < quality_target:
            evidence.append(f"Quality {r['Avg_Quality']:.1f}% < {quality_target}%")
        if r["Avg_SLA"] < sla_target:
            evidence.append(f"SLA {r['Avg_SLA']:.1f}% < {sla_target}%")
        if r["AHT_Gap"] > 0:
            evidence.append(f"AHT {r['AHT_Gap']:.1f} above target")
        if r["Absence_%"] > 8:
            evidence.append(f"Absence {r['Absence_%']:.1f}% > 8%")
        [
            employees["Risk_Score"] >= 3,
            employees["Risk_Score"] == 2,
            employees["Risk_Score"] == 1,
        ],
        [
            "Critical",
            "High",
            "Watch",
        ],
        default="Normal",
    )

    # ========================================================
    # FINDINGS + ACTIONS
    # ========================================================

    findings = []
    actions = []

    for _, row in team.iterrows():

        evidence = []

        # Productivity
        if row["Productivity_%"] < productivity_target:
            evidence.append(
                f"Productivity "
                f"{row['Productivity_%']:.1f}% "
                f"< {productivity_target}%"
            )

        # Quality
        if row["Avg_Quality"] < quality_target:
            evidence.append(
                f"Quality "
                f"{row['Avg_Quality']:.1f}% "
                f"< {quality_target}%"
            )

        # SLA
        if row["Avg_SLA"] < sla_target:
            evidence.append(
                f"SLA "
                f"{row['Avg_SLA']:.1f}% "
                f"< {sla_target}%"
            )

        # AHT
        if row["AHT_Gap"] > 0:
            evidence.append(
                f"AHT "
                f"{row['AHT_Gap']:.1f} "
                f"above target"
            )

        # Attendance
        if row["Absence_%"] > 8:
            evidence.append(
                f"Absence "
                f"{row['Absence_%']:.1f}% "
                f"> 8%"
            )

        # ----------------------------------------------------
        # FINDING
        # ----------------------------------------------------

        if evidence:
            findings.append(["High", r["Team"], "; ".join(evidence),
                             "Evidence indicates a performance gap; causal root cause requires validation."])
            action = "Investigate workload/task mix and review targeted coaching opportunities."
            if r["AHT_Gap"] > 10:
                action = "Review high-AHT workflow and run process-efficiency coaching."
            actions.append([r["Team"], "; ".join(evidence), action,
                            "Operations Manager / Team Lead","High","Within 2 business days",
                            "Improve KPI performance without reducing quality/SLA."])

    findings=pd.DataFrame(findings, columns=["Severity","Team","Finding","Root_Cause_Position"])
    actions=pd.DataFrame(actions, columns=["Team","Issue","Recommended_Action","Owner_Role","Priority","Due","Success_Metric"])

    overall={
        "productivity": df["Production"].sum()/df["Target"].sum()*100 if df["Target"].sum() else 0,
        "quality": df["Quality_%"].mean(),
        "sla": df["SLA_%"].mean(),
        "aht": df["AHT_Actual"].mean()

            findings.append(
                [
                    "High",
                    row["Team"],
                    "; ".join(evidence),
                    (
                        "Evidence indicates a performance "
                        "gap; causal root cause requires "
                        "validation."
                    ),
                ]
            )

            # ------------------------------------------------
            # ACTION
            # ------------------------------------------------

            action = (
                "Investigate workload/task mix and review "
                "targeted coaching opportunities."
            )

            if row["AHT_Gap"] > 10:
                action = (
                    "Review high-AHT workflow and run "
                    "process-efficiency coaching."
                )

            if (
                row["Productivity_%"]
                < productivity_target
                and row["Avg_Quality"]
                >= quality_target
            ):
                action = (
                    "Review productivity blockers, workload "
                    "distribution, and process efficiency."
                )

            if row["Avg_Quality"] < quality_target:
                action = (
                    "Conduct quality root-cause analysis "
                    "and targeted quality coaching."
                )

            if row["Avg_SLA"] < sla_target:
                action = (
                    "Review SLA misses, queue management, "
                    "work allocation, and turnaround time."
                )

            actions.append(
                [
                    row["Team"],
                    "; ".join(evidence),
                    action,
                    "Operations Manager / Team Lead",
                    "High",
                    "Within 2 business days",
                    (
                        "Improve KPI performance without "
                        "reducing quality/SLA."
                    ),
                ]
            )

    # ========================================================
    # DATAFRAME OUTPUTS
    # ========================================================

    findings = pd.DataFrame(
        findings,
        columns=[
            "Severity",
            "Team",
            "Finding",
            "Root_Cause_Position",
        ],
    )

    actions = pd.DataFrame(
        actions,
        columns=[
            "Team",
            "Issue",
            "Recommended_Action",
            "Owner_Role",
            "Priority",
            "Due",
            "Success_Metric",
        ],
    )

    # ========================================================
    # OVERALL KPI
    # ========================================================

    total_target = float(
        df["Target"].sum()
    )

    total_production = float(
        df["Production"].sum()
    )

    if total_target > 0:
        overall_productivity = (
            total_production
            / total_target
            * 100
        )
    else:
        overall_productivity = 0

    overall_quality = float(
        df["Quality_%"].mean()
    )

    overall_sla = float(
        df["SLA_%"].mean()
    )

    overall_aht = float(
        df["AHT_Actual"].mean()
    )

    overall = {
        "productivity": round(
            overall_productivity,
            2,
        ),
        "quality": round(
            overall_quality,
            2,
        ),
        "sla": round(
            overall_sla,
            2,
        ),
        "aht": round(
            overall_aht,
            2,
        ),
    }
    return {"team":team,"employees":employees,"findings":findings,"actions":actions,"overall":overall}

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "team": team,
        "employees": employees,
        "findings": findings,
        "actions": actions,
        "overall": overall,
    }


# ============================================================
# AI PROMPT
# ============================================================

def make_ai_prompt(result):

    if not isinstance(result, dict):
        raise ValueError(
            "Invalid analysis result supplied to AI prompt."
        )

    payload = {
        "team_performance": result["team"].to_dict(orient="records"),
        "employee_risk": result["employees"].to_dict(orient="records"),
        "findings": result["findings"].to_dict(orient="records"),
        "actions": result["actions"].to_dict(orient="records")
        "team_performance": (
            result.get(
                "team",
                pd.DataFrame(),
            )
            .to_dict(orient="records")
        ),

        "employee_risk": (
            result.get(
                "employees",
                pd.DataFrame(),
            )
            .to_dict(orient="records")
        ),

        "findings": (
            result.get(
                "findings",
                pd.DataFrame(),
            )
            .to_dict(orient="records")
        ),

        "actions": (
            result.get(
                "actions",
                pd.DataFrame(),
            )
            .to_dict(orient="records")
        ),
    }
    return """You are an AI Operations Analyst.
Use ONLY the supplied data. Never invent facts.
Distinguish FACT from HYPOTHESIS.

    return (
        """
You are an AI Operations Analyst.

Use ONLY the supplied operational data.

Never invent facts.

Clearly distinguish FACT from HYPOTHESIS.

Do not make employment decisions or infer personal characteristics.
Return valid JSON with:
executive_summary, critical_findings, root_cause_analysis,
affected_teams, affected_employees, recommended_actions,
management_email, data_gaps.

For each root cause include problem, evidence, hypothesis, confidence, validation_needed.
For each action include issue, action, owner_role, priority, due_date, success_metric.
Analyze:
- Team performance
- Employee operational risk
- KPI gaps
- Quality
- SLA
- Productivity
- AHT
- Attendance
- Errors
- Operational findings
- Recommended actions

Return VALID JSON with exactly these top-level fields:

{
  "executive_summary": "",
  "critical_findings": [],
  "root_cause_analysis": [],
  "affected_teams": [],
  "affected_employees": [],
  "recommended_actions": [],
  "management_email": "",
  "data_gaps": []
}

For every root cause include:

{
  "problem": "",
  "evidence": "",
  "hypothesis": "",
  "confidence": "",
  "validation_needed": ""
}

For every action include:

{
  "issue": "",
  "action": "",
  "owner_role": "",
  "priority": "",
  "due_date": "",
  "success_metric": ""
}

Important rules:

1. Do not invent operational facts.
2. Do not infer personal characteristics.
3. Do not make hiring, firing, promotion, compensation,
   disciplinary, or other employment decisions.
4. Treat root causes as hypotheses unless directly supported
   by the supplied data.
5. Mention data gaps when evidence is insufficient.
6. Use concise management language.
7. Return valid JSON only.

DATA:
""" + json.dumps(payload, indent=2, default=str)

"""
        + json.dumps(
            payload,
            indent=2,
            default=str,
        )
    )
