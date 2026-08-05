
import streamlit as st
import pandas as pd
from engine import analyze_data, make_ai_prompt

st.set_page_config(page_title="AI Operations Manager", page_icon="🤖", layout="wide")

st.title("🤖 AI Operations Manager")
st.caption("Upload operational data → analyze performance → identify risks → create actions.")

with st.sidebar:
    st.header("Controls")
    st.info("MVP: calculations and rule-based insights work locally. AI provider integration is prepared through the generated prompt.")
    productivity_target = st.number_input("Productivity target %", 1, 200, 90)
    quality_target = st.number_input("Quality target %", 1, 100, 95)
    sla_target = st.number_input("SLA target %", 1, 100, 97)
    aht_target = st.number_input("AHT target", 1, 1000, 50)

uploaded = st.file_uploader("Upload Excel or CSV operational data", type=["xlsx", "xls", "csv"])

if not uploaded:
    st.warning("Upload the Step 1 Operational_Data sheet as Excel, or a CSV with the required columns.")
    st.markdown("### Required columns")
    st.code("Date, Employee_ID, Employee_Name, Team, Target, Production, AHT_Actual, AHT_Target, Quality_%, SLA_%, Attendance, Error_Count, Error_Category")
    st.stop()

try:
    if uploaded.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        xls = pd.ExcelFile(uploaded)
        sheet = "Operational_Data" if "Operational_Data" in xls.sheet_names else xls.sheet_names[0]
        df = pd.read_excel(uploaded, sheet_name=sheet)

    result = analyze_data(
        df,
        productivity_target=productivity_target,
        quality_target=quality_target,
        sla_target=sla_target,
        aht_target=aht_target,
    )

    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Productivity", f"{result['overall']['productivity']:.1f}%")
    k2.metric("Quality", f"{result['overall']['quality']:.1f}%")
    k3.metric("SLA", f"{result['overall']['sla']:.1f}%")
    k4.metric("AHT", f"{result['overall']['aht']:.1f}")

    st.divider()

    tabs = st.tabs(["📊 Dashboard", "🚨 AI Insights", "👥 Employee Risk", "✅ Action Center", "🧠 AI Prompt", "📥 Export"])

    with tabs[0]:
        st.subheader("Team Performance")
        st.dataframe(result["team"], use_container_width=True)
        st.bar_chart(result["team"].set_index("Team")["Productivity_%"])

    with tabs[1]:
        st.subheader("Automated Findings")
        if result["findings"].empty:
            st.success("No threshold breaches detected.")
        else:
            st.dataframe(result["findings"], use_container_width=True)
        st.info("Root causes are evidence-based hypotheses. The app does not claim causality where the data cannot prove it.")

    with tabs[2]:
        st.subheader("Employee Risk")
        st.dataframe(result["employees"].sort_values(["Risk_Score","Avg_Productivity"], ascending=[False, True]), use_container_width=True)

    with tabs[3]:
        st.subheader("Recommended Actions")
        st.dataframe(result["actions"], use_container_width=True)

    with tabs[4]:
        st.subheader("AI Analyst Prompt")
        st.code(make_ai_prompt(result), language="text")
        st.caption("Paste this into your approved LLM/API integration. Step 7 can automate the API call and parse the JSON response.")

    with tabs[5]:
        st.subheader("Download analysis")
        st.download_button(
            "Download Team Analysis CSV",
            result["team"].to_csv(index=False).encode("utf-8"),
            "team_analysis.csv",
            "text/csv",
        )
        st.download_button(
            "Download Action Plan CSV",
            result["actions"].to_csv(index=False).encode("utf-8"),
            "action_plan.csv",
            "text/csv",
        )

except Exception as e:
    st.error(f"Could not process the file: {e}")
    st.markdown("Check the required column names shown above.")
