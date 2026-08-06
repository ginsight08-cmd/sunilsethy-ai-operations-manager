```python
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

                "company_name":
                    company_name.strip(),

                "manager_email":
                    manager_email.strip(),

                "report_name":
                    report_name.strip()

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
                "⏱️ n8n workflow timed out."
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
    # AI RISK DASHBOARD
    # ========================================================

    st.divider()

    st.subheader(
        "🎯 AI Operations Risk Dashboard"
    )


    # --------------------------------------------------------
    # KPI VALUES
    # --------------------------------------------------------

    productivity = result["overall"]["productivity"]

    quality = result["overall"]["quality"]

    sla = result["overall"]["sla"]

    aht = result["overall"]["aht"]


    # --------------------------------------------------------
    # KPI GAPS
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # KPI BREACH COUNT
    # --------------------------------------------------------

    breaches = 0


    if productivity < productivity_target:

        breaches += 1


    if quality < quality_target:

        breaches += 1


    if sla < sla_target:

        breaches += 1


    if aht > aht_target:

        breaches += 1


    # --------------------------------------------------------
    # RISK LEVEL
    # --------------------------------------------------------

    if breaches >= 3:

        risk_level = "🔴 HIGH"

    elif breaches >= 1:

        risk_level = "🟠 MEDIUM"

    else:

        risk_level = "🟢 LOW"


    # --------------------------------------------------------
    # ACTION COUNT
    # --------------------------------------------------------

    actions_df = result.get(
        "actions",
        pd.DataFrame()
    )


    if isinstance(actions_df, pd.DataFrame):

        action_count = len(actions_df)

    else:

        action_count = 0


    # --------------------------------------------------------
    # HIGH PRIORITY ACTION COUNT
    # --------------------------------------------------------

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

                    actions_df[
                        priority_column
                    ]
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


    # --------------------------------------------------------
    # RISK SUMMARY CARDS
    # --------------------------------------------------------

    r1, r2, r3, r4 = st.columns(4)


    with r1:

        st.metric(

            "Overall Risk",

            risk_level

        )


    with r2:

        st.metric(

            "KPI Breaches",

            breaches,

            delta=(
                f"{4 - breaches} KPIs on target"
            )

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


    # --------------------------------------------------------
    # KPI PERFORMANCE
    # --------------------------------------------------------

    st.subheader(
        "📊 KPI Performance vs Target"
    )


    k1, k2, k3, k4 = st.columns(4)


    with k1:

        st.metric(

            "Productivity",

            f"{productivity:.2f}%",

            delta=(
                f"{productivity_gap:+.2f}% vs target"
            )

        )


    with k2:

        st.metric(

            "Quality",

            f"{quality:.2f}%",

            delta=(
                f"{quality_gap:+.2f}% vs target"
            )

        )


    with k3:

        st.metric(

            "SLA",

            f"{sla:.2f}%",

            delta=(
                f"{sla_gap:+.2f}% vs target"
            )

        )


    with k4:

        st.metric(

            "Average AHT",

            f"{aht:.2f}",

            delta=(
                f"{aht_gap:+.2f} vs target"
            )

        )


    # --------------------------------------------------------
    # MANAGEMENT SUMMARY
    # --------------------------------------------------------

    st.subheader(
        "🧠 Management Summary"
    )


    if breaches == 0:

        st.success(

            "✅ All monitored KPIs are currently "
            "meeting their defined targets."

        )

    elif breaches == 1:

        st.warning(

            "⚠️ 1 KPI requires management attention. "
            f"Current overall risk level: {risk_level}."

        )

    else:

        st.warning(

            f"⚠️ {breaches} KPIs require management "
            f"attention. Current overall risk level: "
            f"{risk_level}."

        )


    # --------------------------------------------------------
    # CUSTOMER / REPORT DETAILS
    # --------------------------------------------------------

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

                st.write(
                    "**Company**"
                )

                st.write(
                    company_name
                )


            with info2:

                st.write(
                    "**Manager Email**"
                )

                st.write(
                    manager_email
                )


            with info3:

                st.write(
                    "**Report**"
                )

                st.write(
                    report_name
                )


    st.divider()


    # ========================================================
    # ORIGINAL KPI CARDS
    # ========================================================

    st.subheader(
        "📊 Operational KPI Dashboard"
    )


    k1, k2, k3, k4 = st.columns(4)


    with k1:

        st.metric(

            "Productivity",

            f"{productivity:.1f}%",

            delta=(
                f"Target {productivity_target}%"
            )

        )


    with k2:

        st.metric(

            "Quality",

            f"{quality:.1f}%",

            delta=(
                f"Target {quality_target}%"
            )

        )


    with k3:

        st.metric(

            "SLA",

            f"{sla:.1f}%",

            delta=(
                f"Target {sla_target}%"
            )

        )


    with k4:

        st.metric(

            "Average AHT",

            f"{aht:.1f}",

            delta=(
                f"Target {aht_target}"
            )

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
```
