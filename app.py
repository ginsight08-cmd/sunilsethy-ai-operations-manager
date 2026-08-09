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
# Complete Streamlit application
# ============================================================

APP_NAME = "Generative Insight"
APP_VERSION = "1.0.0"

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

# Add your logo here:
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
    "razorpay_checkout_url": "",
    "razorpay_subscription_id": "",
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# BRAND THEME
# ============================================================

st.markdown(
    f"""
<style>

    .stApp {{
        background:
            radial-gradient(
                circle at 85% 0%,
                rgba(0,174,239,0.08),
                transparent 30%
            ),
            linear-gradient(
                180deg,
                #FFFFFF 0%,
                #F7FAFF 100%
            );
    }}

    .main {{
        padding-top: 1.5rem;
    }}

    .main-title {{
        font-size: 2.35rem;
        font-weight: 850;
        color: {BRAND_NAVY};
        margin-bottom: 0.15rem;
        letter-spacing: -1px;
    }}

    .brand-subtitle {{
        color: #667085;
        font-size: 1.02rem;
        margin-bottom: 1rem;
    }}

    .gi-brand {{
        font-size: 1.45rem;
        font-weight: 800;
        color: {BRAND_NAVY};
        letter-spacing: -0.5px;
    }}

    .gi-brand span {{
        color: {BRAND_BLUE};
    }}

    .gi-tagline {{
        color: #667085;
        font-size: 0.82rem;
        margin-top: 0.15rem;
    }}

    .hero {{
        padding: 1.45rem 1.6rem;
        border-radius: 20px;
        border: 1px solid #DCE8F8;
        background:
            linear-gradient(
                135deg,
                rgba(7,87,184,0.08),
                rgba(0,174,239,0.04),
                rgba(255,157,0,0.05)
            );
        box-shadow: 0 8px 30px rgba(7,87,184,0.06);
        margin-bottom: 1.2rem;
    }}

    .small-muted {{
        color: #667085;
        font-size: .88rem;
    }}

    div[data-testid="stMetric"] {{
        background: #FFFFFF;
        border: 1px solid #E0E8F5;
        border-radius: 16px;
        padding: 0.8rem;
        box-shadow: 0 4px 15px rgba(7,87,184,0.05);
    }}

    div[data-testid="stMetricValue"] {{
        color: {BRAND_NAVY};
        font-weight: 800;
    }}

    .plan-card {{
        padding: 1.25rem;
        border-radius: 18px;
        border: 1px solid #DDE7F5;
        background: #FFFFFF;
        min-height: 260px;
        box-shadow: 0 8px 24px rgba(7,87,184,0.06);
        color: #172033 !important;
        transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }}

    .plan-card:hover {{
        border-color: {BRAND_CYAN};
        box-shadow: 0 10px 30px rgba(0,174,239,0.12);
        transform: translateY(-3px);
    }}

    section[data-testid="stSidebar"] {{
        background:
            linear-gradient(
                180deg,
                #F5F9FF 0%,
                #FFFFFF 100%
            );
        border-right: 1px solid #E0E8F5;
    }}

    .stButton > button {{
        border-radius: 10px;
        font-weight: 700;
        border: 1px solid #C9D8EE;
    }}

    .stButton > button[kind="primary"] {{
        background: linear-gradient(
            90deg,
            {BRAND_BLUE},
            {BRAND_CYAN}
        );
        color: white;
        border: none;
    }}

    .stButton > button[kind="primary"]:hover {{
        background: linear-gradient(
            90deg,
            #064A9D,
            #009BD5
        );
        color: white;
    }}

    button[data-baseweb="tab"] {{
        font-weight: 700;
    }}

    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {BRAND_BLUE};
    }}

    a {{
        color: {BRAND_BLUE};
    }}

    .gi-footer {{
        text-align: center;
        color: #667085;
        font-size: 0.82rem;
        padding: 1.5rem 0;
    }}


    /* EMBED-SAFE TYPOGRAPHY: explicit dark text prevents host-page CSS
       from making Streamlit content white/invisible inside an iframe. */
    .stApp .stMarkdown, .stApp .stMarkdown p, .stApp .stMarkdown li,
    .stApp .stMarkdown span, .stApp label,
    .stApp [data-testid="stWidgetLabel"], .stApp [data-testid="stWidgetLabel"] * {{
        color: #172033 !important;
    }}
    .stApp .stCaption, .stApp [data-testid="stCaptionContainer"],
    .stApp [data-testid="stCaptionContainer"] * {{
        color: #52637A !important;
    }}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
        color: #071A3D !important;
    }}
    .stApp input, .stApp textarea, .stApp select,
    .stApp input::placeholder, .stApp textarea::placeholder {{
        color: #172033 !important;
        -webkit-text-fill-color: #172033 !important;
        opacity: 1 !important;
    }}
    .stApp [data-baseweb="select"] * {{
        color: #172033 !important;
    }}
    .stApp button[data-baseweb="tab"] {{
        color: #334155 !important;
    }}
    .stApp button[data-baseweb="tab"][aria-selected="true"] {{
        color: #0757B8 !important;
    }}
    .stApp [data-testid="stDataFrame"] *,
    .stApp [data-testid="stTable"] * {{
        color: #172033 !important;
    }}
    .plan-card, .plan-card * {{
        color: #172033 !important;
    }}
    .plan-card .plan-name, .plan-card .plan-price {{
        color: #071A3D !important;
    }}
    .plan-card .plan-description, .plan-card .plan-feature {{
        color: #52637A !important;
    }}
    .plan-card .plan-feature {{
        font-weight: 600 !important;
    }}
    .stApp a {{
        color: #0757B8 !important;
        text-decoration: none;
    }}
    .stApp a:hover {{
        color: #003F8F !important;
        text-decoration: underline;
    }}

    /* ========================================================
       HARD EMBED CONTRAST FIX
       Explicitly style Streamlit-generated content and the
       custom HTML blocks. This prevents invisible text when
       the app is embedded inside a website/iframe.
       ======================================================== */
    .stApp [data-testid="stMarkdownContainer"],
    .stApp [data-testid="stMarkdownContainer"] p,
    .stApp [data-testid="stMarkdownContainer"] div,
    .stApp [data-testid="stMarkdownContainer"] span,
    .stApp [data-testid="stMarkdownContainer"] li,
    .stApp [data-testid="stMarkdownContainer"] strong,
    .stApp [data-testid="stMarkdownContainer"] em {{
        color: #172033 !important;
        opacity: 1 !important;
        visibility: visible !important;
        -webkit-text-fill-color: #172033 !important;
    }}

    .stApp [data-testid="stMarkdownContainer"] h1,
    .stApp [data-testid="stMarkdownContainer"] h2,
    .stApp [data-testid="stMarkdownContainer"] h3,
    .stApp [data-testid="stMarkdownContainer"] h4,
    .stApp [data-testid="stMarkdownContainer"] h5,
    .stApp [data-testid="stMarkdownContainer"] h6 {{
        color: #071A3D !important;
        opacity: 1 !important;
        visibility: visible !important;
        -webkit-text-fill-color: #071A3D !important;
    }}

    .stApp .hero p {{
        color: #475569 !important;
        opacity: 1 !important;
        visibility: visible !important;
        -webkit-text-fill-color: #475569 !important;
        font-size: 0.98rem !important;
        line-height: 1.65 !important;
    }}

    .stApp .hero .brand-subtitle {{
        color: #0757B8 !important;
        opacity: 1 !important;
        -webkit-text-fill-color: #0757B8 !important;
    }}

    /* Tabs: force both selected and unselected labels to remain visible. */
    .stApp [data-baseweb="tab-list"] {{
        background: transparent !important;
    }}
    .stApp button[data-baseweb="tab"],
    .stApp button[data-baseweb="tab"] span,
    .stApp button[data-baseweb="tab"] div {{
        color: #334155 !important;
        opacity: 1 !important;
        visibility: visible !important;
        -webkit-text-fill-color: #334155 !important;
        font-weight: 700 !important;
    }}
    .stApp button[data-baseweb="tab"][aria-selected="true"],
    .stApp button[data-baseweb="tab"][aria-selected="true"] span,
    .stApp button[data-baseweb="tab"][aria-selected="true"] div {{
        color: #0757B8 !important;
        -webkit-text-fill-color: #0757B8 !important;
    }}

    /* Streamlit headings/captions outside markdown containers. */
    .stApp [data-testid="stHeader"] *,
    .stApp [data-testid="stText"],
    .stApp [data-testid="stCaptionContainer"] *,
    .stApp [data-testid="stWidgetLabel"] *,
    .stApp [data-testid="stForm"] label,
    .stApp [data-testid="stForm"] p {{
        opacity: 1 !important;
        visibility: visible !important;
    }}

    .stApp [data-testid="stCaptionContainer"] *,
    .stApp .stCaption {{
        color: #52637A !important;
        -webkit-text-fill-color: #52637A !important;
    }}

    /* Inputs and buttons in an embedded page. */
    .stApp input,
    .stApp textarea,
    .stApp [role="textbox"],
    .stApp [data-baseweb="input"] input,
    .stApp [data-baseweb="textarea"] textarea {{
        background-color: #FFFFFF !important;
        color: #172033 !important;
        -webkit-text-fill-color: #172033 !important;
        opacity: 1 !important;
    }}

    .stApp input::placeholder,
    .stApp textarea::placeholder {{
        color: #64748B !important;
        -webkit-text-fill-color: #64748B !important;
        opacity: 1 !important;
    }}

    .stApp .stButton button,
    .stApp [data-testid="stFormSubmitButton"] button,
    .stApp [data-testid="stLinkButton"] a {{
        opacity: 1 !important;
        visibility: visible !important;
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
        return st.secrets.get(name, default)
    except Exception:
        return default


def show_brand_header(compact=False):
    """Display the Generative Insight logo and website branding."""

    if LOGO_PATH.exists():
        st.image(
            str(LOGO_PATH),
            width=230 if compact else 420,
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
    """Create the Supabase client from Streamlit Secrets."""
    url = secret("SUPABASE_URL")
    anon_key = secret("SUPABASE_ANON_KEY")

    if not url or not anon_key:
        raise RuntimeError(
            "Supabase authentication is not configured. "
            "Add SUPABASE_URL and SUPABASE_ANON_KEY to Streamlit Secrets."
        )

    return create_client(url, anon_key)


def get_supabase_admin_client() -> Client:
    url = secret("SUPABASE_URL")
    service_role_key = secret("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not service_role_key:
        raise RuntimeError("Add SUPABASE_SERVICE_ROLE_KEY to Streamlit Secrets for secure plan activation.")
    return create_client(url, service_role_key)


def update_user_plan(plan, subscription_id="", razorpay_status=""):
    if not st.session_state.get("user_id"):
        raise RuntimeError("No authenticated user is available.")
    admin = get_supabase_admin_client()
    current = admin.auth.admin.get_user_by_id(st.session_state.user_id)
    user = getattr(current, "user", None)
    metadata = dict(getattr(user, "user_metadata", {}) or {}) if user else {}
    metadata.update({
        "plan": plan,
        "razorpay_subscription_id": subscription_id or metadata.get("razorpay_subscription_id", ""),
        "razorpay_subscription_status": razorpay_status or metadata.get("razorpay_subscription_status", ""),
        "plan_updated_at": datetime.utcnow().isoformat() + "Z",
    })
    admin.auth.admin.update_user_by_id(st.session_state.user_id, {"user_metadata": metadata})
    st.session_state.user_plan = plan
    st.session_state.razorpay_subscription_id = metadata.get("razorpay_subscription_id", "")


def get_razorpay_subscription(subscription_id):
    key_id, key_secret = secret("RAZORPAY_KEY_ID"), secret("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise RuntimeError("Razorpay credentials are not configured.")
    if not subscription_id:
        raise RuntimeError("No Razorpay subscription ID is available.")
    try:
        response = requests.get(f"{RAZORPAY_API_BASE}/subscriptions/{subscription_id}", auth=(key_id, key_secret), timeout=30)
    except requests.exceptions.Timeout as exc:
        raise RuntimeError("Razorpay verification timed out. Please try again.") from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Could not connect to Razorpay: {exc}") from exc
    try:
        data = response.json()
    except ValueError:
        data = {"error": response.text}
    if response.status_code >= 300:
        error = data.get("error", data) if isinstance(data, dict) else data
        if isinstance(error, dict):
            error = error.get("description") or error.get("reason") or str(error)
        raise RuntimeError(f"Razorpay verification failed (HTTP {response.status_code}): {error}")
    return data


def verify_professional_subscription():
    subscription_id = st.session_state.get("razorpay_subscription_id", "")
    if not subscription_id:
        admin = get_supabase_admin_client()
        current = admin.auth.admin.get_user_by_id(st.session_state.user_id)
        user = getattr(current, "user", None)
        metadata = getattr(user, "user_metadata", {}) or {} if user else {}
        subscription_id = metadata.get("razorpay_subscription_id", "")
    data = get_razorpay_subscription(subscription_id)
    status = str(data.get("status", "")).lower()
    if status == "active":
        update_user_plan("Professional", subscription_id, status)
        return True, status
    update_user_plan("Free", subscription_id, status)
    return False, status


def friendly_auth_error(error) -> str:
    """Convert Supabase auth errors into user-friendly messages."""
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
    """Create a persistent customer account in Supabase Auth."""
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
    """Authenticate a customer using Supabase Auth."""
    supabase = get_supabase_client()

    return supabase.auth.sign_in_with_password(
        {
            "email": email.strip().lower(),
            "password": password,
        }
    )


def sign_out_user():
    """Sign the current user out of Supabase."""
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()
    except Exception:
        pass


def set_authenticated_user(response):
    """Copy authenticated Supabase user information into session state."""
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
    st.session_state.razorpay_subscription_id = metadata.get("razorpay_subscription_id", "")


def clear_authentication():
    sign_out_user()

    st.session_state.authenticated = False
    st.session_state.user_email = ""
    st.session_state.user_id = ""
    st.session_state.user_name = ""
    st.session_state.company_name = ""
    st.session_state.user_plan = "Free"
    st.session_state.show_plans = False
    st.session_state.razorpay_checkout_url = ""
    st.session_state.razorpay_subscription_id = ""

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


def normalize_n8n_response(response):
    try:
        data = response.json()
    except ValueError:
        return {"answer": response.text}

    if isinstance(data, list) and data:
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
            text = text[3:].strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()
            if text.endswith("```"):
                text = text[:-3].strip()

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
        from reportlab.lib.styles import (
            getSampleStyleSheet,
            ParagraphStyle,
        )
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
            "PDF generation requires reportlab. "
            "Add reportlab to requirements.txt."
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

    story = []

    story.append(Paragraph("Generative Insight", title_style))
    story.append(
        Paragraph(
            f"<b>{company_name}</b> — {report_name}<br/>"
            f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}",
            body_style,
        )
    )

    story.append(Spacer(1, 8))

    overall = result["overall"]

    kpi_rows = [
        ["KPI", "Actual", "Target"],
        [
            "Productivity",
            f'{float(overall["productivity"]):.2f}%',
            f'{result.get("_targets", {}).get("productivity", "")}%',
        ],
        [
            "Quality",
            f'{float(overall["quality"]):.2f}%',
            f'{result.get("_targets", {}).get("quality", "")}%',
        ],
        [
            "SLA",
            f'{float(overall["sla"]):.2f}%',
            f'{result.get("_targets", {}).get("sla", "")}%',
        ],
        [
            "Average AHT",
            f'{float(overall["aht"]):.2f}',
            f'{result.get("_targets", {}).get("aht", "")}',
        ],
    ]

    story.append(
        Paragraph("Executive Overview", heading_style)
    )

    story.append(
        Paragraph(
            f"<b>Risk:</b> {risk_level}",
            body_style,
        )
    )

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

    story.append(
        Paragraph("KPI Summary", heading_style)
    )

    for item in summary_points:
        cleaned = (
            item.replace("🔴 ", "")
            .replace("🟢 ", "")
            .replace("🟠 ", "")
            .replace("🟡 ", "")
        )
        story.append(
            Paragraph(cleaned, body_style)
        )

    story.append(
        Paragraph("Management Recommendation", heading_style)
    )

    story.append(
        Paragraph(
            recommendation,
            body_style,
        )
    )

    for title, key in [
        ("Team Performance", "team"),
        ("Operational Findings", "findings"),
        ("Recommended Actions", "actions"),
        ("Employee Risk", "employees"),
    ]:
        df = result.get(key)

        if isinstance(df, pd.DataFrame) and not df.empty:
            story.append(
                Paragraph(title, heading_style)
            )

            pdf_df = df.copy()

            if len(pdf_df.columns) > 8:
                pdf_df = pdf_df.iloc[:, :8]

            headers = [str(c) for c in pdf_df.columns]
            rows = [headers]

            for _, row in pdf_df.head(50).iterrows():
                rows.append(
                    [str(v)[:90] for v in row.tolist()]
                )

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
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor("#111827"),
                        ),
                        (
                            "TEXTCOLOR",
                            (0, 0),
                            (-1, 0),
                            colors.white,
                        ),
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.25,
                            colors.grey,
                        ),
                        (
                            "FONTSIZE",
                            (0, 0),
                            (-1, -1),
                            6,
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "TOP",
                        ),
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

    if not all(
        [smtp_host, smtp_user, smtp_password, smtp_from]
    ):
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

    with smtplib.SMTP(
        smtp_host,
        smtp_port,
        timeout=30,
    ) as server:
        server.starttls()
        server.login(
            smtp_user,
            smtp_password,
        )
        server.send_message(message)


# ============================================================
# RAZORPAY SUBSCRIPTIONS
# ============================================================

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


def razorpay_is_configured():
    return all(
        [
            secret("RAZORPAY_KEY_ID"),
            secret("RAZORPAY_KEY_SECRET"),
            secret("RAZORPAY_PROFESSIONAL_PLAN_ID"),
        ]
    )


def create_razorpay_subscription(customer_email="", customer_name=""):
    key_id = secret("RAZORPAY_KEY_ID")
    key_secret = secret("RAZORPAY_KEY_SECRET")
    plan_id = secret("RAZORPAY_PROFESSIONAL_PLAN_ID")

    if not key_id or not key_secret or not plan_id:
        raise RuntimeError(
            "Razorpay is not configured. Add RAZORPAY_KEY_ID, "
            "RAZORPAY_KEY_SECRET and RAZORPAY_PROFESSIONAL_PLAN_ID "
            "to Streamlit Secrets."
        )

    raw_total_count = secret("RAZORPAY_PROFESSIONAL_TOTAL_COUNT", "12")
    try:
        total_count = int(raw_total_count)
    except (TypeError, ValueError):
        total_count = 12

    if total_count < 1:
        total_count = 12

    payload = {
        "plan_id": plan_id,
        "total_count": total_count,
        "customer_notify": 1,
        "notes": {
            "application": APP_NAME,
            "plan": "Professional",
            "customer_email": str(customer_email or "")[:255],
            "customer_name": str(customer_name or "")[:255],
        },
    }

    try:
        response = requests.post(
            f"{RAZORPAY_API_BASE}/subscriptions",
            auth=(key_id, key_secret),
            json=payload,
            timeout=30,
        )
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            "Razorpay request timed out. Please try again."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"Could not connect to Razorpay: {exc}"
        ) from exc

    try:
        data = response.json()
    except ValueError:
        data = {"error": response.text}

    if response.status_code >= 300:
        error_message = data.get("error", data) if isinstance(data, dict) else data
        if isinstance(error_message, dict):
            error_message = (
                error_message.get("description")
                or error_message.get("reason")
                or str(error_message)
            )
        raise RuntimeError(
            f"Razorpay subscription creation failed (HTTP {response.status_code}): "
            f"{error_message}"
        )

    checkout_url = data.get("short_url")
    subscription_id = data.get("id")

    if not checkout_url or not subscription_id:
        raise RuntimeError(
            "Razorpay created the subscription but did not return a valid "
            "subscription checkout URL."
        )

    return {
        "id": subscription_id,
        "status": data.get("status", "created"),
        "short_url": checkout_url,
        "plan_id": data.get("plan_id", plan_id),
    }


# ============================================================
# PRICING
# ============================================================

def show_pricing(section_id="default"):
    """Display the existing pricing UI with Razorpay Professional checkout."""

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
            (
                "Current plan"
                if st.session_state.user_plan == "Free"
                else "Start Free"
            ),
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
            "Current plan"
            if st.session_state.user_plan == "Professional"
            else "Upgrade",
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
            plan_visuals = {
                "Free": ("🌱", "Start your AI operations journey"),
                "Professional": ("🚀", "Advanced intelligence & automation"),
                "Business": ("🏢", "Scale AI operations across teams"),
            }
            icon, description = plan_visuals.get(name, ("✨", "Operational intelligence"))

            st.markdown(
                f'''
                <div class="plan-card">
                    <div style="font-size:2.6rem; line-height:1; margin-bottom:.7rem;">{icon}</div>
                    <div class="plan-name" style="font-size:1.15rem; font-weight:800;">{name}</div>
                    <div class="plan-price" style="font-size:1.65rem; font-weight:850; margin:.35rem 0;">{price}</div>
                    <div class="plan-description" style="font-size:.86rem; margin-bottom:.8rem;">{description}</div>
                    {''.join(f'<div class="plan-feature" style="margin:.35rem 0;">✓ {feature}</div>' for feature in features)}
                </div>
                '''
                , unsafe_allow_html=True,
            )

            # Professional uses the Razorpay subscription API.
            # Free/Business retain the existing checkout-link behavior.
            if name == "Professional":
                if st.session_state.user_plan == "Professional":
                    st.button(
                        "Current plan",
                        use_container_width=True,
                        disabled=True,
                        key=f"professional_current_{section_id}",
                    )
                elif not razorpay_is_configured():
                    st.button(
                        "Upgrade",
                        use_container_width=True,
                        disabled=True,
                        key=f"professional_disabled_{section_id}",
                    )
                    st.caption(
                        "Razorpay checkout is not configured yet."
                    )
                else:
                    # Keep the payment option visible in every environment.
                    # Secure activation still requires an authenticated Supabase user.
                    if st.button(
                        "💳 Upgrade to Professional",
                        type="primary",
                        use_container_width=True,
                        key=f"razorpay_upgrade_{section_id}",
                    ):
                        if not st.session_state.get("authenticated") or not st.session_state.get("user_id"):
                            st.warning("Please create an account or sign in before starting a Professional subscription.")
                        else:
                            try:
                                with st.spinner("Creating secure Razorpay subscription..."):
                                    subscription = create_razorpay_subscription(
                                        customer_email=st.session_state.get("user_email", ""),
                                        customer_name=st.session_state.get("user_name", ""),
                                    )

                                st.session_state.razorpay_checkout_url = subscription["short_url"]
                                st.session_state.razorpay_subscription_id = subscription["id"]

                                # Store the subscription ID/status against the authenticated
                                # Supabase user. The service-role key is only used server-side.
                                try:
                                    update_user_plan(
                                        st.session_state.get("user_plan", "Free"),
                                        subscription["id"],
                                        subscription.get("status", "created"),
                                    )
                                except Exception as exc:
                                    st.warning(
                                        "Checkout was created, but subscription tracking could not be saved: "
                                        f"{exc}"
                                    )

                                st.success("Subscription created. Continue to secure Razorpay checkout.")
                            except Exception as exc:
                                st.error(f"❌ {exc}")

                if st.session_state.get("razorpay_checkout_url"):
                    st.link_button(
                        "💳 Continue to Razorpay Checkout",
                        st.session_state.razorpay_checkout_url,
                        use_container_width=True,
                    )
                    subscription_id = st.session_state.get(
                        "razorpay_subscription_id", ""
                    )
                    if subscription_id:
                        st.caption(f"Subscription ID: {subscription_id}")
                        if st.button("🔄 Verify Professional Payment", use_container_width=True, key=f"verify_razorpay_{section_id}"):
                            try:
                                with st.spinner("Verifying your Razorpay subscription..."):
                                    active, status = verify_professional_subscription()
                                if active:
                                    st.success("✅ Payment verified. Professional plan activated.")
                                    st.session_state.razorpay_checkout_url = ""
                                    st.rerun()
                                else:
                                    st.info(f"Payment is not active yet. Razorpay status: {status or 'unknown'}. Complete checkout and try again.")
                            except Exception as exc:
                                st.error(f"❌ Verification failed: {exc}")
            else:
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

    if (
        not secret("SUPABASE_URL")
        or not secret("SUPABASE_ANON_KEY")
    ):
        st.error(
            "🔐 Authentication is not configured yet. "
            "Add SUPABASE_URL and SUPABASE_ANON_KEY in "
            "Streamlit → App Settings → Secrets."
        )
        st.stop()

    signup_tab, login_tab, pricing_tab = st.tabs(
        [
            "🆕 Create Account",
            "🔐 Sign In",
            "💳 Plans",
        ]
    )

    # --------------------------------------------------------
    # SIGN UP
    # --------------------------------------------------------

    with signup_tab:

        st.markdown(
            "### Create your Generative Insight account"
        )

        st.caption(
            "Start with the Free plan. You can upgrade later."
        )

        with st.form(
            "signup_form",
            clear_on_submit=False,
        ):

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
                help=(
                    "Use a strong password. Supabase enforces "
                    "the configured password policy."
                ),
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
                st.warning(
                    "Please enter your full name."
                )

            elif not signup_company.strip():
                st.warning(
                    "Please enter your company or organization."
                )

            elif (
                not signup_email.strip()
                or "@" not in signup_email
            ):
                st.warning(
                    "Please enter a valid email address."
                )

            elif len(signup_password) < 6:
                st.warning(
                    "Please use a password with at least 6 characters."
                )

            elif signup_password != signup_confirm:
                st.warning(
                    "Passwords do not match."
                )

            else:

                try:

                    with st.spinner(
                        "Creating your account..."
                    ):

                        signup_response = sign_up_user(
                            signup_name,
                            signup_company,
                            signup_email,
                            signup_password,
                        )

                    signup_user = getattr(
                        signup_response,
                        "user",
                        None,
                    )

                    signup_session = getattr(
                        signup_response,
                        "session",
                        None,
                    )

                    if (
                        signup_user is not None
                        and signup_session is not None
                    ):

                        set_authenticated_user(
                            signup_response
                        )

                        st.success(
                            "✅ Account created successfully."
                        )

                        st.rerun()

                    elif signup_user is not None:

                        st.success(
                            "✅ Account created. Please check your "
                            "email and click the verification link "
                            "before signing in."
                        )

                    else:

                        st.info(
                            "If the email is valid, check your inbox "
                            "for the verification email."
                        )

                except Exception as e:

                    st.error(
                        "❌ Could not create account: "
                        + friendly_auth_error(e)
                    )

        st.caption(
            "By creating an account, you agree to use the platform "
            "responsibly and validate AI recommendations before "
            "taking material business action."
        )

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

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

            if (
                not login_email.strip()
                or not login_password
            ):

                st.warning(
                    "Please enter your email and password."
                )

            else:

                try:

                    with st.spinner(
                        "Signing you in..."
                    ):

                        login_response = sign_in_user(
                            login_email,
                            login_password,
                        )

                    set_authenticated_user(
                        login_response
                    )

                    st.success(
                        "✅ Signed in successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "❌ Sign in failed: "
                        + friendly_auth_error(e)
                    )

        st.info(
            "If email confirmation is enabled in Supabase, "
            "verify your email before signing in."
        )

    # --------------------------------------------------------
    # PRICING ON LOGIN PAGE
    # --------------------------------------------------------

    with pricing_tab:
        show_pricing("login")

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

plan_config = get_plan_config(
    st.session_state.user_plan
)

with st.sidebar:

    if LOGO_PATH.exists():

        st.image(
            str(LOGO_PATH),
            use_container_width=True,
        )

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

    st.success(
        f"Plan: **{st.session_state.user_plan}**"
    )

    if st.session_state.get("user_name"):
        st.caption(
            st.session_state.user_name
        )

    st.caption(
        st.session_state.user_email
    )

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
    '<div class="main-title">AI Operations Manager</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="brand-subtitle">'
    "Executive operational intelligence → risk detection → "
    "AI decisions → action plans → management reports"
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# CUSTOMER INFORMATION
# ============================================================

st.subheader("🏢 Report Setup")

col1, col2, col3 = st.columns(3)

with col1:

    company_name = st.text_input(
        "Company Name",
        value=st.session_state.get(
            "company_name",
            "",
        ),
        placeholder="e.g. ABC Technologies",
    )

with col2:

    manager_email = st.text_input(
        "Manager Email",
        value=st.session_state.get(
            "user_email",
            "",
        ),
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
)

if not uploaded:

    st.info(
        "Upload operational data to activate the "
        "executive dashboard."
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
        f"Your {st.session_state.user_plan} plan supports "
        f"files up to {plan_config['max_mb']} MB."
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

n8n_url = secret(
    "N8N_WEBHOOK_URL"
)

copilot_url = secret(
    "N8N_COPILOT_WEBHOOK_URL"
)

if n8n_url and "/webhook-test/" in n8n_url:

    st.warning(
        "⚠️ n8n is configured with a TEST webhook. "
        "For production use, activate the workflow and use "
        "/webhook/operations-upload in Streamlit Secrets."
    )

if (
    copilot_url
    and "/webhook-test/" in copilot_url
):

    st.warning(
        "⚠️ Management Copilot is using an n8n TEST webhook. "
        "Use the production /webhook/management-copilot URL "
        "after activating the workflow."
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
            sheet_name=sheet,
        )

except Exception as e:

    st.error(
        f"❌ Could not read the uploaded file: {e}"
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
    col
    for col in required_columns
    if col not in df.columns
]

if missing_columns:

    st.error(
        "❌ Required columns are missing."
    )

    st.write(missing_columns)

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

except Exception as e:

    st.error(
        f"❌ Analysis failed: {e}"
    )

    st.stop()

st.session_state.analysis_result = result
st.session_state.analysis_df = df


# ============================================================
# KPI CALCULATIONS
# ============================================================

overall = result["overall"]

productivity = float(
    overall["productivity"]
)

quality = float(
    overall["quality"]
)

sla = float(
    overall["sla"]
)

aht = float(
    overall["aht"]
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


actions_df = result.get(
    "actions",
    pd.DataFrame(),
)

action_count = (
    len(actions_df)
    if isinstance(actions_df, pd.DataFrame)
    else 0
)

high_priority_count = 0

if (
    isinstance(actions_df, pd.DataFrame)
    and not actions_df.empty
):

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
                    .isin(
                        [
                            "high",
                            "critical",
                        ]
                    )
                ]
            )

            break


# ============================================================
# EXECUTIVE HERO
# ============================================================

st.markdown(
    f"""
    <div class="hero">
        <h3>Executive Health: {risk_level}</h3>
        <p class="small-muted">
        {company_name or "Your organization"} · {report_name}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TOP EXECUTIVE METRICS
# ============================================================

r1, r2, r3, r4 = st.columns(4)

with r1:

    st.metric(
        "Operational Risk",
        risk_level,
    )

with r2:

    st.metric(
        "KPI Breaches",
        breaches,
        delta=f"{4 - breaches} on target",
    )

with r3:

    st.metric(
        "Action Items",
        action_count,
    )

with r4:

    st.metric(
        "High/Critical Actions",
        high_priority_count,
    )


# ============================================================
# KPI PERFORMANCE
# ============================================================

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
        ),
    )

