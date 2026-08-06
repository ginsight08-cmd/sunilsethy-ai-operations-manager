
import streamlit as st
import pandas as pd
import requests

from engine import analyze_data, make_ai_prompt


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Operations Manager",
    page_icon="🤖",
    layout="wide"
)


# ============================================================
# HEADER
# ============================================================

st.title("🤖 AI Operations Manager")

st.caption(
    "Upload operational data → analyze performance → "
    "identify risks → create actions → ask AI → "
    "send management report."
)


# ============================================================
# SIDEBAR KPI SETTINGS
# ============================================================

with st.sidebar:

    st.header("⚙️ KPI Controls")

    productivity_target = st.number_input(
        "Productivity target %",
        min_value=1,
        max_value=200,
        value=90
    )

    quality_target = st.number_input(
        "Quality target %",
        min_value=1,
        max_value=100,
        value=95
    )

    sla_target = st.number_input(
        "SLA target %",
        min_value=1,
        max_value=100,
        value=97
    )

    aht_target = st.number_input(
        "AHT target",
        min_value=1,
        max_value=1000,
        value=50
    )


# ============================================================
# CUSTOMER INFORMATION
# ============================================================

st.subheader("🏢 Customer Information")

col1, col2 = st.columns(2)

with col1:

    company_name = st.text_input(
        "Company Name",
        placeholder="e.g. ABC Technologies"
    )

with col2:

    manager_email = st.text_input(
        "Manager Email",
        placeholder="manager@company.com"
    )

report_name = st.text_input(
    "Report Name",
    value="Daily Operations Report"
)


# ============================================================
# FILE UPLOAD
# ============================================================

uploaded = st.file_uploader(
    "📁 Upload Excel or CSV operational data",
    type=["xlsx", "xls", "csv"]
)


if not uploaded:

    st.warning(
        "Upload the operational data file to start the analysis."
    )

    st.markdown("### Required columns")

    st.code(
        "Date, Employee_ID, Employee_Name, Team, Target, "
        "Production, AHT_Actual, AHT_Target, Quality_%, "
        "SLA_%, Attendance, Error_Count, Error_Category"
    )

    st.stop()


# ============================================================
# SESSION STATE
# ============================================================

if "n8n_sent" not in st.session_state:
    st.session_state.n8n_sent = False

if "n8n_result" not in st.session_state:
    st.session_state.n8n_result = None

if "copilot_answer" not in st.session_state:
    st.session_state.copilot_answer = None


# ============================================================
# SEND FILE + CUSTOMER DATA TO N8N
# ============================================================

if not st.session_state.n8n_sent:

    n8n_url = st.secrets.get(
        "N8N_WEBHOOK_URL",
        ""
    )

    if n8n_url:

        if not company_name.strip():

            st.warning(
                "⚠️ Please enter the Company Name."
            )

            st.stop()

        if not manager_email.strip():

            st.warning(
                "⚠️ Please enter the Manager Email."
            )

            st.stop()

        if not report_name.strip():

            st.warning(
                "⚠️ Please enter the Report Name."
            )

            st.stop()

        try:

            uploaded.seek(0)

            file_content = uploaded.getvalue()

            files = {
                "file": (
                    uploaded.name,
                    file_content,
                    uploaded.type or "application/octet-stream"
                )
            }

            data = {
                "company_name": company_name.strip(),
                "manager_email": manager_email.strip(),
                "report_name": report_name.strip()
            }

            with st.spinner(
                "🤖 Sending data to AI Operations Manager..."
            ):

                response = requests.post(
                    n8n_url,
                    files=files,
                    data=data,
                    timeout=120
                )

            if response.status_code < 300:

                st.success(
                    "✅ AI Operations Manager workflow completed."
                )

                try:

                    n8n_result = response.json()

                except Exception:

                    n8n_result = {
                        "status": "success",
                        "message": "Workflow completed successfully.",
                        "company_name": company_name,
                        "manager_email": manager_email,
                        "report_name": report_name
                    }

                if isinstance(n8n_result, list) and len(n8n_result) > 0:
                    n8n_result = n8n_result[0]

                if not isinstance(n8n_result, dict):
                    n8n_result = {}

                st.session_state.n8n_result = n8n_result
                st.session_state.n8n_sent = True

            else:

                st.error(
                    f"❌ n8n workflow failed. "
                    f"HTTP Status: {response.status_code}"
                )

                st.code(response.text)

        except requests.exceptions.Timeout:

            st.error(
                "⏱️ n8n workflow timed out. "
                "The workflow may still be running."
            )

        except Exception as e:

            st.error(
                f"❌ Could not connect to n8n: {e}"
            )

    else:

        st.info(
            "ℹ️ n8n automation is not configured. "
            "The file will still be analyzed locally."
        )


