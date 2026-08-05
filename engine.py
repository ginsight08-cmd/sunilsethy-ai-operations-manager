
import pandas as pd
import numpy as np
import json

REQUIRED = [
    "Employee_ID","Team","Target","Production","AHT_Actual",
    "Quality_%","SLA_%","Attendance","Error_Count"
]

def analyze_data(df, productivity_target=90, quality_target=95, sla_target=97, aht_target=50):
    df = df.copy()
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))

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
    employees["Risk_Score"] = (
        (employees["Avg_Productivity"] < productivity_target).astype(int)
        + (employees["Avg_Quality"] < quality_target).astype(int)
        + (employees["Avg_SLA"] < sla_target).astype(int)
        + (employees["AHT_Gap"] > 10).astype(int)
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
    }
    return {"team":team,"employees":employees,"findings":findings,"actions":actions,"overall":overall}

def make_ai_prompt(result):
    payload = {
        "team_performance": result["team"].to_dict(orient="records"),
        "employee_risk": result["employees"].to_dict(orient="records"),
        "findings": result["findings"].to_dict(orient="records"),
        "actions": result["actions"].to_dict(orient="records")
    }
    return """You are an AI Operations Analyst.
Use ONLY the supplied data. Never invent facts.
Distinguish FACT from HYPOTHESIS.
Do not make employment decisions or infer personal characteristics.
Return valid JSON with:
executive_summary, critical_findings, root_cause_analysis,
affected_teams, affected_employees, recommended_actions,
management_email, data_gaps.

For each root cause include problem, evidence, hypothesis, confidence, validation_needed.
For each action include issue, action, owner_role, priority, due_date, success_metric.

DATA:
""" + json.dumps(payload, indent=2, default=str)
