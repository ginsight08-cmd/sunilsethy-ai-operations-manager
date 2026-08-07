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
# Updated UI/UX version
# ============================================================

APP_NAME = "Generative Insight"
APP_VERSION = "1.2.0"

st.set_page_config(
    page_title="Generative Insight | AI Operations Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
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
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# GLOBAL UI / UX THEME
# ============================================================

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Manrope:wght@600;700;800&display=swap');

:root {{
    --gi-blue: {BRAND_BLUE};
    --gi-cyan: {BRAND_CYAN};
    --gi-orange: {BRAND_ORANGE};
    --gi-navy: {BRAND_NAVY};
    --gi-ink: #172B4D;
    --gi-muted: #667085;
    --gi-light: #F6F9FD;
    --gi-border: #E3EAF4;
    --gi-card: #FFFFFF;
    --gi-green: #12B76A;
    --gi-red: #F04438;
    --gi-yellow: #F79009;
}}

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

h1, h2, h3, h4 {{
    font-family: 'Manrope', 'Inter', sans-serif !important;
    color: var(--gi-navy);
    letter-spacing: -0.35px;
}}

.stApp {{
    background:
        radial-gradient(circle at 92% 0%, rgba(0,174,239,.10), transparent 27%),
        radial-gradient(circle at 3% 20%, rgba(7,87,184,.055), transparent 25%),
        linear-gradient(180deg, #FFFFFF 0%, #F6F9FD 100%);
}}

.main .block-container {{
    max-width: 1540px;
    padding-top: 1.15rem;
    padding-bottom: 3rem;
}}

[data-testid="stHeader"] {{
    background: rgba(255,255,255,.72);
}}

.gi-topbar {{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:20px;
    padding:12px 16px;
    margin-bottom:16px;
    border:1px solid var(--gi-border);
    border-radius:16px;
    background:rgba(255,255,255,.86);
    box-shadow:0 7px 25px rgba(7,26,61,.045);
}}

.gi-topbar-left {{
    display:flex;
    align-items:center;
    gap:12px;
}}

.gi-logo-dot {{
    width:38px;
    height:38px;
    border-radius:11px;
    display:flex;
    align-items:center;
    justify-content:center;
    color:white;
    font-weight:800;
    background:linear-gradient(135deg,var(--gi-blue),var(--gi-cyan));
    box-shadow:0 7px 18px rgba(7,87,184,.22);
}}

.gi-brand-name {{
    font-family:'Manrope','Inter',sans-serif;
    font-size:1.08rem;
    font-weight:800;
    color:var(--gi-navy);
    line-height:1.1;
}}

.gi-brand-name span {{ color:var(--gi-blue); }}

.gi-brand-tagline {{
    font-size:.72rem;
    color:var(--gi-muted);
    margin-top:2px;
}}

.gi-topbar-right {{
    display:flex;
    align-items:center;
    gap:8px;
    color:#52627A;
    font-size:.78rem;
    font-weight:600;
}}

.gi-status {{
    display:inline-flex;
    align-items:center;
    gap:6px;
    padding:6px 10px;
    border-radius:999px;
    background:#ECFDF3;
    color:#087443;
    border:1px solid #B7E7CC;
}}

.gi-status-dot {{
    width:7px;
    height:7px;
    border-radius:50%;
    background:#12B76A;
}}

.main-title {{
    font-family:'Manrope','Inter',sans-serif;
    font-size:clamp(2rem,3.2vw,3.25rem);
    font-weight:800;
    line-height:1.03;
    color:var(--gi-navy);
    margin:.1rem 0 .3rem;
    letter-spacing:-1.8px;
}}

.brand-subtitle {{
    color:var(--gi-muted);
    font-size:.98rem;
    line-height:1.6;
    margin-bottom:1.1rem;
}}

.section-kicker {{
    display:inline-flex;
    align-items:center;
    color:var(--gi-blue);
    background:rgba(7,87,184,.07);
    border:1px solid rgba(7,87,184,.12);
    border-radius:999px;
    padding:.34rem .72rem;
    font-size:.68rem;
    font-weight:800;
    letter-spacing:.075em;
    text-transform:uppercase;
    margin-bottom:.55rem;
}}

.hero {{
    position:relative;
    overflow:hidden;
    padding:1.35rem 1.55rem;
    border-radius:22px;
    border:1px solid #D6E5F7;
    background:
        linear-gradient(135deg,rgba(7,87,184,.095),rgba(0,174,239,.045) 55%,rgba(255,157,0,.055));
    box-shadow:0 16px 45px rgba(7,87,184,.07);
    margin:0 0 1.25rem;
}}

.hero::after {{
    content:'';
    position:absolute;
    width:210px;
    height:210px;
    right:-75px;
    top:-110px;
    border-radius:50%;
    background:rgba(0,174,239,.10);
}}

.hero-content {{
    position:relative;
    z-index:2;
}}

.hero-title {{
    font-family:'Manrope','Inter',sans-serif;
    font-size:1.35rem;
    font-weight:800;
    color:var(--gi-navy);
    margin:0;
}}

.hero-description {{
    color:#52627A;
    margin:.3rem 0 0;
    font-size:.9rem;
    line-height:1.55;
}}

.auth-shell {{
    max-width:1000px;
    margin:0 auto;
}}

.auth-card {{
    background:rgba(255,255,255,.96);
    border:1px solid var(--gi-border);
    border-radius:24px;
    padding:.7rem .9rem 1.05rem;
    box-shadow:0 22px 65px rgba(7,26,61,.09);
    backdrop-filter:blur(12px);
}}

.auth-heading {{
    text-align:center;
    color:var(--gi-navy);
    font-size:clamp(1.65rem,3vw,2.35rem);
    font-weight:800;
    line-height:1.15;
    margin:.2rem 0 .35rem;
}}

.auth-description {{
    text-align:center;
    color:#475467;
    font-size:1rem;
    margin-bottom:1rem;
}}

.auth-note {{
    text-align:center;
    color:var(--gi-muted);
    font-size:.8rem;
    margin-top:.8rem;
}}

.small-muted {{
    color:var(--gi-muted);
    font-size:.84rem;
}}

.text-center {{
    text-align:center !important;
}}

.dashboard-card {{
    background:rgba(255,255,255,.94);
    border:1px solid var(--gi-border);
    border-radius:18px;
    padding:1rem 1.05rem;
    box-shadow:0 7px 24px rgba(7,26,61,.045);
}}

.dashboard-card-title {{
    font-family:'Manrope','Inter',sans-serif;
    color:var(--gi-navy);
    font-weight:800;
    font-size:1rem;
    margin-bottom:.2rem;
}}

.dashboard-card-subtitle {{
    color:var(--gi-muted);
    font-size:.78rem;
}}

.copilot-hero {{
    position:relative;
    overflow:hidden;
    border-radius:22px;
    padding:1.35rem 1.45rem;
    margin:.15rem 0 1rem;
    background:linear-gradient(135deg,#071A3D 0%,#0757B8 58%,#00AEEF 100%);
    color:#fff;
    box-shadow:0 18px 45px rgba(7,87,184,.20);
}}

.copilot-hero::after {{
    content:'';
    position:absolute;
    width:230px;
    height:230px;
    right:-85px;
    top:-100px;
    border-radius:50%;
    background:rgba(255,255,255,.10);
}}

.copilot-hero-content {{
    position:relative;
    z-index:2;
}}

.copilot-badge {{
    display:inline-flex;
    align-items:center;
    gap:7px;
    border:1px solid rgba(255,255,255,.24);
    background:rgba(255,255,255,.10);
    border-radius:999px;
    padding:5px 10px;
    font-size:.68rem;
    font-weight:800;
    letter-spacing:.04em;
    text-transform:uppercase;
}}

.copilot-title {{
    font-family:'Manrope','Inter',sans-serif;
    font-size:1.5rem;
    font-weight:800;
    margin:.55rem 0 .2rem;
    color:#fff;
}}

.copilot-subtitle {{
    color:rgba(255,255,255,.82);
    font-size:.86rem;
    line-height:1.55;
    max-width:800px;
}}

.copilot-prompt {{
    background:#F8FAFC;
    border:1px solid #E2E8F0;
    border-radius:17px;
    padding:1rem;
    margin:.7rem 0;
}}

.answer-card {{
    border:1px solid #DDE7F3;
    border-radius:18px;
    padding:1rem 1.1rem;
    background:#FFFFFF;
    box-shadow:0 8px 24px rgba(7,26,61,.045);
    margin-bottom:.75rem;
}}

.answer-section-title {{
    color:var(--gi-navy);
    font-family:'Manrope','Inter',sans-serif;
    font-size:.92rem;
    font-weight:800;
    margin-bottom:.4rem;
}}

.answer-text {{
    color:#344054;
    line-height:1.65;
    font-size:.9rem;
}}

.decision-card {{
    background:linear-gradient(180deg,#F8FBFF,#FFFFFF);
    border:1px solid #DCE7F5;
    border-radius:18px;
    padding:1rem;
}}

.plan-card {{
    padding:1.25rem;
    border-radius:19px;
    border:1px solid #DDE7F5;
    background:linear-gradient(180deg,#FFFFFF,#F9FBFF);
    min-height:230px;
    box-shadow:0 8px 24px rgba(7,87,184,.06);
    transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease;
}}

.plan-card:hover {{
    transform:translateY(-3px);
    border-color:var(--gi-cyan);
    box-shadow:0 14px 32px rgba(0,174,239,.12);
}}

.upload-card {{
    border:1.5px dashed #AFC4DF;
    border-radius:18px;
    padding:.35rem;
    background:linear-gradient(135deg,rgba(7,87,184,.025),rgba(0,174,239,.025));
}}

div[data-baseweb="input"],
div[data-baseweb="textarea"],
div[data-baseweb="select"] {{
    border-radius:11px;
}}

div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div {{
    border-color:#D5DFED;
    background:#FFFFFF;
    border-radius:11px;
}}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="textarea"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within {{
    border-color:var(--gi-cyan);
    box-shadow:0 0 0 2px rgba(0,174,239,.12);
}}

.stButton > button,
.stLinkButton > a,
.stDownloadButton > button {{
    border-radius:11px;
    min-height:2.55rem;
    font-weight:700;
    border:1px solid #C9D8EE;
    transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease;
}}

.stButton > button:hover,
.stLinkButton > a:hover,
.stDownloadButton > button:hover {{
    transform:translateY(-1px);
    box-shadow:0 7px 18px rgba(7,87,184,.10);
    border-color:#AFC4DF;
}}

.stButton > button[kind="primary"] {{
    background:linear-gradient(100deg,var(--gi-blue),var(--gi-cyan));
    color:#FFFFFF;
    border:none;
    box-shadow:0 8px 20px rgba(7,87,184,.20);
}}

.stButton > button[kind="primary"]:hover {{
    background:linear-gradient(100deg,#064A9D,#009BD5);
    color:#FFFFFF;
}}

.stTabs [data-baseweb="tab-list"] {{
    gap:.3rem;
    background:rgba(255,255,255,.78);
    padding:.38rem;
    border:1px solid var(--gi-border);
    border-radius:15px;
    box-shadow:0 5px 18px rgba(7,26,61,.035);
}}

.stTabs [data-baseweb="tab"] {{
    border-radius:10px;
    font-weight:700;
    padding:.62rem .82rem;
    color:#52627A;
}}

.stTabs [aria-selected="true"] {{
    color:var(--gi-blue) !important;
    background:rgba(7,87,184,.075);
}}

div[data-testid="stMetric"] {{
    background:rgba(255,255,255,.97);
    border:1px solid var(--gi-border);
    border-radius:17px;
    padding:.95rem 1rem;
    box-shadow:0 7px 22px rgba(7,26,61,.055);
    min-height:108px;
}}

div[data-testid="stMetric"] label {{
    color:#667085;
    font-weight:600;
    font-size:.78rem;
}}

div[data-testid="stMetricValue"] {{
    color:var(--gi-navy);
    font-weight:800;
    letter-spacing:-.5px;
}}

div[data-testid="stDataFrame"] {{
    border:1px solid var(--gi-border);
    border-radius:15px;
    overflow:hidden;
    box-shadow:0 5px 18px rgba(7,26,61,.045);
}}

section[data-testid="stSidebar"] {{
    background:linear-gradient(180deg,#F3F8FF 0%,#FFFFFF 65%);
    border-right:1px solid #DCE6F2;
}}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    color:var(--gi-navy);
}}

div[data-testid="stExpander"] {{
    border:1px solid var(--gi-border);
    border-radius:14px;
    background:rgba(255,255,255,.72);
}}

div[data-testid="stAlert"] {{
    border-radius:13px;
}}

.stProgress > div > div > div > div {{
    background:linear-gradient(90deg,var(--gi-blue),var(--gi-cyan));
}}

.gi-footer {{
    text-align:center;
    color:var(--gi-muted);
    font-size:.78rem;
    padding:1.5rem 0;
    line-height:1.7;
}}

@media (max-width: 900px) {{
    .main .block-container {{
        padding-left:.8rem;
        padding-right:.8rem;
    }}

    .gi-topbar-right {{
        display:none;
    }}

    .hero {{
        padding:1.05rem;
    }}

    .copilot-hero {{
        padding:1.1rem;
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
        return st.secrets.get(name, default)
    except Exception:
        return default


def show_brand_header(compact=False):
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=230 if compact else 360)
    else:
        st.markdown(
            """
            <div class="gi-brand-name">
                Generative <span>Insight</span>
            </div>
            <div class="gi-brand-tagline">
                Insights today. Intelligence tomorrow.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div style="margin-top:-5px;margin-bottom:15px;color:#667085;font-size:.78rem;">
            AI / ML &nbsp;|&nbsp; Annotation &nbsp;|&nbsp;
            Web & App Development
            &nbsp;&nbsp;·&nbsp;&nbsp;
            <a href="{WEBSITE_URL}" target="_blank"
               style="font-weight:700;text-decoration:none;">
               Visit Website ↗
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_topbar():
    st.markdown(
        f"""
        <div class="gi-topbar">
            <div class="gi-topbar-left">
                <div class="gi-logo-dot">GI</div>
                <div>
                    <div class="gi-brand-name">Generative <span>Insight</span></div>
                    <div class="gi-brand-tagline">Insights today. Intelligence tomorrow.</div>
                </div>
            </div>
            <div class="gi-topbar-right">
                <span>AI Operations Copilot</span>
                <span class="gi-status">
                    <span class="gi-status-dot"></span>
                    System Ready
                </span>
            </div>
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
        return "Could not connect to Supabase. Check your Supabase settings."

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
        raise RuntimeError("Authentication succeeded but no user was returned.")

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
            text = (
                text.replace("```json", "", 1)
                .replace("```", "", 1)
                .strip()
            )

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
        raise RuntimeError("PDF generation requires reportlab.")

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

    story.append(Paragraph("Executive Overview", heading_style))
    story.append(Paragraph(f"<b>Risk:</b> {risk_level}", body_style))
    story.append(Spacer(1, 5))

    table = Table(kpi_rows, colWidths=[55 * mm, 45 * mm, 45 * mm])
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
        raise RuntimeError("SMTP settings are not configured in Streamlit Secrets.")

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


def show_pricing(section_id="default"):
    st.markdown("### 💳 Plans")

    c1, c2, c3 = st.columns(3)

    plans = [
        (
            c1,
            "Free",
            "₹0",
            ["5 MB file limit", "Dashboard analytics", "AI Copilot", "PDF report"],
            "Current plan" if st.session_state.user_plan == "Free" else "Start Free",
        ),
        (
            c2,
            "Professional",
            "₹1,999/mo",
            ["25 MB file limit", "AI Copilot", "PDF + email reports", "n8n automation"],
            "Upgrade",
        ),
        (
            c3,
            "Business",
            "Custom",
            ["100 MB file limit", "Advanced automation", "Custom workflows", "Team deployment"],
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
                st.link_button(button, checkout_url, use_container_width=True)
            else:
                st.button(
                    button,
                    use_container_width=True,
                    disabled=True,
                    key=f"disabled_{section_id}_{name}",
                )

            st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# AUTHENTICATION
# ============================================================

if not st.session_state.authenticated:

    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)

    st.markdown(
        """
        <div style="text-align:center;padding-top:12px;">
            <div class="gi-logo-dot" style="margin:0 auto 10px;">GI</div>
            <div class="gi-brand-name" style="font-size:1.5rem;">
                Generative <span>Insight</span>
            </div>
            <div class="gi-brand-tagline">
                Insights today. Intelligence tomorrow.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style="text-align:center;margin:10px 0 20px;color:#667085;font-size:.78rem;">
            AI / ML &nbsp;|&nbsp; Annotation &nbsp;|&nbsp;
            Web & App Development
            &nbsp;·&nbsp;
            <a href="{WEBSITE_URL}" target="_blank"
               style="font-weight:700;text-decoration:none;">
               Visit Website ↗
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="hero">
            <div class="hero-content text-center">
                <div class="section-kicker"
                     style="margin-left:auto;margin-right:auto;">
                    AI OPERATIONS INTELLIGENCE
                </div>
                <div class="auth-heading">AI-powered operational intelligence</div>
                <div class="auth-description">
                    Turn operational data into management decisions.
                </div>
                <p style="text-align:center;color:#475467;line-height:1.65;margin:0;">
                    Create your account, upload Excel/CSV operational data,
                    identify KPI risks, investigate team and employee performance,
                    ask the AI Operations Copilot questions, and generate
                    management-ready reports.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not secret("SUPABASE_URL") or not secret("SUPABASE_ANON_KEY"):
        st.error(
            "🔐 Authentication is not configured yet. Add SUPABASE_URL and "
            "SUPABASE_ANON_KEY in Streamlit → App Settings → Secrets."
        )
        st.stop()

    _, auth_center, _ = st.columns([1, 2, 1])

    with auth_center:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)

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
                            signup_response = sign_up_user(
                                signup_name,
                                signup_company,
                                signup_email,
                                signup_password,
                            )

                        signup_user = getattr(signup_response, "user", None)
                        signup_session = getattr(signup_response, "session", None)

                        if signup_user is not None and signup_session is not None:
                            set_authenticated_user(signup_response)
                            st.success("✅ Account created successfully.")
                            st.rerun()
                        elif signup_user is not None:
                            st.success(
                                "✅ Account created. Please check your email and "
                                "click the verification link before signing in."
                            )
                        else:
                            st.info(
                                "If the email is valid, check your inbox for the verification email."
                            )

                    except Exception as e:
                        st.error("❌ Could not create account: " + friendly_auth_error(e))

            st.caption(
                "By creating an account, you agree to use the platform responsibly "
                "and validate AI recommendations before taking material business action."
            )

        with login_tab:
            st.markdown("### Welcome back")
            st.caption("Sign in to continue to your AI Operations Manager dashboard.")

            with st.form("login_form"):
                login_email = st.text_input(
                    "Email",
                    placeholder="name@company.com",
                    key="login_email",
                )
                login_password = st.text_input(
                    "Password",
                    type="password",
                    key="login_password",
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
                            login_response = sign_in_user(
                                login_email,
                                login_password,
                            )

                        set_authenticated_user(login_response)
                        st.success("✅ Signed in successfully.")
                        st.rerun()

                    except Exception as e:
                        st.error("❌ Sign in failed: " + friendly_auth_error(e))

            st.markdown(
                '<div class="auth-note">🔒 Your account is secured through Supabase Authentication.</div>',
                unsafe_allow_html=True,
            )
            st.info(
                "If email confirmation is enabled in Supabase, verify your email before signing in."
            )

        with pricing_tab:
            show_pricing("auth")

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
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
            <div class="gi-brand-name">
                Generative <span>Insight</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption("AI Operations Copilot")

    st.markdown(
        f"""
        <a href="{WEBSITE_URL}" target="_blank"
           style="font-weight:700;text-decoration:none;">
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

show_topbar()

st.markdown(
    '<div class="section-kicker">EXECUTIVE OPERATIONS INTELLIGENCE</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="main-title">AI Operations Manager</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="brand-subtitle">
        Executive operational intelligence
        <span style="color:#A0AEC0;">→</span>
        risk detection
        <span style="color:#A0AEC0;">→</span>
        AI decisions
        <span style="color:#A0AEC0;">→</span>
        action plans
        <span style="color:#A0AEC0;">→</span>
        management reports
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# REPORT SETUP
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

st.markdown(
    f"""
    <div class="dashboard-card" style="margin-bottom:.5rem;">
        <div class="dashboard-card-title">📁 Operational Data</div>
        <div class="dashboard-card-subtitle">
            Upload Excel or CSV data to activate the executive intelligence dashboard.
            Maximum file size: {plan_config['max_mb']} MB.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded = st.file_uploader(
    "Upload Excel or CSV operational data",
    type=["xlsx", "xls", "csv"],
    label_visibility="collapsed",
)

if not uploaded:

    st.info("Upload operational data to activate the executive dashboard.")

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
        f"File is {file_mb:.2f} MB. Your {st.session_state.user_plan} "
        f"plan supports files up to {plan_config['max_mb']} MB."
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
        "For production, activate the workflow and use the production webhook."
    )

if copilot_url and "/webhook-test/" in copilot_url:
    st.warning(
        "⚠️ Management Copilot is using an n8n TEST webhook. "
        "Use the production Copilot webhook after activating the workflow."
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
        df = pd.read_excel(uploaded, sheet_name=sheet)

except Exception as e:
    st.error(f"❌ Could not read the uploaded file: {e}")
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

missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    st.error("❌ Required columns are missing.")
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
    st.error(f"❌ Analysis failed: {e}")
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
        <div class="hero-content">
            <div class="section-kicker">EXECUTIVE HEALTH</div>
            <div class="hero-title">{risk_level}</div>
            <div class="hero-description">
                {company_name or "Your organization"} · {report_name}
                &nbsp;·&nbsp; {len(df):,} operational records analyzed
            </div>
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
        "Immediate management attention is recommended. Multiple KPI thresholds "
        "are breached. Prioritize root-cause analysis, targeted corrective actions, "
        "and close monitoring."
    )
elif breaches >= 1:
    recommendation = (
        "Management should review the affected KPIs, validate contributing factors, "
        "and initiate targeted corrective actions."
    )
else:
    recommendation = (
        "Operations are within defined KPI thresholds. Continue monitoring performance "
        "and maintain current processes."
    )

st.subheader("🧠 Executive Summary")

summary_cols = st.columns(4)

for idx, point in enumerate(summary_points):
    with summary_cols[idx]:
        st.markdown(
            f"""
            <div class="dashboard-card" style="min-height:90px;">
                <div style="font-size:.84rem;line-height:1.55;color:#344054;">
                    {point}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.info(f"💡 **Management Recommendation:** {recommendation}")


# ============================================================
# N8N OPERATIONAL AUTOMATION
# ============================================================

if n8n_url and not st.session_state.n8n_sent:

    if not company_name.strip() or not manager_email.strip():
        st.warning(
            "Enter Company Name and Manager Email to run the configured n8n operational automation."
        )
    else:
        try:
            uploaded.seek(0)

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
                st.code(response.text, language="text")

        except requests.exceptions.Timeout:
            st.warning("⏱️ n8n timed out. The workflow may still be running.")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Could not connect to n8n: {e}")


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

    left, right = st.columns([1.45, 1])

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

            m1, m2 = st.columns(2)

            with m1:
                st.metric("Employees analyzed", f"{len(employees):,}")

            with m2:
                if "Risk_Score" in employees.columns:
                    st.metric(
                        "Highest risk score",
                        f"{employees['Risk_Score'].max():.2f}",
                    )

        st.markdown("**Current KPI position**")

        for item in summary_points:
            st.write(item)

        st.info(
            "Use the AI Insights, Employee Risk and Action Center tabs "
            "to move from detection to action."
        )


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
        "Root causes are evidence-based hypotheses. The available data may not prove causality."
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

    # Strong, highly visible Copilot hero.
    st.markdown(
        """
        <div class="copilot-hero">
            <div class="copilot-hero-content">
                <div class="copilot-badge">🤖 AI Operations Copilot · v1.2</div>
                <div class="copilot-title">Ask your Management Copilot</div>
                <div class="copilot-subtitle">
                    Ask questions about productivity, quality, SLA, AHT, team performance,
                    employee risk and recommended actions. The Copilot uses the operational
                    context from the uploaded dataset.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="copilot-prompt">
            <div class="dashboard-card-title">💬 Management Question</div>
            <div class="dashboard-card-subtitle">
                Example: Which team has the quality drop and what action should management take?
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    question = st.text_area(
        "Ask your operational question",
        placeholder=(
            "Example: Which team is creating the biggest SLA risk, "
            "why is it happening, and what should management do next?"
        ),
        height=105,
        key="copilot_question",
        label_visibility="collapsed",
    )

    c1, c2 = st.columns([3, 1])

    with c1:
        ask_copilot = st.button(
            "🚀 Ask Management Copilot",
            type="primary",
            use_container_width=True,
            key="ask_management_copilot",
        )

    with c2:
        clear_copilot = st.button(
            "🧹 Clear",
            use_container_width=True,
            key="clear_copilot",
        )

    if clear_copilot:
        st.session_state.copilot_answer = None
        st.session_state.last_question = ""
        st.rerun()

    if ask_copilot:

        if not question.strip():
            st.warning("⚠️ Please enter a question first.")

        elif not plan_config["copilot"]:
            st.error("Copilot is not available on this plan.")

        elif not copilot_url:
            st.error(
                "❌ N8N_COPILOT_WEBHOOK_URL is not configured in Streamlit Secrets."
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

                with st.spinner("🤖 Management Copilot is analyzing your question..."):

                    copilot_response = requests.post(
                        copilot_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=120,
                    )

                if copilot_response.status_code < 300:

                    raw = normalize_n8n_response(copilot_response)
                    answer_data = parse_ai_answer(raw)

                    st.session_state.copilot_answer = answer_data
                    st.session_state.last_question = question.strip()

                else:

                    st.session_state.copilot_answer = None

                    st.error(
                        "❌ Copilot workflow failed: "
                        f"HTTP {copilot_response.status_code}"
                    )

                    st.code(copilot_response.text, language="text")

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

            except requests.exceptions.RequestException as e:

                st.session_state.copilot_answer = None
                st.error(f"❌ Copilot request failed: {e}")

            except Exception as e:

                st.session_state.copilot_answer = None
                st.error(f"❌ Unexpected Copilot error: {e}")

    if st.session_state.copilot_answer:

        st.divider()

        st.markdown(
            """
            <div class="section-kicker">AI RESPONSE</div>
            <h3 style="margin-top:0;">🧠 Copilot Analysis</h3>
            """,
            unsafe_allow_html=True,
        )

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
                st.markdown(
                    f"""
                    <div class="answer-card">
                        <div class="answer-section-title">🔎 What is happening</div>
                        <div class="answer-text">{what}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if factors:
                st.markdown(
                    '<div class="answer-card"><div class="answer-section-title">🔍 Contributing Factors</div>',
                    unsafe_allow_html=True,
                )

                for factor in factors:
                    st.markdown(
                        f'<div class="answer-text">• {factor}</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown("</div>", unsafe_allow_html=True)

            if rec_actions:
                st.markdown(
                    '<div class="answer-card"><div class="answer-section-title">✅ Recommended Actions</div>',
                    unsafe_allow_html=True,
                )

                for i, action in enumerate(rec_actions, 1):
                    st.markdown(
                        f'<div class="answer-text"><strong>{i}.</strong> {action}</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(
                """
                <div class="decision-card">
                    <div class="answer-section-title">
                        📌 Management Decision
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            d1, d2, d3 = st.columns(3)

            with d1:
                st.metric("Priority", priority or "N/A")

            with d2:
                st.metric("Owner", owner or "N/A")

            with d3:
                st.metric("Timeline", timeline or "N/A")

            if sufficiency:
                st.warning(f"📊 **Data Sufficiency:** {sufficiency}")

        elif isinstance(answer, str):

            st.markdown(
                f"""
                <div class="answer-card">
                    <div class="answer-section-title">🧠 Copilot Response</div>
                    <div class="answer-text">{answer}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:
            st.code(str(answer), language="text")

    else:
        st.markdown(
            """
            <div class="dashboard-card" style="margin-top:1rem;">
                <div class="dashboard-card-title">💡 Try asking</div>
                <div class="dashboard-card-subtitle" style="line-height:1.9;">
                    • Which team is creating the biggest KPI risk?<br>
                    • Why did quality fall below target?<br>
                    • Which employees need immediate attention?<br>
                    • What actions should management take today?<br>
                    • Is the current operational risk improving or worsening?
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# TAB 6 — REPORTS
# ============================================================

with tabs[5]:

    st.subheader("📄 Management Reports")

    if not plan_config["pdf"]:
        st.warning("PDF reporting is not available on your current plan.")

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

            except Exception as e:
                st.error(f"❌ Could not generate PDF: {e}")

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
                                "Please find attached the management report for "
                                f"{company_name or 'your organization'}.\n\n"
                                "Generated by Generative Insight AI Operations Copilot."
                            ),
                            st.session_state.report_pdf,
                            "operations_report.pdf",
                        )

                        st.success("✅ Report emailed successfully.")

                    except Exception as e:
                        st.error(f"❌ Email failed: {e}")

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
        "To activate real paid checkout, configure the plan checkout URLs "
        "in Streamlit Secrets using your payment provider."
    )


# ============================================================
# AI CONTEXT / DEBUG
# ============================================================

with st.expander("🧠 AI Analyst Context / Prompt", expanded=False):
    st.code(make_ai_prompt(result), language="text")


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