with k2:

    st.metric(
        "Quality",
        f"{quality:.2f}%",
        delta=(
            f"{quality_gap:+.2f}% vs target"
        ),
    )

with k3:

    st.metric(
        "SLA",
        f"{sla:.2f}%",
        delta=(
            f"{sla_gap:+.2f}% vs target"
        ),
    )

with k4:

    st.metric(
        "Average AHT",
        f"{aht:.2f}",
        delta=(
            f"{aht_gap:+.2f} vs target"
        ),
    )


# ============================================================
# EXECUTIVE SUMMARY
# ============================================================

summary_points = []

summary_points.append(
    f"{'🔴' if productivity < productivity_target else '🟢'} "
    f"Productivity: {productivity:.1f}% vs "
    f"{productivity_target}% target."
)

summary_points.append(
    f"{'🔴' if quality < quality_target else '🟢'} "
    f"Quality: {quality:.1f}% vs "
    f"{quality_target}% target."
)

summary_points.append(
    f"{'🔴' if sla < sla_target else '🟢'} "
    f"SLA: {sla:.1f}% vs "
    f"{sla_target}% target."
)

summary_points.append(
    f"{'🟠' if aht > aht_target else '🟢'} "
    f"AHT: {aht:.1f} vs "
    f"{aht_target} target."
)

