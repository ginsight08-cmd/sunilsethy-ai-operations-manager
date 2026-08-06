import streamlit as st
import pandas as pd
import requests

from engine import analyze_data, make_ai_prompt


# ============================================================
# PAGE CONFIGURATION
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
# SETTINGS
# ============================================================

with st.sidebar:

    st.header("⚙️ KPI Controls")

    productivity_target = st.number_input(
        "Productivity Target %",
        min_value=1,
        max_value=200,
        value=90
    )

    quality_target = st.number_input(
        "Quality Target %",
        min_value=1,
        max_value=100,
        value=95
    )

    sla_target = st.number_input(
        "SLA Target %",
        min_value=1,
        max_value=100,
        value=97
    )

    aht_target = st.number_input(
        "AHT Target",
        min_value=1,
        max_value=1000,
        value=50
    )

    st.divider()

    st.caption("AI Operations Manager")
    st.caption("Automated KPI & Risk Intelligence")


# ============================================================
# CUSTOMER INFORMATION
# ============================================================

st.subheader("🏢 Customer Information")

col1, col2, col3 = st.columns(3)

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

with col3:
    report_name = st.text_input(
        "Report Name",
        value="Daily Operations Report"
    )


# ============================================================
# FILE UPLOAD
# ============================================================

st.subheader("📁 Upload Operational Data")

uploaded = st.file_uploader(
    "Upload Excel or CSV operational data",
    type=["xlsx", "xls", "csv"]
)


if not uploaded:

    st.warning(
        "Upload the operational data file to begin analysis."
    )

    st.markdown("### Required columns")

    st.code(
        "Date, Employee_ID, Employee_Name, Team, Target, "
        "Production, AHT_Actual, AHT_Target, Quality_%, "
        "SLA_%, Attendance, Error_Count, Error_Category"
    )

    st.stop()


# ============================================================
# SEND FILE + CUSTOMER DETAILS TO N8N
# ============================================================

if "n8n_sent" not in st.session_state:
    st.session_state.n8n_sent = False


