import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# Generative Insight — AI Operations Manager
# Robust mobile-friendly Streamlit app
# Fixes:
# 1. Raw HTML/code appearing on the Hero screen
# 2. XLSX "list index out of range" upload failures
# 3. Better CSV/XLS/XLSX validation and error messages
# ------------------------------------------------------------

st.set_page_config(
    page_title="Generative Insight | AI Operations Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MAX_FILE_SIZE = 5 * 1024 * 1024

REQUIRED_COLUMNS = [
    "Employee_ID",
    "Team",
    "Target",
    "Production",
    "AHT_Actual",
    "Quality_%",
    "SLA_%",
    "Attendance",
    "Error_Count",
]


# ============================================================
# PAGE STYLING
# ============================================================

st.markdown(
    """
    <style>
    .main {
        background: linear-gradient(180deg, #F7FBFF 0%, #FFFFFF 45%);
    }

    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .gi-brand {
        font-size: 30px;
        font-weight: 800;
        letter-spacing: -0.8px;
        color: #071A3D;
        margin-bottom: 2px;
    }

    .gi-brand span {
        color: #0757B8;
    }

    .gi-tagline {
        color: #667085;
        font-size: 14px;
        margin-bottom: 4px;
    }

    .gi-nav {
        color: #667085;
        font-size: 13px;
        margin-bottom: 22px;
    }

    .gi-nav a {
        color: #0757B8;
        text-decoration: underline;
    }

    .hero {
        border: 1px solid #D8E7F8;
        border-radius: 18px;
        padding: 30px;
        background: linear-gradient(135deg, #EFF8FF 0%, #F9FCFF 58%, #FFF9EF 100%);
        margin-bottom: 24px;
    }

    .hero h1 {
        color: #071A3D;
        font-size: 38px;
        line-height: 1.12;
        margin: 0 0 10px 0;
        letter-spacing: -1.2px;
    }

    .brand-subtitle {
        color: #0757B8;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .hero p {
        color: #475467;
        font-size: 16px;
        line-height: 1.65;
        max-width: 850px;
        margin: 0;
    }

    .section-title {
        color: #071A3D;
        font-size: 24px;
        font-weight: 750;
        margin: 12px 0 4px 0;
    }

    .section-help {
        color: #667085;
        margin-bottom: 16px;
    }

    .upload-box {
        background: #FFFFFF;
        border: 1px solid #D8E7F8;
        border-radius: 14px;
        padding: 18px;
        margin: 10px 0 18px 0;
    }

    .metric-card {
        background: #F7FAFF;
        border: 1px solid #E0E8F5;
        border-radius: 12px;
        padding: 16px;
    }

    .small-note {
        color: #667085;
        font-size: 13px;
    }

    @media (max-width: 700px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1rem;
        }

        .hero {
            padding: 22px;
        }

        .hero h1 {
            font-size: 28px;
        }

        .brand-subtitle {
            font-size: 16px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HERO — IMPORTANT: DO NOT PUT HTML INSIDE A CODE BLOCK
# ============================================================

st.markdown(
    """
    <div class="gi-brand">Generative <span>Insight</span></div>
    <div class="gi-tagline">Insights today. Intelligence tomorrow.</div>
    <div class="gi-nav">
        AI / ML &nbsp; | &nbsp; Annotation &nbsp; | &nbsp;
        Web &amp; App Development &nbsp; · &nbsp;
        <a href="https://generativeinsight.in/" target="_blank">Visit Website</a>
    </div>

    <div class="hero">
        <h1>AI-powered operational intelligence</h1>
        <div class="brand-subtitle">
            Turn operational data into management decisions.
        </div>
        <p>
            Upload Excel/CSV operational data, identify KPI risks,
            investigate team and employee performance, ask the AI
            Operations Copilot questions, and generate management-ready
            reports.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def clean_column_name(name):
    """Normalize Excel/CSV headers without changing their meaning."""
    name = str(name).replace("\ufeff", "").strip()
    name = " ".join(name.split())
    return name


def clean_dataframe(df):
    if df is None:
        raise ValueError("The uploaded file did not contain readable data.")

    df = df.copy()
    df.columns = [clean_column_name(c) for c in df.columns]

    # Remove completely empty rows and columns.
    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")

    if df.empty:
        raise ValueError("The uploaded file contains no usable data.")

    return df


def validate_columns(df):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "Required columns are missing: "
            + ", ".join(missing)
            + "."
        )


def read_uploaded_file(uploaded_file):
    """
    Robust reader for mobile uploads.

    Handles:
      .csv
      .xlsx
      .xls

    For XLSX, explicitly checks that the uploaded bytes are actually
    a valid ZIP-based Excel workbook before pandas/openpyxl is called.
    This prevents confusing 'list index out of range' errors.
    """

    if uploaded_file is None:
        return None

    filename = Path(uploaded_file.name or "").name
    suffix = Path(filename).suffix.lower()
    raw = uploaded_file.getvalue()

    if not raw:
        raise ValueError("The uploaded file is empty.")

    if len(raw) > MAX_FILE_SIZE:
        raise ValueError("File is larger than the 5 MB upload limit.")

    # ---------------- CSV ----------------
    if suffix == ".csv":
        last_error = None

        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
            try:
                bio = io.BytesIO(raw)
                df = pd.read_csv(
                    bio,
                    encoding=encoding,
                    sep=None,
                    engine="python",
                )
                return clean_dataframe(df)
            except Exception as exc:
                last_error = exc

        raise ValueError(
            "Could not read this CSV file. "
            f"Details: {last_error}"
        )

    # ---------------- XLSX ----------------
    if suffix == ".xlsx":
        # A real XLSX file is a ZIP package and normally starts with PK.
        if not raw.startswith(b"PK"):
            raise ValueError(
                "This file is named .xlsx but its internal format is not "
                "a valid XLSX workbook. On your phone, open the file in "
                "Excel/Google Sheets and use Export/Save As → Excel (.xlsx), "
                "then upload the newly exported file."
            )

        try:
            bio = io.BytesIO(raw)

            # Check ZIP integrity before openpyxl.
            with zipfile.ZipFile(bio) as zf:
                bad_member = zf.testzip()
                if bad_member is not None:
                    raise ValueError(
                        f"The Excel workbook is corrupted "
                        f"(damaged item: {bad_member})."
                    )

            bio.seek(0)

            # Load all sheets safely. This avoids assuming sheet index 0 exists.
            excel = pd.ExcelFile(bio, engine="openpyxl")
            sheet_names = excel.sheet_names

            if not sheet_names:
                raise ValueError(
                    "The XLSX workbook has no worksheets. "
                    "Please save/export it again as a normal Excel workbook."
                )

            usable_sheets = []

            for sheet in sheet_names:
                try:
                    sheet_df = pd.read_excel(
                        excel,
                        sheet_name=sheet,
                        engine="openpyxl",
                    )
                    sheet_df = clean_dataframe(sheet_df)

                    if not sheet_df.empty:
                        usable_sheets.append((sheet, sheet_df))
                except Exception:
                    # Ignore an empty/broken secondary sheet and continue.
                    continue

            if not usable_sheets:
                raise ValueError(
                    "The XLSX file opened, but none of its worksheets "
                    "contain readable data."
                )

            # Prefer the sheet containing the required operational columns.
            for sheet_name, sheet_df in usable_sheets:
                normalized = set(sheet_df.columns)
                if all(col in normalized for col in REQUIRED_COLUMNS):
                    return sheet_df

            # If no sheet matches, return the first readable sheet so the
            # validation message can tell the user exactly what is missing.
            return usable_sheets[0][1]

        except zipfile.BadZipFile:
            raise ValueError(
                "The uploaded .xlsx file is not a valid Excel workbook. "
                "Please export/save it again as .xlsx and upload the new file."
            )
        except IndexError:
            raise ValueError(
                "Excel workbook structure could not be read safely. "
                "This usually means the workbook was created/exported in "
                "an incompatible format. Please open it in Excel or "
                "Google Sheets and export it again as .xlsx."
            )
        except Exception as exc:
            raise ValueError(
                "Could not open this XLSX file. "
                "Please export/save it again as .xlsx. "
                f"Technical detail: {type(exc).__name__}: {exc}"
            )

    # ---------------- XLS ----------------
    if suffix == ".xls":
        try:
            # xlrd is required for old binary .xls files.
            df = pd.read_excel(io.BytesIO(raw), engine="xlrd")
            return clean_dataframe(df)
        except ImportError:
            raise ValueError(
                "Old .xls format requires the xlrd package. "
                "Please save/export the file as .xlsx or .csv and upload it again."
            )
        except Exception as exc:
            raise ValueError(
                "Could not read this .xls file. "
                "For best compatibility, open it on your phone and "
                "export it as .xlsx or .csv. "
                f"Details: {type(exc).__name__}: {exc}"
            )

    raise ValueError(
        "Unsupported file type. Please upload a real .csv, .xlsx, or .xls file."
    )


def import_engine():
    try:
        from engine import analyze_data, make_ai_prompt
        return analyze_data, make_ai_prompt
    except Exception as exc:
        st.error(
            "engine.py could not be imported. Make sure engine.py is in the "
            "same directory as app.py."
        )
        st.code(str(exc))
        return None, None


def make_safe_numeric(df, columns):
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


# ============================================================
# REPORT SETUP
# ============================================================

st.markdown('<div class="section-title">🏢 Report Setup</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-help">Configure the report and upload your operational data.</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    company_name = st.text_input(
        "Company Name",
        value="Generative Insight",
        key="company_name",
    )

with col2:
    manager_email = st.text_input(
        "Manager Email",
        value="",
        placeholder="manager@company.com",
        key="manager_email",
    )

report_name = st.text_input(
    "Report Name",
    value="Daily Operations Report",
    key="report_name",
)

st.markdown('<div class="upload-box">', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "📁 Upload Excel or CSV operational data — max 5 MB",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=False,
    key="operations_file",
    help=(
        "Mobile users: upload a real .csv/.xlsx/.xls file. "
        "If an Excel file fails, open it in Excel/Google Sheets and "
        "export it again as .xlsx."
    ),
)

st.markdown(
    '<div class="small-note">'
    'Required columns: Employee_ID, Team, Target, Production, '
    'AHT_Actual, Quality_%, SLA_%, Attendance, Error_Count'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# FILE PROCESSING
# ============================================================

if uploaded_file is not None:
    st.session_state["uploaded_filename"] = uploaded_file.name

    try:
        df = read_uploaded_file(uploaded_file)
        validate_columns(df)

        # Convert metric columns to numbers safely.
        df = make_safe_numeric(
            df,
            [
                "Target",
                "Production",
                "AHT_Actual",
                "Quality_%",
                "SLA_%",
                "Error_Count",
            ],
        )

        st.success(
            f"✅ File loaded successfully: {uploaded_file.name} "
            f"({len(df):,} records)"
        )

        with st.expander("Preview uploaded data"):
            st.dataframe(df.head(20), use_container_width=True)

        analyze_clicked = st.button(
            "🚀 Analyze Operational Data",
            type="primary",
            use_container_width=True,
        )

        if analyze_clicked:
            analyze_data, make_ai_prompt = import_engine()

            if analyze_data is not None:
                try:
                    with st.spinner("Analyzing operational performance..."):
                        result = analyze_data(df)

                    st.session_state["analysis_result"] = result
                    st.session_state["ai_prompt"] = make_ai_prompt(result)

                    st.success("Analysis completed successfully.")

                except Exception as exc:
                    st.error(
                        "The file was read successfully, but analysis failed."
                    )
                    with st.expander("Technical details"):
                        st.code(
                            f"{type(exc).__name__}: {exc}",
                            language="text",
                        )

    except ValueError as exc:
        st.error(f"❌ Could not read the uploaded file: {exc}")

        st.info(
            "📱 Mobile fix: if this is an Excel file, open it in Excel or "
            "Google Sheets → Save/Export → Excel (.xlsx) → upload the newly "
            "exported file. Do not rename a CSV/PDF/other file to .xlsx."
        )

    except Exception as exc:
        st.error(
            "❌ Could not read the uploaded file. "
            "The application handled the upload safely, but the file format "
            "could not be interpreted."
        )

        with st.expander("Technical details"):
            st.code(
                f"{type(exc).__name__}: {exc}",
                language="text",
            )


# ============================================================
# DASHBOARD
# ============================================================

result = st.session_state.get("analysis_result")

if result:
    st.divider()
    st.markdown("## 📊 Operations Dashboard")

    overall = result.get("overall", {})

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Productivity",
            f"{float(overall.get('productivity', 0)):.1f}%",
        )

    with c2:
        st.metric(
            "Quality",
            f"{float(overall.get('quality', 0)):.1f}%",
        )

    with c3:
        st.metric(
            "SLA",
            f"{float(overall.get('sla', 0)):.1f}%",
        )

    with c4:
        st.metric(
            "Avg AHT",
            f"{float(overall.get('aht', 0)):.1f}",
        )

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📈 Team Performance",
            "⚠️ Employee Risk",
            "🔎 AI Insights",
            "🤖 Copilot Prompt",
            "📄 Export",
        ]
    )

    with tab1:
        team_df = result.get("team")
        if team_df is not None and not team_df.empty:
            st.dataframe(team_df, use_container_width=True)

            if "Productivity_%" in team_df.columns:
                chart_df = team_df.set_index("Team")[["Productivity_%"]]
                st.bar_chart(chart_df)

    with tab2:
        employee_df = result.get("employees")
        if employee_df is not None and not employee_df.empty:
            st.dataframe(employee_df, use_container_width=True)

    with tab3:
        findings_df = result.get("findings")
        actions_df = result.get("actions")

        st.subheader("Findings")
        if findings_df is not None and not findings_df.empty:
            st.dataframe(findings_df, use_container_width=True)
        else:
            st.success("No KPI findings were generated from the supplied data.")

        st.subheader("Recommended Actions")
        if actions_df is not None and not actions_df.empty:
            st.dataframe(actions_df, use_container_width=True)

    with tab4:
        ai_prompt = st.session_state.get("ai_prompt", "")
        st.text_area(
            "AI Operations Copilot Prompt",
            value=ai_prompt,
            height=420,
        )

        if ai_prompt:
            st.download_button(
                "⬇️ Download AI Prompt",
                data=ai_prompt,
                file_name="ai_operations_prompt.txt",
                mime="text/plain",
                use_container_width=True,
            )

    with tab5:
        team_df = result.get("team")
        employee_df = result.get("employees")
        findings_df = result.get("findings")
        actions_df = result.get("actions")

        st.subheader("Download report tables")

        if team_df is not None:
            st.download_button(
                "⬇️ Team Performance CSV",
                team_df.to_csv(index=False).encode("utf-8"),
                file_name="team_performance.csv",
                mime="text/csv",
                use_container_width=True,
            )

        if employee_df is not None:
            st.download_button(
                "⬇️ Employee Risk CSV",
                employee_df.to_csv(index=False).encode("utf-8"),
                file_name="employee_risk.csv",
                mime="text/csv",
                use_container_width=True,
            )

        if findings_df is not None:
            st.download_button(
                "⬇️ Findings CSV",
                findings_df.to_csv(index=False).encode("utf-8"),
                file_name="findings.csv",
                mime="text/csv",
                use_container_width=True,
            )

        if actions_df is not None:
            st.download_button(
                "⬇️ Actions CSV",
                actions_df.to_csv(index=False).encode("utf-8"),
                file_name="recommended_actions.csv",
                mime="text/csv",
                use_container_width=True,
            )

        report_payload = {
            "company_name": company_name,
            "manager_email": manager_email,
            "report_name": report_name,
            "overall": overall,
        }

        st.download_button(
            "⬇️ Download Report Summary JSON",
            data=json.dumps(report_payload, indent=2, default=str),
            file_name="operations_report_summary.json",
            mime="application/json",
            use_container_width=True,
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()
st.caption(
    "Generative Insight • AI / ML • Annotation • Web & App Development"
)