if breaches >= 3:

    recommendation = (
        "Immediate management attention is recommended. "
        "Multiple KPI thresholds are breached. Prioritize "
        "root-cause analysis, targeted corrective actions, "
        "and close monitoring."
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

st.info(
    f"💡 **Management Recommendation:** {recommendation}"
)


# ============================================================
# N8N OPERATIONAL AUTOMATION
# ============================================================

if n8n_url and not st.session_state.n8n_sent:

    if (
        not company_name.strip()
        or not manager_email.strip()
    ):

        st.warning(
            "Enter Company Name and Manager Email to run "
            "the configured n8n operational automation."
        )

    else:

        try:

            uploaded.seek(0)

            files = {
                "file": (
                    uploaded.name,
                    uploaded.getvalue(),
                    uploaded.type
                    or "application/octet-stream",
                )
            }

            data = {
                "company_name": company_name.strip(),
                "manager_email": manager_email.strip(),
                "report_name": report_name.strip(),
                "user_id": st.session_state.user_id,
                "user_email": st.session_state.user_email,
            }

            with st.spinner(
                "🤖 Running operational automation..."
            ):

                response = requests.post(
                    n8n_url,
                    files=files,
                    data=data,
                    timeout=120,
                )

            if response.status_code < 300:

                st.session_state.n8n_result = (
                    normalize_n8n_response(response)
                )

                st.session_state.n8n_sent = True

                st.success(
                    "✅ Operational automation completed."
                )

            else:

                st.error(
                    f"❌ n8n workflow failed: "
                    f"HTTP {response.status_code}"
                )

                st.code(
                    response.text,
                    language="text",
                )

        except requests.exceptions.Timeout:

            st.warning(
                "⏱️ n8n timed out. The workflow may still be running."
            )

        except requests.exceptions.RequestException as e:

            st.error(
                f"❌ Could not connect to n8n: {e}"
            )


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

        team_df = result.get(
            "team",
            pd.DataFrame(),
        )

        if (
            isinstance(team_df, pd.DataFrame)
            and not team_df.empty
        ):

            st.dataframe(
                team_df,
                use_container_width=True,
                hide_index=True,
            )

            if (
                "Team" in team_df.columns
                and "Productivity_%" in team_df.columns
            ):

                st.subheader(
                    "Productivity by Team"
                )

                st.bar_chart(
                    team_df.set_index("Team")[
                        "Productivity_%"
                    ]
                )

        else:

            st.info(
                "No team-level data available."
            )

    with right:

        st.subheader(
            "Management Snapshot"
        )

        employees = result.get(
            "employees",
            pd.DataFrame(),
        )

        if (
            isinstance(employees, pd.DataFrame)
            and not employees.empty
        ):

            st.metric(
                "Employees analyzed",
                len(employees),
            )

            if "Risk_Score" in employees.columns:

                st.metric(
                    "Highest employee risk score",
                    f"{employees['Risk_Score'].max():.2f}",
                )

        st.write(
            "**Current KPI position**"
        )

        for item in summary_points:
            st.write(item)


# ============================================================
# TAB 2 — AI INSIGHTS
# ============================================================

with tabs[1]:

    st.subheader(
        "🚨 Automated Findings"
    )

    findings_df = result.get(
        "findings",
        pd.DataFrame(),
    )

    if (
        isinstance(findings_df, pd.DataFrame)
        and not findings_df.empty
    ):

        st.dataframe(
            findings_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.success(
            "✅ No threshold breaches detected."
        )

    st.info(
        "Root causes are evidence-based hypotheses. "
        "The available data may not prove causality."
    )


# ============================================================
# TAB 3 — EMPLOYEE RISK
# ============================================================

with tabs[2]:

    st.subheader(
        "👥 Employee Risk"
    )

    employee_data = result.get(
        "employees",
        pd.DataFrame(),
    )

    if (
        isinstance(employee_data, pd.DataFrame)
        and not employee_data.empty
    ):

        sort_cols = [
            c
            for c in [
                "Risk_Score",
                "Avg_Productivity",
            ]
            if c in employee_data.columns
        ]

        if sort_cols:

            employee_data = employee_data.sort_values(
                sort_cols,
                ascending=[
                    False
                ] * len(sort_cols),
            )

        st.dataframe(
            employee_data,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No employee-level risk data available."
        )


# ============================================================
# TAB 4 — ACTION CENTER
# ============================================================

with tabs[3]:

    st.subheader(
        "✅ Recommended Actions"
    )

    if (
        isinstance(actions_df, pd.DataFrame)
        and not actions_df.empty
    ):

        st.dataframe(
            actions_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.success(
            "No action items generated."
        )


# ============================================================
# TAB 5 — MANAGEMENT COPILOT
# ============================================================

with tabs[4]:

    st.subheader(
        "🤖 Management Copilot"
    )

    st.caption(
        "Ask questions about the uploaded operational data. "
        "The Copilot is instructed to use only the supplied "
        "operational context."
    )

    question = st.text_input(
        "Ask your operational question",
        placeholder=(
            "Which team has the quality drop and "
            "what action should be taken?"
        ),
        key="copilot_question",
    )

    ask_copilot = st.button(
        "🚀 Ask Management Copilot",
        type="primary",
        use_container_width=True,
        key="ask_management_copilot",
    )

    if ask_copilot:

        if not question.strip():

            st.warning(
                "⚠️ Please enter a question first."
            )

        elif not plan_config["copilot"]:

            st.error(
                "Copilot is not available on this plan."
            )

        elif not copilot_url:

            st.error(
                "❌ N8N_COPILOT_WEBHOOK_URL is not "
                "configured in Streamlit Secrets."
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

                with st.spinner(
                    "🤖 Management Copilot is analyzing..."
                ):

                    copilot_response = requests.post(
                        copilot_url,
                        json=payload,
                        headers={
                            "Content-Type": "application/json"
                        },
                        timeout=120,
                    )

                if copilot_response.status_code < 300:

                    raw = normalize_n8n_response(
                        copilot_response
                    )

                    answer_data = parse_ai_answer(
                        raw
                    )

                    st.session_state.copilot_answer = (
                        answer_data
                    )

                    st.session_state.last_question = (
                        question.strip()
                    )

                else:

                    st.session_state.copilot_answer = None

                    st.error(
                        "❌ Copilot workflow failed: "
                        f"HTTP {copilot_response.status_code}"
                    )

                    st.code(
                        copilot_response.text,
                        language="text",
                    )

            except requests.exceptions.Timeout:

                st.session_state.copilot_answer = None

                st.error(
                    "⏱️ Management Copilot timed out. "
                    "Please try again."
                )

            except requests.exceptions.ConnectionError:

                st.session_state.copilot_answer = None

                st.error(
                    "🔌 Could not connect to the n8n "
                    "Copilot webhook."
                )

            except requests.exceptions.RequestException as e:

                st.session_state.copilot_answer = None

                st.error(
                    f"❌ Copilot request failed: {e}"
                )

            except Exception as e:

                st.session_state.copilot_answer = None

                st.error(
                    f"❌ Unexpected Copilot error: {e}"
                )

    if st.session_state.copilot_answer:

        st.divider()

        st.markdown(
            "### 🧠 Copilot Analysis"
        )

        st.caption(
            "Question: "
            + st.session_state.last_question
        )

        answer = st.session_state.copilot_answer

        if isinstance(answer, dict):

            what = answer.get(
                "what_is_happening"
            )

            factors = answer.get(
                "contributing_factors",
                [],
            )

            rec_actions = answer.get(
                "recommended_actions",
                [],
            )

            priority = answer.get(
                "priority",
                "",
            )

            owner = answer.get(
                "owner",
                "",
            )

            timeline = answer.get(
                "timeline",
                "",
            )

            sufficiency = answer.get(
                "data_sufficiency"
            )

            if what:

                st.markdown(
                    "#### 🔎 What is happening"
                )

                st.info(what)

            if factors:

                st.markdown(
                    "#### 🔍 Contributing Factors"
                )

                for factor in factors:
                    st.write(
                        f"• {factor}"
                    )

            if rec_actions:

                st.markdown(
                    "#### ✅ Recommended Actions"
                )

                for i, action in enumerate(
                    rec_actions,
                    1,
                ):

                    st.markdown(
                        f"**{i}.** {action}"
                    )

            st.markdown(
                "#### 📌 Management Decision"
            )

            d1, d2, d3 = st.columns(3)

            with d1:
                st.metric(
                    "Priority",
                    priority or "N/A",
                )

            with d2:
                st.metric(
                    "Owner",
                    owner or "N/A",
                )

            with d3:
                st.metric(
                    "Timeline",
                    timeline or "N/A",
                )

            if sufficiency:

                st.markdown(
                    "#### 📊 Data Sufficiency"
                )

                st.warning(
                    sufficiency
                )

        elif isinstance(answer, str):

            st.markdown(answer)

        else:

            st.code(
                str(answer),
                language="text",
            )


# ============================================================
# TAB 6 — REPORTS
# ============================================================

with tabs[5]:

    st.subheader(
        "📄 Management Reports"
    )

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

                with st.spinner(
                    "Generating management report..."
                ):

                    pdf = create_pdf_report(
                        company_name
                        or "Organization",
                        report_name
                        or "Operations Report",
                        report_result,
                        risk_level,
                        summary_points,
                        recommendation,
                    )

                st.session_state.report_pdf = pdf

                st.session_state.report_generated_at = (
                    datetime.now()
                )

            except Exception as e:

                st.error(
                    f"❌ Could not generate PDF: {e}"
                )

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

        st.subheader(
            "📧 Email Report"
        )

        if not plan_config["email"]:

            st.info(
                "Email delivery is available on "
                "Professional and Business plans."
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

                    st.warning(
                        "Enter a recipient email address."
                    )

                elif not st.session_state.report_pdf:

                    st.warning(
                        "Generate the PDF first."
                    )

                else:

                    try:

                        send_email_report(
                            recipient.strip(),
                            f"{company_name} - {report_name}",
                            (
                                "Please find attached the management "
                                f"report for {company_name or 'your organization'}.\n\n"
                                "Generated by Generative Insight AI "
                                "Operations Copilot."
                            ),
                            st.session_state.report_pdf,
                            "operations_report.pdf",
                        )

                        st.success(
                            "✅ Report emailed successfully."
                        )

                    except Exception as e:

                        st.error(
                            f"❌ Email failed: {e}"
                        )

        st.divider()

        st.subheader(
            "📥 Data Exports"
        )

        e1, e2 = st.columns(2)

        with e1:

            team_df = result.get(
                "team",
                pd.DataFrame(),
            )

            if isinstance(
                team_df,
                pd.DataFrame,
            ):

                st.download_button(
                    "⬇️ Team Analysis CSV",
                    team_df.to_csv(
                        index=False
                    ).encode("utf-8"),
                    "team_analysis.csv",
                    "text/csv",
                    use_container_width=True,
                    key="download_team_analysis",
                )

        with e2:

            if isinstance(
                actions_df,
                pd.DataFrame,
            ):

                st.download_button(
                    "⬇️ Action Plan CSV",
                    actions_df.to_csv(
                        index=False
                    ).encode("utf-8"),
                    "action_plan.csv",
                    "text/csv",
                    use_container_width=True,
                    key="download_action_plan",
                )


# ============================================================
# TAB 7 — BILLING
# ============================================================

with tabs[6]:

    st.subheader(
        "💳 Subscription & Billing"
    )

    st.info(
        f"You are currently using the "
        f"**{st.session_state.user_plan}** plan."
    )

    show_pricing("billing")

    st.caption("Professional subscriptions are processed through Razorpay. Complete checkout and verify payment to activate access.")


# ============================================================
# AI PROMPT / DEBUG AREA
# ============================================================

with st.expander(
    "🧠 AI Analyst Context / Prompt",
    expanded=False,
):

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
    <div class="gi-footer">
        <strong>Generative Insight</strong>
        · AI Operations Copilot v{APP_VERSION}
        <br>
        Insights today. Intelligence tomorrow.
        <br>
        <a href="{WEBSITE_URL}" target="_blank">
            generativeinsight.in
        </a>
        &nbsp;·&nbsp;
        © {datetime.now().year}
    </div>
    """,
    unsafe_allow_html=True,
)