if not st.session_state.n8n_sent:

    n8n_url = st.secrets.get(
        "N8N_WEBHOOK_URL",
        ""
    )

    if n8n_url:

        try:

            # Validate company name

            if not company_name.strip():

                st.warning(
                    "Please enter the Company Name."
                )

                st.stop()


            # Validate manager email

            if not manager_email.strip():

                st.warning(
                    "Please enter the Manager Email."
                )

                st.stop()


            # Reset file pointer

            uploaded.seek(0)


            # File

            files = {
                "file": (
                    uploaded.name,
                    uploaded.getvalue(),
                    uploaded.type or "application/octet-stream"
                )
            }


            # Customer information

            data = {
                "company_name": company_name.strip(),
                "manager_email": manager_email.strip(),
                "report_name": report_name.strip()
            }


            # Send to n8n

            response = requests.post(
                n8n_url,
                files=files,
                data=data,
                timeout=60
            )


            if response.status_code < 300:

                st.success(
                    "✅ File and customer details sent to n8n."
                )

                st.session_state.n8n_sent = True

            else:

                st.warning(
                    f"n8n returned status "
                    f"{response.status_code}."
                )


        except Exception as e:

            st.warning(
                f"Could not connect to n8n: {e}"
            )

    else:

        st.info(
            "n8n automation is not configured. "
            "The file will still be analyzed locally."
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
    # KPI VALUES
    # ========================================================

    productivity = result["overall"]["productivity"]

    quality = result["overall"]["quality"]

    sla = result["overall"]["sla"]

    aht = result["overall"]["aht"]


    # ========================================================
    # KPI STATUS FUNCTION
    # ========================================================

    def kpi_status(
        actual,
        target,
        higher_is_better=True
    ):

        if higher_is_better:

            if actual >= target:
                return "🟢 On Target"

            elif actual >= target * 0.98:
                return "🟡 Watch"

            else:
                return "🔴 Critical"

        else:

            if actual <= target:
                return "🟢 On Target"

            elif actual <= target * 1.05:
                return "🟡 Watch"

            else:
                return "🔴 Critical"


    # ========================================================
    # KPI STATUS
    # ========================================================

    productivity_status = kpi_status(
        productivity,
        productivity_target,
        True
    )

    quality_status = kpi_status(
        quality,
        quality_target,
        True
    )

    sla_status = kpi_status(
        sla,
        sla_target,
        True
    )

    aht_status = kpi_status(
        aht,
        aht_target,
        False
    )


    # ========================================================
    # KPI DASHBOARD
    # ========================================================

    st.divider()

    st.subheader("📊 KPI Health Dashboard")

    k1, k2, k3, k4 = st.columns(4)


    with k1:

        st.metric(
            "Productivity",
            f"{productivity:.2f}%",
            f"{productivity - productivity_target:+.2f}%"
        )

        st.caption(
            productivity_status
        )


    with k2:

        st.metric(
            "Quality",
            f"{quality:.2f}%",
            f"{quality - quality_target:+.2f}%"
        )

        st.caption(
            quality_status
        )


    with k3:

        st.metric(
            "SLA",
            f"{sla:.2f}%",
            f"{sla - sla_target:+.2f}%"
        )

        st.caption(
            sla_status
        )


    with k4:

        st.metric(
            "Average AHT",
            f"{aht:.2f}",
            f"{aht - aht_target:+.2f}"
        )

        st.caption(
            aht_status
        )


    # ========================================================
    # OVERALL RISK
    # ========================================================

    critical_count = 0
    watch_count = 0


    statuses = [
        productivity_status,
        quality_status,
        sla_status,
        aht_status
    ]


    for status in statuses:

        if "Critical" in status:
            critical_count += 1

        elif "Watch" in status:
            watch_count += 1


    if critical_count >= 2:

        overall_risk = "🔴 HIGH"

    elif critical_count == 1 or watch_count >= 2:

        overall_risk = "🟡 MEDIUM"

    else:

        overall_risk = "🟢 LOW"


    st.divider()

    risk_col1, risk_col2, risk_col3 = st.columns(
        [1, 2, 1]
    )


    with risk_col2:

        st.metric(
            "🤖 Overall Operational Risk",
            overall_risk
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

        st.subheader("Team Performance")

        st.dataframe(
            result["team"],
            use_container_width=True
        )


        st.subheader("📈 Productivity by Team")

        st.bar_chart(
            result["team"].set_index("Team")[
                "Productivity_%"
            ]
        )


        # ----------------------------------------------------
        # KPI TARGET COMPARISON
        # ----------------------------------------------------

        st.subheader("🎯 KPI vs Target")


        comparison = pd.DataFrame({

            "Actual": [
                productivity,
                quality,
                sla,
                aht
            ],

            "Target": [
                productivity_target,
                quality_target,
                sla_target,
                aht_target
            ]

        }, index=[
            "Productivity %",
            "Quality %",
            "SLA %",
            "Average AHT"
        ])


        st.bar_chart(
            comparison
        )


    # ========================================================
    # AI INSIGHTS
    # ========================================================

    with tabs[1]:

        st.subheader("🚨 Automated Findings")


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

        st.subheader("👥 Employee Risk")


        employee_data = result["employees"].sort_values(
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

        st.subheader("✅ Recommended Actions")


        st.dataframe(
            result["actions"],
            use_container_width=True
        )


    # ========================================================
    # AI PROMPT
    # ========================================================

    with tabs[4]:

        st.subheader("🧠 AI Analyst Prompt")


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

        st.subheader("📥 Download Analysis")


        st.download_button(
            "Download Team Analysis CSV",
            result["team"]
            .to_csv(index=False)
            .encode("utf-8"),
            "team_analysis.csv",
            "text/csv"
        )


        st.download_button(
            "Download Action Plan CSV",
            result["actions"]
            .to_csv(index=False)
            .encode("utf-8"),
            "action_plan.csv",
            "text/csv"
        )


        # ----------------------------------------------------
        # DOWNLOAD RAW DATA
        # ----------------------------------------------------

        st.download_button(
            "Download Uploaded Data",
            df.to_csv(index=False).encode("utf-8"),
            "operational_data.csv",
            "text/csv"
        )


    # ========================================================
    # SUCCESS MESSAGE
    # ========================================================

    st.divider()

    st.success(
        f"✅ Analysis completed for "
        f"**{company_name or 'your organization'}**."
    )


except Exception as e:

    st.error(
        f"❌ Could not process the file: {e}"
    )


# ============================================================
# RESET BUTTON
# ============================================================

st.divider()

if st.button("🔄 Start New Analysis"):

    st.session_state.n8n_sent = False

    st.rerun()