# ============================================================
# N8N AUTOMATION RESULT
# ============================================================

if st.session_state.n8n_result:

    n8n_result = st.session_state.n8n_result

    st.divider()

    st.subheader("🤖 Automation Status")

    status_col1, status_col2, status_col3 = st.columns(3)

    with status_col1:

        st.success(
            "✅ Analysis Completed"
        )

    with status_col2:

        email_display = n8n_result.get(
            "manager_email",
            manager_email
        )

        st.info(
            f"📧 Report sent to:\n\n{email_display}"
        )

    with status_col3:

        company_display = n8n_result.get(
            "company_name",
            company_name
        )

        st.info(
            f"🏢 Company:\n\n{company_display}"
        )


# ============================================================
# READ FILE
# ============================================================

try:

    uploaded.seek(0)

    if uploaded.name.lower().endswith(".csv"):

        df = pd.read_csv(uploaded)

    else:

        xls = pd.ExcelFile(uploaded)

        sheet = (
            "Operational_Data"
            if "Operational_Data" in xls.sheet_names
            else xls.sheet_names[0]
        )

        df = pd.read_excel(
            uploaded,
            sheet_name=sheet
        )


    # ========================================================
    # ANALYSIS
    # ========================================================

    result = analyze_data(
        df,
        productivity_target=productivity_target,
        quality_target=quality_target,
        sla_target=sla_target,
        aht_target=aht_target
    )


    # ========================================================
    # GET KPI VALUES
    # ========================================================

    overall = result["overall"]

    productivity = overall["productivity"]
    quality = overall["quality"]
    sla = overall["sla"]
    aht = overall["aht"]


    # ========================================================
    # AI RISK DASHBOARD
    # ========================================================

    st.divider()

    st.subheader(
        "🎯 AI Operations Risk Dashboard"
    )


    productivity_gap = (
        productivity - productivity_target
    )

    quality_gap = (
        quality - quality_target
    )

    sla_gap = (
        sla - sla_target
    )

    aht_gap = (
        aht - aht_target
    )


    # ========================================================
    # KPI BREACH COUNT
    # ========================================================

    breaches = 0

    if productivity < productivity_target:
        breaches += 1

    if quality < quality_target:
        breaches += 1

    if sla < sla_target:
        breaches += 1

    if aht > aht_target:
        breaches += 1


    # ========================================================
    # RISK LEVEL
    # ========================================================

    if breaches >= 3:

        dashboard_risk = "🔴 HIGH"

    elif breaches >= 1:

        dashboard_risk = "🟠 MEDIUM"

    else:

        dashboard_risk = "🟢 LOW"


    # ========================================================
    # ACTION COUNTS
    # ========================================================

    actions_df = result.get(
        "actions",
        pd.DataFrame()
    )

    if isinstance(actions_df, pd.DataFrame):

        action_count = len(actions_df)

    else:

        action_count = 0


    high_priority_count = 0

    if (
        isinstance(actions_df, pd.DataFrame)
        and not actions_df.empty
    ):

        priority_column = None

        for possible_column in [
            "Priority",
            "priority",
            "Priority_Level",
            "priority_level"
        ]:

            if possible_column in actions_df.columns:

                priority_column = possible_column
                break

        if priority_column:

            high_priority_count = len(
                actions_df[
                    actions_df[priority_column]
                    .astype(str)
                    .str.lower()
                    .isin(
                        [
                            "high",
                            "critical"
                        ]
                    )
                ]
            )


    # ========================================================
    # RISK CARDS
    # ========================================================

    r1, r2, r3, r4 = st.columns(4)

    with r1:

        st.metric(
            "Overall Risk",
            dashboard_risk
        )

    with r2:

        st.metric(
            "KPI Breaches",
            breaches,
            delta=f"{4 - breaches} KPIs on target"
        )

    with r3:

        st.metric(
            "Action Items",
            action_count
        )

    with r4:

        st.metric(
            "High Priority Actions",
            high_priority_count
        )


    # ========================================================
    # KPI PERFORMANCE
    # ========================================================

    st.subheader(
        "📊 KPI Performance vs Target"
    )

    k1, k2, k3, k4 = st.columns(4)

    with k1:

        st.metric(
            "Productivity",
            f"{productivity:.2f}%",
            delta=f"{productivity_gap:+.2f}% vs target"
        )

    with k2:

        st.metric(
            "Quality",
            f"{quality:.2f}%",
            delta=f"{quality_gap:+.2f}% vs target"
        )

    with k3:

        st.metric(
            "SLA",
            f"{sla:.2f}%",
            delta=f"{sla_gap:+.2f}% vs target"
        )

    with k4:

        st.metric(
            "Average AHT",
            f"{aht:.2f}",
            delta=f"{aht_gap:+.2f} vs target"
        )


    # ========================================================
    # AI EXECUTIVE SUMMARY
    # ========================================================

    st.divider()

    st.subheader(
        "🧠 AI Executive Summary"
    )

    summary_points = []


    if productivity < productivity_target:

        summary_points.append(
            f"🔴 Productivity is below target "
            f"({productivity:.1f}% vs {productivity_target}%)."
        )

    else:

        summary_points.append(
            f"🟢 Productivity is above target "
            f"({productivity:.1f}% vs {productivity_target}%)."
        )


    if quality < quality_target:

        summary_points.append(
            f"🔴 Quality is below target "
            f"({quality:.1f}% vs {quality_target}%)."
        )

    else:

        summary_points.append(
            f"🟢 Quality is meeting target "
            f"({quality:.1f}% vs {quality_target}%)."
        )


    if sla < sla_target:

        summary_points.append(
            f"🔴 SLA is below target "
            f"({sla:.1f}% vs {sla_target}%)."
        )

    else:

        summary_points.append(
            f"🟢 SLA is meeting target "
            f"({sla:.1f}% vs {sla_target}%)."
        )


    if aht > aht_target:

        summary_points.append(
            f"🟠 AHT is above target "
            f"({aht:.1f} vs {aht_target})."
        )

    else:

        summary_points.append(
            f"🟢 AHT is within target "
            f"({aht:.1f} vs {aht_target})."
        )


    # Risk level

    risk_count = breaches

    if risk_count == 0:

        risk_level = "🟢 LOW RISK"

    elif risk_count == 1:

        risk_level = "🟡 MEDIUM RISK"

    elif risk_count == 2:

        risk_level = "🟠 HIGH RISK"

    else:

        risk_level = "🔴 CRITICAL RISK"


    st.metric(
        "Operational Risk Level",
        risk_level
    )


    for point in summary_points:

        st.write(point)


    # ========================================================
    # MANAGEMENT RECOMMENDATION
    # ========================================================

    if risk_count == 0:

        recommendation = (
            "Operations are currently performing within "
            "defined KPI thresholds. Continue monitoring "
            "performance and maintain current processes."
        )

    elif risk_count <= 2:

        recommendation = (
            "Management should review the affected KPIs, "
            "identify contributing operational factors, "
            "and initiate targeted corrective actions."
        )

    else:

        recommendation = (
            "Immediate management attention is recommended. "
            "Multiple KPI thresholds are currently breached. "
            "Prioritize root-cause analysis and corrective actions."
        )


    st.info(
        f"💡 **Management Recommendation:** {recommendation}"
    )


    # ========================================================
    # MANAGEMENT COPILOT
    # ========================================================

    st.divider()

    st.subheader(
        "🤖 Management Copilot"
    )

    st.caption(
        "Ask questions about your operational data "
        "and receive an AI-generated management response."
    )


    question = st.text_input(
        "Ask your operational question",
        placeholder=(
            "Example: Why is Quality below target?"
        ),
        key="copilot_question"
    )


    ask_copilot = st.button(
        "🚀 Ask Management Copilot",
        type="primary"
    )


    # ========================================================
    # CALL N8N COPILOT
    # ========================================================

    if ask_copilot and question.strip():

        copilot_url = st.secrets.get(
            "N8N_COPILOT_WEBHOOK_URL",
            ""
        )


        if not copilot_url:

            st.error(
                "❌ N8N_COPILOT_WEBHOOK_URL is not configured "
                "in Streamlit secrets."
            )

        else:

            findings_text = result["findings"].to_string(
                index=False
            )

            actions_text = result["actions"].to_string(
                index=False
            )


            # ------------------------------------------------
            # BUILD COPILOT CONTEXT
            # ------------------------------------------------

            copilot_context = f"""
Company:
{company_name}

Report:
{report_name}

Operational KPIs:

Productivity:
{productivity:.2f}% | Target: {productivity_target}%

Quality:
{quality:.2f}% | Target: {quality_target}%

SLA:
{sla:.2f}% | Target: {sla_target}%

Average AHT:
{aht:.2f} | Target: {aht_target}

Overall Risk:
{risk_level}

Operational Findings:
{findings_text}

Recommended Actions:
{actions_text}

KPI Summary:
{chr(10).join(summary_points)}
"""


            # ------------------------------------------------
            # JSON PAYLOAD
            # ------------------------------------------------

            copilot_payload = {

                "question": question.strip(),

                "company_name": company_name.strip(),

                "report_name": report_name.strip(),

                "context": copilot_context

            }


            # ------------------------------------------------
            # SEND TO N8N
            # ------------------------------------------------

            try:

                with st.spinner(
                    "🤖 Management Copilot is analyzing your question..."
                ):

                    copilot_response = requests.post(

                        copilot_url,

                        json=copilot_payload,

                        timeout=120

                    )


                # ------------------------------------------------
                # SUCCESS
                # ------------------------------------------------

                if copilot_response.status_code < 300:

                    try:

                        copilot_result = (
                            copilot_response.json()
                        )

                    except Exception:

                        copilot_result = {
                            "answer":
                                copilot_response.text
                        }


                    # n8n can return list

                    if (
                        isinstance(copilot_result, list)
                        and len(copilot_result) > 0
                    ):

                        copilot_result = copilot_result[0]


                    # ------------------------------------------------
                    # EXTRACT ANSWER
                    # ------------------------------------------------

                    if isinstance(copilot_result, dict):

                        copilot_answer = (

                            copilot_result.get("answer")

                            or copilot_result.get("response")

                            or copilot_result.get("output")

                            or copilot_result.get("text")

                            or copilot_result.get("message")

                        )

                    else:

                        copilot_answer = str(
                            copilot_result
                        )


                    if not copilot_answer:

                        copilot_answer = (
                            "The AI workflow completed, "
                            "but no answer field was returned."
                        )


                    st.session_state.copilot_answer = (
                        copilot_answer
                    )


                else:

                    st.error(
                        f"❌ Copilot workflow failed. "
                        f"HTTP Status: "
                        f"{copilot_response.status_code}"
                    )

                    st.code(
                        copilot_response.text
                    )


            except requests.exceptions.Timeout:

                st.error(
                    "⏱️ Management Copilot timed out. "
                    "Please try again."
                )


            except Exception as e:

                st.error(
                    f"❌ Could not connect to Management Copilot: {e}"
                )


    elif ask_copilot and not question.strip():

        st.warning(
            "⚠️ Please enter a question first."
        )


    # ========================================================
    # DISPLAY COPILOT ANSWER
    # ========================================================

    if st.session_state.copilot_answer:

        st.markdown(
            "### 🧠 Copilot Analysis"
        )

        st.success(
            "✅ AI response received from n8n."
        )

        st.markdown(
            st.session_state.copilot_answer
        )


    # ========================================================
    # CUSTOMER / REPORT INFORMATION
    # ========================================================

    if (
        company_name
        or manager_email
        or report_name
    ):

        with st.expander(
            "🏢 Report Information",
            expanded=False
        ):

            info1, info2, info3 = st.columns(3)

            with info1:

                st.write("**Company**")
                st.write(company_name)

            with info2:

                st.write("**Manager Email**")
                st.write(manager_email)

            with info3:

                st.write("**Report**")
                st.write(report_name)


    # ========================================================
    # TABS
    # ========================================================

    st.divider()

    tabs = st.tabs([
        "📊 Dashboard",
        "🚨 AI Insights",
        "👥 Employee Risk",
        "✅ Action Center",
        "🧠 AI Prompt",
        "📥 Export"
    ])


    # ========================================================
    # DASHBOARD
    # ========================================================

    with tabs[0]:

        st.subheader(
            "Team Performance"
        )

        st.dataframe(
            result["team"],
            use_container_width=True
        )

        if not result["team"].empty:

            st.subheader(
                "Productivity by Team"
            )

            st.bar_chart(
                result["team"].set_index(
                    "Team"
                )["Productivity_%"]
            )


    # ========================================================
    # AI INSIGHTS
    # ========================================================

    with tabs[1]:

        st.subheader(
            "🚨 Automated Findings"
        )

        if result["findings"].empty:

            st.success(
                "✅ No threshold breaches detected."
            )

        else:

            st.dataframe(
                result["findings"],
                use_container_width=True
            )

        st.info(
            "Root causes are evidence-based hypotheses. "
            "The available data may not prove causality."
        )


    # ========================================================
    # EMPLOYEE RISK
    # ========================================================

    with tabs[2]:

        st.subheader(
            "👥 Employee Risk"
        )

        employee_data = result[
            "employees"
        ].sort_values(
            [
                "Risk_Score",
                "Avg_Productivity"
            ],
            ascending=[
                False,
                True
            ]
        )

        st.dataframe(
            employee_data,
            use_container_width=True
        )


    # ========================================================
    # ACTION CENTER
    # ========================================================

    with tabs[3]:

        st.subheader(
            "✅ Recommended Actions"
        )

        st.dataframe(
            result["actions"],
            use_container_width=True
        )


    # ========================================================
    # AI PROMPT
    # ========================================================

    with tabs[4]:

        st.subheader(
            "🧠 AI Analyst Prompt"
        )

        st.code(
            make_ai_prompt(result),
            language="text"
        )

        st.caption(
            "This prompt is sent automatically "
            "to the AI Operations Manager workflow."
        )


    # ========================================================
    # EXPORT
    # ========================================================

    with tabs[5]:

        st.subheader(
            "📥 Download Analysis"
        )

        st.download_button(
            "⬇️ Download Team Analysis CSV",

            result["team"]
            .to_csv(index=False)
            .encode("utf-8"),

            "team_analysis.csv",

            "text/csv"
        )

        st.download_button(
            "⬇️ Download Action Plan CSV",

            result["actions"]
            .to_csv(index=False)
            .encode("utf-8"),

            "action_plan.csv",

            "text/csv"
        )


# ============================================================
# ERROR HANDLING
# ============================================================

except Exception as e:

    st.error(
        f"❌ Could not process the file: {e}"
    )

