import io
import json
import smtplib
from datetime import datetime
from pathlib import Path
from email.message import EmailMessage

import pandas as pd
import requests
import streamlit as st
from supabase import create_client, Client

from engine import analyze_data, make_ai_prompt


# ============================================================
# GENERATIVE INSIGHT | AI OPERATIONS COPILOT
# Mobile-friendly Streamlit application
# ============================================================

APP_NAME = "Generative Insight"
APP_VERSION = "1.1.0"

st.set_page_config(
    page_title="Generative Insight | AI Operations Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# BRAND CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

# Put your company logo at:
# assets/Generative_insight.png
LOGO_PATH = BASE_DIR / "assets" / "Generative_insight.png"

WEBSITE_URL = "https://generativeinsight.in"

BRAND_BLUE = "#0757B8"
BRAND_CYAN = "#00AEEF"
BRAND_ORANGE = "#FF9D00"
BRAND_NAVY = "#071A3D"


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "authenticated": False,
    "user_email": "",
    "user_id": "",
    "user_name": "",
    "company_name": "",
    "user_plan": "Free",
    "n8n_sent": False,
    "n8n_result": None,
    "copilot_answer": None,
    "last_question": "",
    "file_name": "",
    "analysis_result": None,
    "analysis_df": None,
    "report_pdf": None,
    "report_generated_at": None,
    "show_plans": False,
    "mobile_section": "📊 Dashboard",
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# MOBILE + BRAND CSS
# ============================================================

st.markdown(
    f"""
    <style>
        .gi-brand {{
            font-size: 2rem;
            font-weight: 800;
            color: {BRAND_NAVY};
            line-height: 1.1;
        }}

        .gi-brand span {{
            color: {BRAND_BLUE};
        }}

        .gi-tagline {{
            color: #667085;
            font-size: 0.9rem;
            margin-top: 4px;
        }}

        .hero {{
            padding: 22px;
            border-radius: 18px;
            background: linear-gradient(
                135deg,
                #f4f8ff 0%,
                #eefaff 100%
            );
            border: 1px solid #dbe7f5;
            margin-bottom: 18px;
        }}

        .main-title {{
            font-size: clamp(1.6rem, 5vw, 2.6rem);
            font-weight: 800;
            color: {BRAND_NAVY};
        }}

        .brand-subtitle {{
            font-size: clamp(1rem, 3vw, 1.25rem);
            font-weight: 600;
            color: {BRAND_BLUE};
            margin-top: 5px;
        }}

        .copilot-card {{
            padding: 18px;
            border-radius: 16px;
            border: 2px solid #d8e8ff;
            background: #f8fbff;
            margin: 10px 0 18px 0;
        }}

        .copilot-title {{
            font-size: 1.25rem;
            font-weight: 800;
            color: {BRAND_NAVY};
        }}

        .plan-card {{
            padding: 18px;
            border: 1px solid #e4e7ec;
            border-radius: 14px;
            margin-bottom: 12px;
        }}

        div[data-testid="stMetric"] {{
            min-height: 95px;
        }}

        /* Make Streamlit tabs easier to use on phones. */
        div[data-testid="stTabs"] {{
            width: 100%;
        }}

        div[data-testid="stTabs"] [role="tablist"] {{
            gap: 6px;
            overflow-x: auto;
            flex-wrap: nowrap;
            scrollbar-width: thin;
            padding-bottom: 5px;
        }}

        div[data-testid="stTabs"] button[role="tab"] {{
            white-space: nowrap;
            min-width: max-content;
        }}

        @media (max-width: 768px) {{
            .hero {{
                padding: 16px;
            }}

            .main-title {{
                font-size: 1.65rem;
            }}

            .brand-subtitle {{
                font-size: 1rem;
            }}

            .stButton button,
            .stDownloadButton button {{
                min-height: 46px;
            }}

            div[data-testid="stFileUploader"] {{
                width: 100%;
            }}

            .copilot-card {{
                padding: 14px;
            }}
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def secret(name, default=""):
    try:
        value = st.secrets.get(name, default)
        return value if value is not None else default
    except Exception:
        return default


def show_brand_header(compact=False):
    """Display the company logo and website branding."""

    if LOGO_PATH.exists():
        st.image(
            str(LOGO_PATH),
            width=230 if compact else 330,
        )
    else:
        st.markdown(
            """
            <div class="gi-brand">
                Generative <span>Insight</span>
            </div>
            <div class="gi-tagline">
                Insights today. Intelligence tomorrow.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div style="
            margin-top:-8px;
            margin-bottom:18px;
            color:#667085;
            font-size:0.85rem;
        ">
            AI / ML &nbsp; | &nbsp;
            Annotation &nbsp; | &nbsp;
            Web & App Development
            &nbsp;&nbsp;·&nbsp;&nbsp;
            <a href="{WEBSITE_URL}" target="_blank">
                Visit Website
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_supabase_client() -> Client:
    url = secret("SUPABASE_URL")
    anon_key = secret("SUPABASE_ANON_KEY")

    if not url or not anon_key:
        raise RuntimeError(
            "Supabase authentication is not configured. "
            "Add SUPABASE_URL and SUPABASE_ANON_KEY to Streamlit Secrets."
        )

    return create_client(url, anon_key)


def friendly_auth_error(error) -> str:
    message = str(getattr(error, "message", error))
    lowered = message.lower()

    if "invalid login credentials" in lowered:
        return "Invalid email or password."
    if "email not confirmed" in lowered:
        return "Please verify your email address before signing in."
    if "user already registered" in lowered:
        return "An account with this email already exists. Please sign in."
    if "password should be at least" in lowered:
        return "Password must meet Supabase's minimum password requirements."
    if "rate limit" in lowered:
        return "Too many attempts. Please wait a moment and try again."
    if "name or service not known" in lowered:
        return (
            "Could not connect to Supabase. Check SUPABASE_URL and "
            "SUPABASE_ANON_KEY in Streamlit Secrets."
        )

    return message


def sign_up_user(full_name, company_name, email, password):
    supabase = get_supabase_client()

    return supabase.auth.sign_up(
        {
            "email": email.strip().lower(),
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name.strip(),
                    "company_name": company_name.strip(),
                    "plan": "Free",
                }
            },
        }
    )


