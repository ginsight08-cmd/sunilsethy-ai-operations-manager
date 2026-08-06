
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
    "identify risks → create actions → notify management."
)


# ============================================================
# SESSION STATE
# ============================================================

if "n8n_sent" not in st.session_state:
    st.session_state.n8n_sent = False

if "n8n_result" not in st.session_state:
    st.session_state.n8n_result = None


# ============================================================
# SIDEBAR - KPI TARGETS
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

    st.info(
        "Upload your operational data to start the AI analysis."
    )

    st.markdown("### Required columns")

    st.code(
        "Date, Employee_ID, Employee_Name, Team, Target, "
        "Production, AHT_Actual, AHT_Target, Quality_%, "
        "SLA_%, Attendance, Error_Count, Error_Category"
    )

    st.stop()


# ============================================================
# SEND FILE + CUSTOMER DATA TO N8N
# ============================================================

if not st.session_state.n8n_sent:

    n8n_url = st.secrets.get(
        "N8N_WEBHOOK_URL",
        ""
    )

    if n8n_url:

        # ----------------------------------------
        # Validate customer information
        # ----------------------------------------

        if not company_name.strip():

            st.warning(
                "⚠️ Please enter the Company Name."
            )

        elif not manager_email.strip():

            st.warning(
                "⚠️ Please enter the Manager Email."
            )

        else:

            try:

                uploaded.seek(0)

                # ----------------------------------------
                # FILE
                # ----------------------------------------

                files = {
                    "file": (
                        uploaded.name,
                        uploaded.getvalue(),
                        uploaded.type or "application/octet-stream"
                    )
                }

                # ----------------------------------------
                # CUSTOMER DATA
                # ----------------------------------------

                data = {
                    "company_name": company_name.strip(),
                    "manager_email": manager_email.strip(),
                    "report_name": report_name.strip()
                }

                # ----------------------------------------
                # SEND TO N8N
                # ----------------------------------------

                with st.spinner(
                    "🤖 AI Operations Manager is analyzing your data..."
                ):

                    response = requests.post(
                        n8n_url,
                        files=files,
                        data=data,
                        timeout=120
                    )

                # ----------------------------------------
                # SUCCESS
                # ----------------------------------------

                if response.status_code < 300:

                    st.session_state.n8n_sent = True

                    try:

                        n8n_result = response.json()

                        st.session_state.n8n_result = n8n_result

                    except Exception:

                        st.session_state.n8n_result = {
                            "status": "success",
                            "message": (
                                "AI Operations Manager "
                                "completed successfully."
                            )
                        }

                    st.success(
                        "✅ AI Operations Manager completed successfully!"
                    )

                # ----------------------------------------
                # ERROR
                # ----------------------------------------

                else:

                    st.error(
                        f"❌ n8n workflow failed. "
                        f"HTTP Status: {response.status_code}"
                    )

                    st.code(
                        response.text
                    )

            except requests.exceptions.Timeout:

                st.error(
                    "⏱️ n8n took too long to respond. "
                    "Please check the workflow execution."
                )

            except Exception as e:

                st.error(
                    f"❌ Could not connect to n8n: {e}"
                )

    else:

        st.warning(
            "⚠️ n8n automation is not configured. "
            "The file will still be analyzed locally."
        )


# ============================================================
# N8N RESULT DASHBOARD
# ============================================================

if st.session_state.n8n_result:

    n8n_result = st.session_state.n8n_result

    st.divider()

    st.subheader(
        "🤖 AI Operations Manager — Automation Result"
    )

    # ----------------------------------------
    # STATUS
    # ----------------------------------------

    if n8n_result.get("status") == "success":

        st.success(
            "✅ Operational analysis completed "
            "and management report sent."
        )

    else:

        st.warning(
            n8n_result.get(
                "message",
                "Workflow completed."
            )
        )

    # ----------------------------------------
    # CUSTOMER DETAILS
    # ----------------------------------------

    displayed_company = n8n_result.get(
        "company_name",
        company_name
    )

    displayed_email = n8n_result.get(
        "manager_email",
        manager_email
    )

    displayed_report = n8n_result.get(
        "report_name",
        report_name
    )

    info1, info2, info3 = st.columns(3)

    with info1:

        st.markdown(
            f"**🏢 Company**  \n{displayed_company}"
        )

    with info2:

        st.markdown(
            f"**📧 Report Sent To**  \n{displayed_email}"
        )

    with info3:

        st.markdown(
            f"**📄 Report**  \n{displayed_report}"
        )

    st.divider()

    # ----------------------------------------
    # KPI RESULT
    # ----------------------------------------

    st.subheader("📊 Latest AI Analysis")

    k1, k2, k3, k4 = st.columns(4)

    productivity = n8n_result.get(
        "productivity",
        "N/A"
    )

    quality = n8n_result.get(
        "quality",
        "N/A"
    )

    sla = n8n_result.get(
        "sla",
        "N/A"
    )

    aht = n8n_result.get(
        "average_aht",
        "N/A"
    )

    with k1:

        st.metric(
            "Productivity",
            f"{productivity}%"
        )

    with k2:

        st.metric(
            "Quality",
            f"{quality}%"
        )

    with k3:

        st.metric(
            "SLA",
            f"{sla}%"
        )

    with k4:

        st.metric(
            "Average AHT",
            aht
        )

    # ----------------------------------------
    # SECONDARY METRICS
    # ----------------------------------------

    st.divider()

    m1, m2, m3 = st.columns(3)

    with m1:

        st.metric(
            "🚨 Total Errors",
            n8n_result.get(
                "total_errors",
                "N/A"
            )
        )

    with m2:

        st.metric(
            "📋 Action Items",
            n8n_result.get(
                "action_items",
                "N/A"
            )
        )

    with m3:

        email_status = (
            "✅ Sent"
            if n8n_result.get(
                "email_sent",
                False
            )
            else "Not confirmed"
        )

        st.metric(
            "📧 Email Status",
            email_status
        )


# ============================================================
# READ FILE
# ============================================================

try:

    if uploaded.name.lower().endswith(".csv"):

        uploaded.seek(0)

        df = pd.read_csv(
            uploaded
        )

    else:

        uploaded.seek(0)

        xls = pd.ExcelFile(
            uploaded
        )

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
    # LOCAL ANALYSIS
    # ========================================================

    result = analyze_data(
        df,
        productivity_target=productivity_target,
        quality_target=quality_target,
        sla_target=sla_target,
        aht_target=aht_target
    )


    # ========================================================
    # LOCAL KPI CARDS
    # ========================================================

    st.divider()

    st.subheader(
        "📈 Detailed Operational Analysis"
    )

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "Productivity",
        f"{result['overall']['productivity']:.1f}%"
    )

    k2.metric(
        "Quality",
        f"{result['overall']['quality']:.1f}%"
    )

    k3.metric(
        "SLA",
        f"{result['overall']['sla']:.1f}%"
    )

    k4.metric(
        "AHT",
        f"{result['overall']['aht']:.1f}"
    )


    # ========================================================
    # TABS
    # ========================================================

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

        st.subheader(
            "Productivity by Team"
        )

        st.bar_chart(
            result["team"].set_index(
                "Team"
            )[
                "Productivity_%"
            ]
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

        st.dataframe(
            result["employees"].sort_values(
                [
                    "Risk_Score",
                    "Avg_Productivity"
                ],
                ascending=[
                    False,
                    True
                ]
            ),
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
            "This prompt can be sent automatically "
            "to the selected AI provider."
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


except Exception as e:

    st.error(
        f"❌ Could not process the file: {e}"
    )

