# AI Operations Manager — MVP

A Streamlit prototype that converts operational Excel/CSV data into KPI analysis, risk detection, evidence-based findings, recommended actions, and an AI-ready prompt.

## Run locally

1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Create a virtual environment:
   `python -m venv .venv`
4. Activate it.
5. Install:
   `pip install -r requirements.txt`
6. Start:
   `streamlit run app.py`

## Input

Upload an Excel file containing an `Operational_Data` sheet, or a CSV.

Required fields:
Employee_ID, Team, Target, Production, AHT_Actual, Quality_%, SLA_%, Attendance, Error_Count

Optional:
Date, Employee_Name, AHT_Target, Error_Category

## Product roadmap

Step 6: Working web MVP
Step 7: Connect approved LLM/API and parse structured JSON
Step 8: Authentication + multi-company database
Step 9: Automated email/Teams/n8n workflows
Step 10: Billing, tenant isolation, audit logs and enterprise security

## Safety / governance

Use employee IDs or anonymized identifiers for external AI calls. Do not send unnecessary PII. AI findings are decision support, not automatic employment decisions.