def sign_in_user(email, password):
    supabase = get_supabase_client()

    return supabase.auth.sign_in_with_password(
        {
            "email": email.strip().lower(),
            "password": password,
        }
    )


def sign_out_user():
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()
    except Exception:
        pass


def set_authenticated_user(response):
    user = getattr(response, "user", None)

    if user is None:
        raise RuntimeError(
            "Authentication succeeded but no user was returned."
        )

    metadata = getattr(user, "user_metadata", {}) or {}

    st.session_state.authenticated = True
    st.session_state.user_email = (user.email or "").lower()
    st.session_state.user_id = user.id
    st.session_state.user_name = metadata.get("full_name", "")
    st.session_state.company_name = metadata.get("company_name", "")
    st.session_state.user_plan = metadata.get("plan", "Free") or "Free"


def clear_analysis():
    st.session_state.n8n_sent = False
    st.session_state.n8n_result = None
    st.session_state.copilot_answer = None
    st.session_state.last_question = ""
    st.session_state.file_name = ""
    st.session_state.analysis_result = None
    st.session_state.analysis_df = None
    st.session_state.report_pdf = None
    st.session_state.report_generated_at = None


def clear_authentication():
    sign_out_user()

    st.session_state.authenticated = False
    st.session_state.user_email = ""
    st.session_state.user_id = ""
    st.session_state.user_name = ""
    st.session_state.company_name = ""
    st.session_state.user_plan = "Free"
    st.session_state.show_plans = False

    clear_analysis()


def get_plan_config(plan):
    configs = {
        "Free": {
            "max_mb": 5,
            "copilot": True,
            "pdf": True,
            "email": False,
            "automation": False,
            "price": "₹0",
        },
        "Professional": {
            "max_mb": 25,
            "copilot": True,
            "pdf": True,
            "email": True,
            "automation": True,
            "price": "₹1,999/mo",
        },
        "Business": {
            "max_mb": 100,
            "copilot": True,
            "pdf": True,
            "email": True,
            "automation": True,
            "price": "Custom",
        },
    }

    return configs.get(plan, configs["Free"])


def normalize_n8n_response(response):
    try:
        data = response.json()
    except ValueError:
        return {"answer": response.text}

    if isinstance(data, list):
        if not data:
            return {"answer": "The workflow returned an empty response."}
        data = data[0]

    return data if isinstance(data, dict) else {"answer": data}


def parse_ai_answer(data):
    answer = data

    if isinstance(data, dict):
        answer = (
            data.get("answer")
            or data.get("response")
            or data.get("output")
            or data.get("text")
            or data.get("message")
        )

    if isinstance(answer, str):
        text = answer.strip()

        if text.startswith("```"):
            text = text.replace("```json", "", 1).replace("```", "", 1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    return answer


def dataframe_to_text(df):
    if df is None or df.empty:
        return "No records available."

    return df.to_string(index=False)


def build_copilot_context(
    company_name,
    report_name,
    result,
    productivity_target,
    quality_target,
    sla_target,
    aht_target,
    risk_level,
    summary_points,
):
    overall = result["overall"]

    return f"""
Company:
{company_name}

Report:
{report_name}

Operational KPIs:

Productivity:
{float(overall["productivity"]):.2f}% | Target: {productivity_target}%

Quality:
{float(overall["quality"]):.2f}% | Target: {quality_target}%

SLA:
{float(overall["sla"]):.2f}% | Target: {sla_target}%

Average AHT:
{float(overall["aht"]):.2f} | Target: {aht_target}

Overall Risk:
{risk_level}

Operational Findings:
{dataframe_to_text(result.get("findings"))}

Recommended Actions:
{dataframe_to_text(result.get("actions"))}

Employee Risk Data:
{dataframe_to_text(result.get("employees"))}

Team Performance:
{dataframe_to_text(result.get("team"))}

KPI Summary:
{chr(10).join(summary_points)}
""".strip()


def create_pdf_report(
    company_name,
    report_name,
    result,
    risk_level,
    summary_points,
    recommendation,
):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        raise RuntimeError(
            "PDF generation requires reportlab. Add reportlab to requirements.txt."
        )

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"{company_name} - {report_name}",
        author=APP_NAME,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "GI_Title",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        spaceAfter=8,
    )

    heading_style = ParagraphStyle(
        "GI_Heading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        spaceBefore=10,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "GI_Body",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
    )

    story = [
        Paragraph("Generative Insight", title_style),
        Paragraph(
            f"<b>{company_name}</b> — {report_name}<br/>"
            f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}",
            body_style,
        ),
        Spacer(1, 8),
    ]

    overall = result["overall"]

    targets = result.get("_targets", {})

    kpi_rows = [
        ["KPI", "Actual", "Target"],
        [
            "Productivity",
            f'{float(overall["productivity"]):.2f}%',
            f'{targets.get("productivity", "")}%',
        ],
        [
            "Quality",
            f'{float(overall["quality"]):.2f}%',
            f'{targets.get("quality", "")}%',
        ],
        [
            "SLA",
            f'{float(overall["sla"]):.2f}%',
            f'{targets.get("sla", "")}%',
        ],
        [
            "Average AHT",
            f'{float(overall["aht"]):.2f}',
            f'{targets.get("aht", "")}',
        ],
    ]

    story.append(Paragraph("Executive Overview", heading_style))
    story.append(Paragraph(f"<b>Risk:</b> {risk_level}", body_style))
    story.append(Spacer(1, 5))

    table = Table(
        kpi_rows,
        colWidths=[55 * mm, 45 * mm, 45 * mm],
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(table)
    story.append(Paragraph("KPI Summary", heading_style))

    for item in summary_points:
        cleaned = (
            item.replace("🔴 ", "")
            .replace("🟢 ", "")
            .replace("🟠 ", "")
            .replace("🟡 ", "")
        )
        story.append(Paragraph(cleaned, body_style))

    story.append(Paragraph("Management Recommendation", heading_style))
    story.append(Paragraph(recommendation, body_style))

    for title, key in [
        ("Team Performance", "team"),
        ("Operational Findings", "findings"),
        ("Recommended Actions", "actions"),
        ("Employee Risk", "employees"),
    ]:
        df = result.get(key)

        if isinstance(df, pd.DataFrame) and not df.empty:
            story.append(Paragraph(title, heading_style))

            pdf_df = df.copy()

            if len(pdf_df.columns) > 8:
                pdf_df = pdf_df.iloc[:, :8]

            headers = [str(c) for c in pdf_df.columns]
            rows = [headers]

            for _, row in pdf_df.head(50).iterrows():
                rows.append([str(v)[:90] for v in row.tolist()])

            col_count = len(headers)
            available_width = 180 * mm
            col_width = available_width / max(col_count, 1)

            tbl = Table(
                rows,
                colWidths=[col_width] * col_count,
                repeatRows=1,
            )

            tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 6),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )

            story.append(tbl)
            story.append(Spacer(1, 5))

    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Generated by Generative Insight AI Operations Copilot. "
            "AI recommendations should be validated against operational "
            "evidence before management action.",
            body_style,
        )
    )

    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()


