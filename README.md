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

## n8n configuration

Add these values to local `.streamlit/secrets.toml` or to the deployed app's
Streamlit Secrets. Copy the production URLs directly from active n8n Webhook
nodes:

```toml
N8N_WEBHOOK_URL = "https://YOUR-N8N-HOST/webhook/operations-upload"
N8N_COPILOT_WEBHOOK_URL = "https://YOUR-N8N-HOST/webhook/management-copilot"
```

Do not use an n8n editor/workspace URL. Test URLs containing `/webhook-test/`
only work temporarily while the editor is listening for a test event.

## Vakil case management setup

The **Vakil / Legal Case Management** industry stores each signed-in user's
clients and cases in Supabase so they remain available after logout, restart,
or deployment. Before using it online:

1. Open the Supabase project used by this Streamlit app.
2. Open **SQL Editor**.
3. Run the complete `supabase_vakil_schema.sql` script once.
4. Confirm `SUPABASE_URL` and `SUPABASE_ANON_KEY` are present in Streamlit
   Secrets, then redeploy the app.

The SQL enables row-level security. Authenticated users can select, create,
update, and delete only records whose `user_id` matches their own login.

### WhatsApp and email case alerts

The Vakil module includes a Notifications tab for tracked WhatsApp and email
updates. Add `N8N_VAKIL_NOTIFICATION_WEBHOOK_URL` to Streamlit Secrets and
configure the n8n delivery workflow described in
`N8N_VAKIL_NOTIFICATION_SETUP.md`. A second scheduled n8n workflow can send
automatic reminders even when the Streamlit app is closed.

## Input

Upload an Excel file containing an `Operational_Data` sheet, or a CSV.

Required fields:
Employee_ID, Team, Target, Production, AHT_Actual, Quality_%, SLA_%, Attendance, Error_Count

Optional:
Date, Employee_Name, AHT_Target, Error_Category

## Case Management module

Select **Case Management / Service Operations** from the Industry menu. The
module supports case creation, assignment, status and priority changes, SLA
tracking, configurable due-soon and stale-case thresholds, risk-based work
queues, workload charts, field-level change history, and Excel/CSV exports.

Required case-register columns:

```text
Case_ID, Created_At, Status, Priority, Owner, Category, SLA_Due_At
```

Optional columns:

```text
Customer, Description, Last_Updated_At, Resolution_At, Resolution_Notes
```

Use the downloadable workbook inside the module as the canonical template.
Dates and times are interpreted as UTC. Supported standard statuses are New,
Assigned, In Progress, Pending, Resolved, Closed, and Cancelled.

## Product roadmap

Step 6: Working web MVP
Step 7: Connect approved LLM/API and parse structured JSON
Step 8: Authentication + multi-company database
Step 9: Automated email/Teams/n8n workflows
Step 10: Billing, tenant isolation, audit logs and enterprise security

## Safety / governance

Use employee IDs or anonymized identifiers for external AI calls. Do not send unnecessary PII. AI findings are decision support, not automatic employment decisions.
