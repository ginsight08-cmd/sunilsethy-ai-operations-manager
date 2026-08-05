import streamlit as st
import pandas as pd
import requests
from engine import analyze_data, make_ai_prompt

st.set_page_config(
    page_title="AI Operations Manager",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Operations Manager")
st.caption(
    "Upload operational data → analyze performance → "
    "identify risks → create actions."
)

# -----------------------------
# SETTINGS
# -----------------------------
with st.sidebar:
    st.header("Controls")

    productivity_target = st.number_input(
        "Productivity target %",
        1, 200, 90
    )

    quality_target = st.number_input(
        "Quality target %",
        1, 100, 95
    )

    sla_target = st.number_input(
        "SLA target %",
        1, 100, 97
    )

    aht_target = st.number_input(
        "AHT target",
        1, 1000, 50
    )

# -----------------------------
# FILE UPLOAD
# -----------------------------
uploaded = st.file_uploader(
    "Upload Excel or CSV operational data",
    type=["xlsx", "xls", "csv"]
)

if not uploaded:
    st.warning(
        "Upload the Step 1 Operational_Data sheet as Excel, "
        "or a CSV with the required columns."
    )

    st.markdown("### Required columns")

    st.code(
        "Date, Employee_ID, Employee_Name, Team, Target, "
        "Production, AHT_Actual, AHT_Target, Quality_%, "
        "SLA_%, Attendance, Error_Count, Error_Category"
    )

    st.stop()

# -----------------------------
# SEND FILE TO N8N
# -----------------------------
if "n8n_sent" not in st.session_state:
    st.session_state.n8n_sent = False

if not st.session_state.n8n_sent:

    n8n_url = st.secrets.get("N8N_WEBHOOK_URL", "")

    if n8n_url:

        try:

            uploaded.seek(0)

            files = {
                "file": (
                    uploaded.name,
                    uploaded.getvalue(),
                    uploaded.type or "application/octet-stream"
                )
            }

            response = requests.post(
                n8n_url,
                files=files,
                timeout=30
            )

            if response.status_code < 300:

                st.success(
                    "✅ File successfully sent to automation workflow."
                )

                st.session_state.n8n_sent = True

            else:

                st.warning(
                    f"n8n received a response with status "
                    f"{response.status_code}."
                )

        except Exception as e:

            st.warning(
                f"Could not connect to n8n: {e}"
            )

    else:

        st.info(
            "n8n automation is not configured yet. "
            "The file will still be analyzed locally."
        )

# -----------------------------
# READ FILE
# -----------------------------
try:

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

    # -----------------------------
    # ANALYSIS
    # -----------------------------
    result = analyze_data(
        df,
        productivity_target=productivity_target,
        quality_target=quality_target,
        sla_target=sla_target,
        aht_target=aht_target
    )

    # -----------------------------
    # KPI CARDS
    # -----------------------------
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

    st.divider()

    tabs = st.tabs([
        "📊 Dashboard",
        "🚨 AI Insights",
        "👥 Employee Risk",
        "✅ Action Center",
        "🧠 AI Prompt",
        "📥 Export"
    ])

    # -----------------------------
    # DASHBOARD
    # -----------------------------
    with tabs[0]:

        st.subheader("Team Performance")

        st.dataframe(
            result["team"],
            use_container_width=True
        )

        st.bar_chart(
            result["team"].set_index("Team")[
                "Productivity_%"
            ]
        )

    # -----------------------------
    # AI INSIGHTS
    # -----------------------------
    with tabs[1]:

        st.subheader("Automated Findings")

        if result["findings"].empty:

            st.success(
                "No threshold breaches detected."
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

    # -----------------------------
    # EMPLOYEE RISK
    # -----------------------------
    with tabs[2]:

        st.subheader("Employee Risk")

        st.dataframe(
            result["employees"].sort_values(
                ["Risk_Score", "Avg_Productivity"],
                ascending=[False, True]
            ),
            use_container_width=True
        )

    # -----------------------------
    # ACTION CENTER
    # -----------------------------
    with tabs[3]:

        st.subheader("Recommended Actions")

        st.dataframe(
            result["actions"],
            use_container_width=True
        )

    # -----------------------------
    # AI PROMPT
    # -----------------------------
    with tabs[4]:

        st.subheader("AI Analyst Prompt")

        st.code(
            make_ai_prompt(result),
            language="text"
        )

        st.caption(
            "This prompt will later be sent automatically "
            "to our selected AI provider."
        )

    # -----------------------------
    # EXPORT
    # -----------------------------
    with tabs[5]:

        st.subheader("Download Analysis")

        st.download_button(
            "Download Team Analysis CSV",
            result["team"].to_csv(index=False).encode("utf-8"),
            "team_analysis.csv",
            "text/csv"
        )

        st.download_button(
            "Download Action Plan CSV",
            result["actions"].to_csv(index=False).encode("utf-8"),
            "action_plan.csv",
            "text/csv"
        )

except Exception as e:

    st.error(
        f"Could not process the file: {e}"
    )