def send_email_report(
    recipient,
    subject,
    body,
    pdf_bytes=None,
    pdf_filename="operations_report.pdf",
):
    smtp_host = secret("SMTP_HOST")
    smtp_port = int(secret("SMTP_PORT", "587"))
    smtp_user = secret("SMTP_USERNAME")
    smtp_password = secret("SMTP_PASSWORD")
    smtp_from = secret("SMTP_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_password, smtp_from]):
        raise RuntimeError(
            "SMTP settings are not configured in Streamlit Secrets."
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp_from
    message["To"] = recipient
    message.set_content(body)

    if pdf_bytes:
        message.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=pdf_filename,
        )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(message)


def read_uploaded_file(uploaded_file):
    """
    Robust mobile-friendly CSV/XLS/XLSX reader.

    The previous implementation could fail when an Excel workbook had
    no readable sheet or when a mobile-uploaded file was not decoded as
    expected. This function validates the file bytes before parsing and
    never indexes sheet_names[0] unless a sheet exists.
    """
    if uploaded_file is None:
        raise ValueError("No file was uploaded.")

    file_name = str(uploaded_file.name or "").strip()
    suffix = Path(file_name).suffix.lower()

    raw = uploaded_file.getvalue()

    if not raw:
        raise ValueError("The uploaded file is empty.")

    if suffix == ".csv":
        last_error = None

        for encoding in ["utf-8-sig", "utf-8", "cp1252", "latin1"]:
            try:
                frame = pd.read_csv(
                    io.BytesIO(raw),
                    encoding=encoding,
                    low_memory=False,
                )
                if frame is not None:
                    return frame
            except Exception as exc:
                last_error = exc

        raise ValueError(
            f"Could not read CSV file. Please save it as UTF-8 CSV. "
            f"Parser error: {last_error}"
        )

    if suffix in [".xlsx", ".xls"]:
        try:
            workbook = pd.ExcelFile(io.BytesIO(raw))
        except Exception as exc:
            raise ValueError(
                "Could not open the Excel file. Make sure it is a valid "
                f"{suffix.upper()} workbook. Details: {exc}"
            )

        sheets = list(workbook.sheet_names or [])

        if not sheets:
            raise ValueError(
                "The Excel workbook does not contain any readable worksheets."
            )

        preferred = [
            name for name in sheets
            if str(name).strip().lower() == "operational_data"
        ]

        sheet_name = preferred[0] if preferred else sheets[0]

        try:
            frame = pd.read_excel(
                io.BytesIO(raw),
                sheet_name=sheet_name,
            )
        except Exception as exc:
            raise ValueError(
                f"Could not read Excel sheet '{sheet_name}'. Details: {exc}"
            )

        if frame is None:
            raise ValueError("The Excel sheet returned no data.")

        return frame

    raise ValueError(
        "Unsupported file type. Please upload CSV, XLS, or XLSX."
    )


def clean_dataframe(df):
    """Normalize column names and remove completely empty rows/columns."""
    df = df.copy()

    df.columns = [
        str(col).replace("\ufeff", "").strip()
        for col in df.columns
    ]

    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")

    return df


def render_copilot(
    copilot_url,
    plan_config,
    company_name,
    report_name,
    result,
    productivity_target,
    quality_target,
    sla_target,
    aht_target,
    risk_level,
    summary_points,
):
    """Always-visible Management Copilot section, optimized for mobile."""

    st.markdown(
        """
        <div class="copilot-card">
            <div class="copilot-title">🤖 Management Copilot</div>
            <div>
                Ask questions about your uploaded operational data,
                KPI risks, teams, employees, and recommended actions.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "Example: Which team has the biggest productivity gap, "
        "and what action should management take?"
    )

    question = st.text_area(
        "Ask your operational question",
        placeholder=(
            "Example: Which team needs immediate attention and why?"
        ),
        height=100,
        key="mobile_copilot_question",
    )

    ask_copilot = st.button(
        "🚀 Ask Management Copilot",
        type="primary",
        use_container_width=True,
        key="mobile_ask_management_copilot",
    )

    if ask_copilot:
        if not question.strip():
            st.warning("⚠️ Please enter a question first.")

        elif not plan_config["copilot"]:
            st.error("Copilot is not available on your current plan.")

        elif not copilot_url:
            st.error(
                "❌ N8N_COPILOT_WEBHOOK_URL is not configured "
                "in Streamlit Secrets."
            )

        else:
            context = build_copilot_context(
                company_name,
                report_name,
                result,
                productivity_target,
                quality_target,
                sla_target,
                aht_target,
                risk_level,
                summary_points,
            )

            payload = {
                "question": question.strip(),
                "company_name": company_name.strip(),
                "report_name": report_name.strip(),
                "context": context,
                "user_id": st.session_state.user_id,
                "user_email": st.session_state.user_email,
            }

            try:
                with st.spinner("🤖 Management Copilot is analyzing..."):
                    response = requests.post(
                        copilot_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=120,
                    )

                if response.status_code < 300:
                    raw = normalize_n8n_response(response)
                    answer_data = parse_ai_answer(raw)

                    st.session_state.copilot_answer = answer_data
                    st.session_state.last_question = question.strip()

                    st.success("✅ Copilot analysis completed.")
                else:
                    st.session_state.copilot_answer = None
                    st.error(
                        "❌ Copilot workflow failed: "
                        f"HTTP {response.status_code}"
                    )
                    if response.text:
                        st.code(response.text[:3000], language="text")

            except requests.exceptions.Timeout:
                st.session_state.copilot_answer = None
                st.error(
                    "⏱️ Management Copilot timed out. Please try again."
                )

            except requests.exceptions.ConnectionError:
                st.session_state.copilot_answer = None
                st.error(
                    "🔌 Could not connect to the n8n Copilot webhook."
                )

            except requests.exceptions.RequestException as exc:
                st.session_state.copilot_answer = None
                st.error(f"❌ Copilot request failed: {exc}")

            except Exception as exc:
                st.session_state.copilot_answer = None
                st.error(f"❌ Unexpected Copilot error: {exc}")

    if st.session_state.copilot_answer:
        st.divider()
        st.markdown("### 🧠 Copilot Analysis")

        if st.session_state.last_question:
            st.caption(
                "Question: " + st.session_state.last_question
            )

        answer = st.session_state.copilot_answer

        if isinstance(answer, dict):
            what = answer.get("what_is_happening")
            factors = answer.get("contributing_factors", [])
            rec_actions = answer.get("recommended_actions", [])
            priority = answer.get("priority", "")
            owner = answer.get("owner", "")
            timeline = answer.get("timeline", "")
            sufficiency = answer.get("data_sufficiency")

            if what:
                st.markdown("#### 🔎 What is happening")
                st.info(str(what))

            if factors:
                st.markdown("#### 🔍 Contributing Factors")
                for factor in factors:
                    st.write(f"• {factor}")

            if rec_actions:
                st.markdown("#### ✅ Recommended Actions")
                for i, action in enumerate(rec_actions, 1):
                    st.markdown(f"**{i}.** {action}")

            st.markdown("#### 📌 Management Decision")

            d1, d2, d3 = st.columns(3)

            with d1:
                st.metric("Priority", priority or "N/A")

            with d2:
                st.metric("Owner", owner or "N/A")

            with d3:
                st.metric("Timeline", timeline or "N/A")

            if sufficiency:
                st.markdown("#### 📊 Data Sufficiency")
                st.warning(str(sufficiency))

        elif isinstance(answer, str):
            st.markdown(answer)

        else:
            st.code(str(answer), language="text")


# ============================================================
# PRICING
# ============================================================

def show_pricing(section_id="default"):
    st.markdown("### 💳 Plans")

    c1, c2, c3 = st.columns(3)

    plans = [
        (
            c1,
            "Free",
            "₹0",
            [
                "5 MB file limit",
                "Dashboard analytics",
                "AI Copilot",
                "PDF report",
            ],
            "Current plan" if st.session_state.user_plan == "Free" else "Start Free",
        ),
        (
            c2,
            "Professional",
            "₹1,999/mo",
            [
                "25 MB file limit",
                "AI Copilot",
                "PDF + email reports",
                "n8n automation",
            ],
            "Upgrade",
        ),
        (
            c3,
            "Business",
            "Custom",
            [
                "100 MB file limit",
                "Advanced automation",
                "Custom workflows",
                "Team deployment",
            ],
            "Contact Sales",
        ),
    ]

    for col, name, price, features, button in plans:
        with col:
            st.markdown('<div class="plan-card">', unsafe_allow_html=True)
            st.markdown(f"#### {name}")
            st.markdown(f"### {price}")

            for feature in features:
                st.write(f"✓ {feature}")

            checkout_key = f"{name.upper()}_CHECKOUT_URL"
            checkout_url = secret(checkout_key)

            if checkout_url:
                st.link_button(
                    button,
                    checkout_url,
                    use_container_width=True,
                )
            else:
                st.button(
                    button,
                    use_container_width=True,
                    disabled=True,
                    key=f"disabled_{section_id}_{name}",
                )

            st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# AUTHENTICATION PAGE
# ============================================================

if not st.session_state.authenticated:
    show_brand_header()

    st.markdown(
        """
        <div class="hero">
            <div class="main-title">
                AI-powered operational intelligence
            </div>

            <div class="brand-subtitle">
                Turn operational data into management decisions.
            </div>

            <p>
                Create your account, upload Excel/CSV operational data,
                identify KPI risks, investigate team and employee
                performance, ask the AI Operations Copilot questions,
                and generate management-ready reports.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not secret("SUPABASE_URL") or not secret("SUPABASE_ANON_KEY"):
        st.error(
            "🔐 Authentication is not configured yet. "
            "Add SUPABASE_URL and SUPABASE_ANON_KEY in "
            "Streamlit → App Settings → Secrets."
        )
        st.stop()

    signup_tab, login_tab, pricing_tab = st.tabs(
        ["🆕 Create Account", "🔐 Sign In", "💳 Plans"]
    )

    with signup_tab:
        st.markdown("### Create your Generative Insight account")
        st.caption("Start with the Free plan. You can upgrade later.")

        with st.form("signup_form", clear_on_submit=False):
            signup_name = st.text_input(
                "Full Name",
                placeholder="e.g. Sunil Sethy",
            )

            signup_company = st.text_input(
                "Company / Organization",
                placeholder="e.g. ABC Technologies",
            )

            signup_email = st.text_input(
                "Work Email",
                placeholder="name@company.com",
            )

            signup_password = st.text_input(
                "Password",
                type="password",
            )

            signup_confirm = st.text_input(
                "Confirm Password",
                type="password",
            )

            signup_submitted = st.form_submit_button(
                "🚀 Create Free Account",
                type="primary",
                use_container_width=True,
            )

        if signup_submitted:
            if not signup_name.strip():
                st.warning("Please enter your full name.")
            elif not signup_company.strip():
                st.warning("Please enter your company or organization.")
            elif not signup_email.strip() or "@" not in signup_email:
                st.warning("Please enter a valid email address.")
            elif len(signup_password) < 6:
                st.warning("Please use a password with at least 6 characters.")
            elif signup_password != signup_confirm:
                st.warning("Passwords do not match.")
            else:
                try:
                    with st.spinner("Creating your account..."):
                        response = sign_up_user(
                            signup_name,
                            signup_company,
                            signup_email,
                            signup_password,
                        )

                    signup_user = getattr(response, "user", None)
                    signup_session = getattr(response, "session", None)

                    if signup_user is not None and signup_session is not None:
                        set_authenticated_user(response)
                        st.success("✅ Account created successfully.")
                        st.rerun()

                    elif signup_user is not None:
                        st.success(
                            "✅ Account created. Please check your email "
                            "and click the verification link before signing in."
                        )
                    else:
                        st.info(
                            "If the email is valid, check your inbox for "
                            "the verification email."
                        )

                except Exception as exc:
                    st.error(
                        "❌ Could not create account: "
                        + friendly_auth_error(exc)
                    )

    with login_tab:
        st.markdown("### Welcome back")

        with st.form("login_form"):
            login_email = st.text_input(
                "Email",
                placeholder="name@company.com",
            )

            login_password = st.text_input(
                "Password",
                type="password",
            )

            login_submitted = st.form_submit_button(
                "🔐 Sign In",
                type="primary",
                use_container_width=True,
            )

        if login_submitted:
            if not login_email.strip() or not login_password:
                st.warning("Please enter your email and password.")
            else:
                try:
                    with st.spinner("Signing you in..."):
                        response = sign_in_user(
                            login_email,
                            login_password,
                        )

                    set_authenticated_user(response)
                    st.success("✅ Signed in successfully.")
                    st.rerun()

                except Exception as exc:
                    st.error(
                        "❌ Sign in failed: "
                        + friendly_auth_error(exc)
                    )

        st.info(
            "If email confirmation is enabled in Supabase, "
            "verify your email before signing in."
        )

    with pricing_tab:
        show_pricing("login")

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

plan_config = get_plan_config(st.session_state.user_plan)

with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), use_container_width=True)
    else:
        st.markdown(
            """
            <div class="gi-brand">
                Generative <span>Insight</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption("AI Operations Copilot")

    st.markdown(
        f"""
        <a href="{WEBSITE_URL}" target="_blank">
            🌐 Visit Generative Insight
        </a>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.success(f"Plan: **{st.session_state.user_plan}**")

    if st.session_state.get("user_name"):
        st.caption(st.session_state.user_name)

    st.caption(st.session_state.user_email)

    st.divider()
    st.header("⚙️ KPI Controls")

    productivity_target = st.number_input(
        "Productivity target %",
        min_value=1,
        max_value=200,
        value=90,
    )

    quality_target = st.number_input(
        "Quality target %",
        min_value=1,
        max_value=100,
        value=95,
    )

    sla_target = st.number_input(
        "SLA target %",
        min_value=1,
        max_value=100,
        value=97,
    )

    aht_target = st.number_input(
        "AHT target",
        min_value=1,
        max_value=1000,
        value=50,
    )

    st.divider()

    if st.button(
        "💳 View Plans",
        use_container_width=True,
        key="sidebar_view_plans",
    ):
        st.session_state.show_plans = True

    if st.button(
        "🔄 Reset Analysis",
        use_container_width=True,
        key="sidebar_reset_analysis",
    ):
        clear_analysis()
        st.rerun()

    if st.button(
        "🚪 Sign Out",
        use_container_width=True,
        key="sidebar_sign_out",
    ):
        clear_authentication()
        st.rerun()

if st.session_state.get("show_plans"):
    st.divider()
    show_pricing("sidebar")
    st.divider()


# ============================================================
# HEADER
# ============================================================

show_brand_header(compact=True)

st.markdown(
    "## AI Operations Manager",
    unsafe_allow_html=True,
)

st.markdown(
    "Executive operational intelligence → risk detection → "
    "AI decisions → action plans → management reports"
)


# ============================================================
# CUSTOMER INFORMATION
# ============================================================

st.subheader("🏢 Report Setup")

col1, col2, col3 = st.columns(3)

with col1:
    company_name = st.text_input(
        "Company Name",
        value=st.session_state.get("company_name", ""),
        placeholder="e.g. ABC Technologies",
    )

with col2:
    manager_email = st.text_input(
        "Manager Email",
        value=st.session_state.get("user_email", ""),
        placeholder="manager@company.com",
    )

with col3:
    report_name = st.text_input(
        "Report Name",
        value="Daily Operations Report",
    )


# ============================================================
# FILE UPLOAD
# ============================================================

uploaded = st.file_uploader(
    (
        "📁 Upload Excel or CSV operational data — "
        f"max {plan_config['max_mb']} MB"
    ),
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=False,
    key="operations_file_uploader",
)

if not uploaded:
    st.info(
        "Upload operational data to activate the executive dashboard."
    )

    st.markdown("### Required columns")

    st.code(
        "Date, Employee_ID, Employee_Name, Team, Target, "
        "Production, AHT_Actual, AHT_Target, Quality_%, "
        "SLA_%, Attendance, Error_Count, Error_Category"
    )

    st.markdown("### What you get")

    a, b, c, d = st.columns(4)
    a.metric("Risk Detection", "✓")
    b.metric("Employee Risk", "✓")
    c.metric("AI Copilot", "✓")
    d.metric("Management Report", "✓")

    st.stop()


# ============================================================
# FILE SIZE
# ============================================================

file_mb = uploaded.size / (1024 * 1024)

if file_mb > plan_config["max_mb"]:
    st.error(
        f"File is {file_mb:.2f} MB. "
        f"Your {st.session_state.user_plan} plan supports files "
        f"up to {plan_config['max_mb']} MB."
    )
    st.stop()


# ============================================================
# RESET WHEN NEW FILE
# ============================================================

if st.session_state.file_name != uploaded.name:
    st.session_state.file_name = uploaded.name
    st.session_state.n8n_sent = False
    st.session_state.n8n_result = None
    st.session_state.copilot_answer = None
    st.session_state.last_question = ""
    st.session_state.analysis_result = None
    st.session_state.analysis_df = None
    st.session_state.report_pdf = None


# ============================================================
# N8N SETTINGS
# ============================================================

n8n_url = secret("N8N_WEBHOOK_URL")
copilot_url = secret("N8N_COPILOT_WEBHOOK_URL")

if n8n_url and "/webhook-test/" in n8n_url:
    st.warning(
        "⚠️ n8n is configured with a TEST webhook. "
        "For production use, activate the workflow and use "
        "/webhook/operations-upload in Streamlit Secrets."
    )

if copilot_url and "/webhook-test/" in copilot_url:
    st.warning(
        "⚠️ Management Copilot is using an n8n TEST webhook. "
        "Use the production /webhook/management-copilot URL "
        "after activating the workflow."
    )


# ============================================================
# READ FILE — MOBILE SAFE
# ============================================================

try:
    df = read_uploaded_file(uploaded)
    df = clean_dataframe(df)

except Exception as exc:
    st.error(f"❌ Could not read the uploaded file: {exc}")

    st.info(
        "Mobile upload tip: upload a valid .csv, .xlsx, or .xls file. "
        "For Excel, make sure the workbook contains at least one "
        "readable worksheet."
    )

    with st.expander("Technical details"):
        st.code(str(exc), language="text")

    st.stop()


if df.empty:
    st.error(
        "❌ The uploaded file contains no usable rows."
    )
    st.stop()


# ============================================================
# VALIDATE DATA
# ============================================================

required_columns = [
    "Employee_ID",
    "Employee_Name",
    "Team",
    "Target",
    "Production",
    "AHT_Actual",
    "Quality_%",
    "SLA_%",
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    st.error("❌ Required columns are missing.")
    st.write(missing_columns)

    st.info(
        "Column names must match the required format exactly. "
        "Extra columns are allowed."
    )

    st.stop()


# ============================================================
# LOCAL ANALYSIS
# ============================================================

try:
    result = analyze_data(
        df,
        productivity_target=productivity_target,
        quality_target=quality_target,
        sla_target=sla_target,
        aht_target=aht_target,
    )

except Exception as exc:
    st.error(f"❌ Analysis failed: {exc}")

    with st.expander("Technical details"):
        st.code(str(exc), language="text")

    st.stop()

st.session_state.analysis_result = result
st.session_state.analysis_df = df


# ============================================================
# KPI CALCULATIONS
# ============================================================

overall = result["overall"]

productivity = float(overall["productivity"])
quality = float(overall["quality"])
sla = float(overall["sla"])
aht = float(overall["aht"])

productivity_gap = productivity - productivity_target
quality_gap = quality - quality_target
sla_gap = sla - sla_target
aht_gap = aht - aht_target

breaches = sum(
    [
        productivity < productivity_target,
        quality < quality_target,
        sla < sla_target,
        aht > aht_target,
    ]
)

if breaches == 0:
    risk_level = "🟢 LOW RISK"
elif breaches == 1:
    risk_level = "🟡 MEDIUM RISK"
elif breaches == 2:
    risk_level = "🟠 HIGH RISK"
else:
    risk_level = "🔴 CRITICAL RISK"

actions_df = result.get("actions", pd.DataFrame())

action_count = (
    len(actions_df)
    if isinstance(actions_df, pd.DataFrame)
    else 0
)

high_priority_count = 0

if isinstance(actions_df, pd.DataFrame) and not actions_df.empty:
    for col in [
        "Priority",
        "priority",
        "Priority_Level",
        "priority_level",
    ]:
        if col in actions_df.columns:
            high_priority_count = len(
                actions_df[
                    actions_df[col]
                    .astype(str)
                    .str.lower()
                    .isin(["high", "critical"])
                ]
            )
            break


# ============================================================
# EXECUTIVE HERO
# ============================================================

st.markdown(
    f"""
    <div class="hero">
        <div class="main-title">
            Executive Health: {risk_level}
        </div>
        <div class="brand-subtitle">
            {company_name or "Your organization"} · {report_name}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TOP EXECUTIVE METRICS
# ============================================================

r1, r2, r3, r4 = st.columns(4)

with r1:
    st.metric("Operational Risk", risk_level)

with r2:
    st.metric(
        "KPI Breaches",
        breaches,
        delta=f"{4 - breaches} on target",
    )

with r3:
    st.metric("Action Items", action_count)

with r4:
    st.metric("High/Critical Actions", high_priority_count)


# ============================================================
# KPI PERFORMANCE
# ============================================================

st.subheader("📊 KPI Performance vs Target")

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric(
        "Productivity",
        f"{productivity:.2f}%",
        delta=f"{productivity_gap:+.2f}% vs target",
    )

with k2:
    st.metric(
        "Quality",
        f"{quality:.2f}%",
        delta=f"{quality_gap:+.2f}% vs target",
    )

with k3:
    st.metric(
        "SLA",
        f"{sla:.2f}%",
        delta=f"{sla_gap:+.2f}% vs target",
    )

with k4:
    st.metric(
        "Average AHT",
        f"{aht:.2f}",
        delta=f"{aht_gap:+.2f} vs target",
    )


# ============================================================
# EXECUTIVE SUMMARY
# ============================================================

summary_points = [
    f"{'🔴' if productivity < productivity_target else '🟢'} "
    f"Productivity: {productivity:.1f}% vs {productivity_target}% target.",
    f"{'🔴' if quality < quality_target else '🟢'} "
    f"Quality: {quality:.1f}% vs {quality_target}% target.",
    f"{'🔴' if sla < sla_target else '🟢'} "
    f"SLA: {sla:.1f}% vs {sla_target}% target.",
    f"{'🟠' if aht > aht_target else '🟢'} "
    f"AHT: {aht:.1f} vs {aht_target} target.",
]

if breaches >= 3:
    recommendation = (
        "Immediate management attention is recommended. Multiple KPI "
        "thresholds are breached. Prioritize root-cause analysis, "
        "targeted corrective actions, and close monitoring."
    )
elif breaches >= 1:
    recommendation = (
        "Management should review the affected KPIs, validate "
        "contributing factors, and initiate targeted corrective actions."
    )
else:
    recommendation = (
        "Operations are within defined KPI thresholds. Continue "
        "monitoring performance and maintain current processes."
    )

st.subheader("🧠 Executive Summary")

for point in summary_points:
    st.write(point)

st.info(f"💡 **Management Recommendation:** {recommendation}")


# ============================================================
# ALWAYS-VISIBLE MANAGEMENT COPILOT
# FIX: COPILOT IS NO LONGER HIDDEN INSIDE MOBILE TABS
# ============================================================

st.divider()

render_copilot(
    copilot_url,
    plan_config,
    company_name,
    report_name,
    result,
    productivity_target,
    quality_target,
    sla_target,
    aht_target,
    risk_level,
    summary_points,
)


# ============================================================
# N8N OPERATIONAL AUTOMATION
# ============================================================

if n8n_url and not st.session_state.n8n_sent:
    if not company_name.strip() or not manager_email.strip():
        st.warning(
            "Enter Company Name and Manager Email to run "
            "the configured n8n operational automation."
        )
    else:
        try:
            files = {
                "file": (
                    uploaded.name,
                    uploaded.getvalue(),
                    uploaded.type or "application/octet-stream",
                )
            }

            data = {
                "company_name": company_name.strip(),
                "manager_email": manager_email.strip(),
                "report_name": report_name.strip(),
                "user_id": st.session_state.user_id,
                "user_email": st.session_state.user_email,
            }

            with st.spinner("🤖 Running operational automation..."):
                response = requests.post(
                    n8n_url,
                    files=files,
                    data=data,
                    timeout=120,
                )

            if response.status_code < 300:
                st.session_state.n8n_result = normalize_n8n_response(response)
                st.session_state.n8n_sent = True
                st.success("✅ Operational automation completed.")
            else:
                st.error(
                    f"❌ n8n workflow failed: HTTP {response.status_code}"
                )
                if response.text:
                    st.code(response.text[:3000], language="text")

        except requests.exceptions.Timeout:
            st.warning(
                "⏱️ n8n timed out. The workflow may still be running."
            )

        except requests.exceptions.RequestException as exc:
            st.error(f"❌ Could not connect to n8n: {exc}")


# ============================================================
# QUICK MANAGEMENT COPILOT
# ============================================================

st.markdown("## 🤖 Management Copilot")
st.caption(
    "Ask questions about the uploaded operational data. "
    "The Copilot uses the current dashboard context."
)

quick_question = st.text_area(
    "Ask your operational question",
    placeholder=(
        "Example: Which team needs the most attention and "
        "what action should management take?"
    ),
    height=90,
    key="quick_copilot_question",
)

quick_ask = st.button(
    "🚀 Ask Management Copilot",
    type="primary",
    use_container_width=True,
    key="quick_ask_management_copilot",
)

if quick_ask:
    if not quick_question.strip():
        st.warning("Please enter a question first.")
    elif not plan_config["copilot"]:
        st.error("Copilot is not available on your current plan.")
    elif not copilot_url:
        st.error(
            "N8N_COPILOT_WEBHOOK_URL is not configured in "
            "Streamlit Secrets."
        )
    else:
        context = build_copilot_context(
            company_name,
            report_name,
            result,
            productivity_target,
            quality_target,
            sla_target,
            aht_target,
            risk_level,
            summary_points,
        )

        payload = {
            "question": quick_question.strip(),
            "company_name": company_name.strip(),
            "report_name": report_name.strip(),
            "context": context,
            "user_id": st.session_state.user_id,
            "user_email": st.session_state.user_email,
        }

        try:
            with st.spinner("🤖 Management Copilot is analyzing..."):
                response = requests.post(
                    copilot_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=120,
                )

            if response.status_code < 300:
                raw = normalize_n8n_response(response)
                st.session_state.copilot_answer = parse_ai_answer(raw)
                st.session_state.last_question = quick_question.strip()
                st.success("✅ Copilot analysis completed.")
            else:
                st.error(
                    f"❌ Copilot workflow failed: HTTP {response.status_code}"
                )
                st.code(response.text, language="text")

        except requests.exceptions.Timeout:
            st.error("⏱️ Management Copilot timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            st.error("🔌 Could not connect to the n8n Copilot webhook.")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Copilot request failed: {e}")
        except Exception as e:
            st.error(f"❌ Unexpected Copilot error: {e}")

if st.session_state.copilot_answer:
    st.markdown("### 🧠 Copilot Analysis")
    st.caption("Question: " + st.session_state.last_question)

    answer = st.session_state.copilot_answer

    if isinstance(answer, dict):
        what = answer.get("what_is_happening")
        factors = answer.get("contributing_factors", [])
        actions = answer.get("recommended_actions", [])
        priority = answer.get("priority", "")
        owner = answer.get("owner", "")
        timeline = answer.get("timeline", "")
        sufficiency = answer.get("data_sufficiency")

        if what:
            st.info(what)

        if factors:
            st.markdown("#### 🔍 Contributing Factors")
            for factor in factors:
                st.write(f"• {factor}")

        if actions:
            st.markdown("#### ✅ Recommended Actions")
            for i, action in enumerate(actions, 1):
                st.markdown(f"**{i}.** {action}")

        d1, d2, d3 = st.columns(3)
        d1.metric("Priority", priority or "N/A")
        d2.metric("Owner", owner or "N/A")
        d3.metric("Timeline", timeline or "N/A")

        if sufficiency:
            st.warning(sufficiency)

    elif isinstance(answer, str):
        st.markdown(answer)
    else:
        st.code(str(answer), language="text")

st.divider()

# ============================================================
# MAIN TABS
# ============================================================

tabs = st.tabs(
    [
        "📊 Executive Dashboard",
        "🚨 AI Insights",
        "👥 Employee Risk",
        "✅ Action Center",
        "🤖 Management Copilot",
        "📄 Reports",
        "💳 Billing",
    ]
)


# ============================================================
# TAB 1 — EXECUTIVE DASHBOARD
# ============================================================

with tabs[0]:
    left, right = st.columns([1.4, 1])

    with left:
        st.subheader("Team Performance")

        team_df = result.get("team", pd.DataFrame())

        if isinstance(team_df, pd.DataFrame) and not team_df.empty:
            st.dataframe(
                team_df,
                use_container_width=True,
                hide_index=True,
            )

            if (
                "Team" in team_df.columns
                and "Productivity_%" in team_df.columns
            ):
                st.subheader("Productivity by Team")
                st.bar_chart(
                    team_df.set_index("Team")["Productivity_%"]
                )
        else:
            st.info("No team-level data available.")

    with right:
        st.subheader("Management Snapshot")

        employees = result.get("employees", pd.DataFrame())

        if isinstance(employees, pd.DataFrame) and not employees.empty:
            st.metric("Employees analyzed", len(employees))

            if "Risk_Score" in employees.columns:
                st.metric(
                    "Highest employee risk score",
                    f"{employees['Risk_Score'].max():.2f}",
                )

        st.write("**Current KPI position**")

        for item in summary_points:
            st.write(item)


# ============================================================
# TAB 2 — AI INSIGHTS
# ============================================================

with tabs[1]:
    st.subheader("🚨 Automated Findings")

    findings_df = result.get("findings", pd.DataFrame())

    if isinstance(findings_df, pd.DataFrame) and not findings_df.empty:
        st.dataframe(
            findings_df,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("✅ No threshold breaches detected.")

    st.info(
        "Root causes are evidence-based hypotheses. "
        "The available data may not prove causality."
    )


# ============================================================
# TAB 3 — EMPLOYEE RISK
# ============================================================

with tabs[2]:
    st.subheader("👥 Employee Risk")

    employee_data = result.get("employees", pd.DataFrame())

    if isinstance(employee_data, pd.DataFrame) and not employee_data.empty:
        sort_cols = [
            c
            for c in ["Risk_Score", "Avg_Productivity"]
            if c in employee_data.columns
        ]

        if sort_cols:
            employee_data = employee_data.sort_values(
                sort_cols,
                ascending=[False] * len(sort_cols),
            )

        st.dataframe(
            employee_data,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No employee-level risk data available.")


# ============================================================
# TAB 4 — ACTION CENTER
# ============================================================

with tabs[3]:
    st.subheader("✅ Recommended Actions")

    if isinstance(actions_df, pd.DataFrame) and not actions_df.empty:
        st.dataframe(
            actions_df,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No action items generated.")


# ============================================================
# TAB 5 — MANAGEMENT COPILOT
# ============================================================

with tabs[4]:
    st.subheader("🤖 Management Copilot")

    st.info(
        "The Copilot is also available above the tabs so it remains "
        "easy to access on mobile."
    )

    render_copilot(
        copilot_url,
        plan_config,
        company_name,
        report_name,
        result,
        productivity_target,
        quality_target,
        sla_target,
        aht_target,
        risk_level,
        summary_points,
    )


# ============================================================
# TAB 6 — REPORTS
# ============================================================

with tabs[5]:
    st.subheader("📄 Management Reports")

    if not plan_config["pdf"]:
        st.warning(
            "PDF reporting is not available on your current plan."
        )
    else:
        report_result = dict(result)

        report_result["_targets"] = {
            "productivity": productivity_target,
            "quality": quality_target,
            "sla": sla_target,
            "aht": aht_target,
        }

        if st.button(
            "📄 Generate Executive PDF",
            type="primary",
            use_container_width=True,
            key="generate_executive_pdf",
        ):
            try:
                with st.spinner("Generating management report..."):
                    pdf = create_pdf_report(
                        company_name or "Organization",
                        report_name or "Operations Report",
                        report_result,
                        risk_level,
                        summary_points,
                        recommendation,
                    )

                st.session_state.report_pdf = pdf
                st.session_state.report_generated_at = datetime.now()

            except Exception as exc:
                st.error(f"❌ Could not generate PDF: {exc}")

        if st.session_state.report_pdf:
            filename = (
                f"{company_name or 'operations'}_report_"
                f"{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            )

            st.download_button(
                "⬇️ Download Executive PDF",
                data=st.session_state.report_pdf,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
                key="download_executive_pdf",
            )

            if st.session_state.report_generated_at:
                st.caption(
                    "Generated "
                    + st.session_state.report_generated_at.strftime(
                        "%d %b %Y, %H:%M"
                    )
                )

        st.divider()
        st.subheader("📧 Email Report")

        if not plan_config["email"]:
            st.info(
                "Email delivery is available on Professional and Business plans."
            )
        else:
            recipient = st.text_input(
                "Recipient email",
                value=manager_email,
                key="report_recipient",
            )

            if st.button(
                "📨 Email PDF Report",
                use_container_width=True,
                key="email_pdf_report",
            ):
                if not recipient.strip():
                    st.warning("Enter a recipient email address.")
                elif not st.session_state.report_pdf:
                    st.warning("Generate the PDF first.")
                else:
                    try:
                        send_email_report(
                            recipient.strip(),
                            f"{company_name} - {report_name}",
                            (
                                "Please find attached the management report "
                                f"for {company_name or 'your organization'}.\n\n"
                                "Generated by Generative Insight AI Operations Copilot."
                            ),
                            st.session_state.report_pdf,
                            "operations_report.pdf",
                        )

                        st.success("✅ Report emailed successfully.")

                    except Exception as exc:
                        st.error(f"❌ Email failed: {exc}")

        st.divider()
        st.subheader("📥 Data Exports")

        e1, e2 = st.columns(2)

        with e1:
            team_df = result.get("team", pd.DataFrame())

            if isinstance(team_df, pd.DataFrame):
                st.download_button(
                    "⬇️ Team Analysis CSV",
                    team_df.to_csv(index=False).encode("utf-8"),
                    "team_analysis.csv",
                    "text/csv",
                    use_container_width=True,
                    key="download_team_analysis",
                )

        with e2:
            if isinstance(actions_df, pd.DataFrame):
                st.download_button(
                    "⬇️ Action Plan CSV",
                    actions_df.to_csv(index=False).encode("utf-8"),
                    "action_plan.csv",
                    "text/csv",
                    use_container_width=True,
                    key="download_action_plan",
                )


# ============================================================
# TAB 7 — BILLING
# ============================================================

with tabs[6]:
    st.subheader("💳 Subscription & Billing")

    st.info(
        f"You are currently using the **{st.session_state.user_plan}** plan."
    )

    show_pricing("billing")

    st.caption(
        "To activate real paid checkout, configure the plan checkout "
        "URLs in Streamlit Secrets using your payment provider."
    )


# ============================================================
# AI PROMPT / DEBUG AREA
# ============================================================

with st.expander("🧠 AI Analyst Context / Prompt", expanded=False):
    st.code(
        make_ai_prompt(result),
        language="text",
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    f"""
    <div style="text-align:center;color:#667085;padding:10px;">
        <b>Generative Insight</b>
        · AI Operations Copilot v{APP_VERSION}<br/>
        Insights today. Intelligence tomorrow.<br/>
        <a href="{WEBSITE_URL}" target="_blank">
            generativeinsight.in
        </a>
        &nbsp;·&nbsp;
        © {datetime.now().year}
    </div>
    """,
    unsafe_allow_html=True,
)
