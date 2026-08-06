
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
    "identify risks → create actions → send management report."
)


# ============================================================
# SIDEBAR SETTINGS
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


# ============================================================
# SEND FILE + CUSTOMER DATA TO N8N
# ============================================================

if not st.session_state.n8n_sent:

    n8n_url = st.secrets.get(
        "N8N_WEBHOOK_URL",
        ""
    )

    if n8n_url:

        # -----------------------------
        # VALIDATE CUSTOMER DETAILS
        # -----------------------------

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

            # -----------------------------
            # PREPARE FILE
            # -----------------------------

            uploaded.seek(0)

            file_content = uploaded.getvalue()

            files = {
                "file": (
                    uploaded.name,
                    file_content,
                    uploaded.type or "application/octet-stream"
                )
            }


            # -----------------------------
            # CUSTOMER DATA
            # -----------------------------

            data = {

                "company_name":
                    company_name.strip(),

                "manager_email":
                    manager_email.strip(),

                "report_name":
                    report_name.strip()
            }


            # -----------------------------
            # SEND TO N8N
            # -----------------------------

            with st.spinner(
                "🤖 Sending data to AI Operations Manager..."
            ):

                response = requests.post(

                    n8n_url,

                    files=files,

                    data=data,

                    timeout=120
                )


            # -----------------------------
            # SUCCESS
            # -----------------------------

            if response.status_code < 300:

                st.success(
                    "✅ AI Operations Manager workflow completed."
                )


                # -----------------------------
                # READ N8N RESPONSE
                # -----------------------------

                try:

                    n8n_result = response.json()

                except Exception:

                    n8n_result = {

                        "status": "success",

                        "message":
                            "Workflow completed successfully.",

                        "company_name":
                            company_name,

                        "manager_email":
                            manager_email,

                        "report_name":
                            report_name
                    }


                st.session_state.n8n_result = n8n_result

                st.session_state.n8n_sent = True


            # -----------------------------
            # ERROR
            # -----------------------------

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
                "⏱️ n8n workflow timed out. "
                "The analysis may still be running."
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

    st.subheader(
        "🤖 Automation Status"
    )


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
            f"📧 Report sent to:\n\n"
            f"{email_display}"
        )


    with status_col3:

        company_display = n8n_result.get(
            "company_name",
            company_name
        )

        st.info(
            f"🏢 Company:\n\n"
            f"{company_display}"
        )


# ============================================================
# READ FILE
# ============================================================

try:

    uploaded.seek(0)


    if uploaded.name.lower().endswith(".csv"):

        df = pd.read_csv(
            uploaded
        )


    else:

        xls = pd.ExcelFile(
            uploaded
        )


        sheet = (

            "Operational_Data"

            if "Operational_Data"
            in xls.sheet_names

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

        productivity_target=
            productivity_target,

        quality_target=
            quality_target,

        sla_target=
            sla_target,

        aht_target=
            aht_target
    )


    # ========================================================
    # KPI CARDS
    # ========================================================

    st.divider()

    st.subheader(
        "📊 Operational KPI Dashboard"
    )


    k1, k2, k3, k4 = st.columns(4)


    with k1:

        st.metric(

            "Productivity",

            f"{result['overall']['productivity']:.1f}%",

            delta=f"Target {productivity_target}%"
        )


    with k2:

        st.metric(

            "Quality",

            f"{result['overall']['quality']:.1f}%",

            delta=f"Target {quality_target}%"
        )


    with k3:

        st.metric(

            "SLA",

            f"{result['overall']['sla']:.1f}%",

            delta=f"Target {sla_target}%"
        )


    with k4:

        st.metric(

            "Average AHT",

            f"{result['overall']['aht']:.1f}",

            delta=f"Target {aht_target}"
        )


    st.divider()


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

            result[
                "team"
            ].to_csv(
                index=False
            ).encode("utf-8"),

            "team_analysis.csv",

            "text/csv"
        )


        st.download_button(

            "⬇️ Download Action Plan CSV",

            result[
                "actions"
            ].to_csv(
                index=False
            ).encode("utf-8"),

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

