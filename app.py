import io
import json
import smtplib
from datetime import datetime
from email.message import EmailMessage

import pandas as pd
import requests
import streamlit as st
from supabase import create_client, Client

from engine import analyze_data, make_ai_prompt

APP_NAME = "Generative Insight"
APP_VERSION = "1.0.0"

st.set_page_config(
    page_title="Generative Insight | AI Operations Manager",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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

# ------------------------------------------------------------
# CSS: all HTML is deliberately contained in ONE style block.
# KPI controls live in the main page, not only the sidebar.
# This makes them available in Wix, fullscreen and mobile.
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"] { background:#f8fbff !important; }
    .stApp {
        background:radial-gradient(circle at 90% 0%,rgba(37,99,235,.07),transparent 30%),
                   linear-gradient(180deg,#f8fbff 0%,#fff 48%,#f8fbff 100%);
        color:#172033 !important;
    }
    .main .block-container {
        width:100% !important; max-width:1180px !important; margin:0 auto !important;
        padding:1.5rem 1.25rem 4rem !important;
    }
    .stMarkdown,.stMarkdown p,.stMarkdown li,.stCaption,label,
    .stTextInput label,.stNumberInput label,.stFileUploader label,
    [data-testid="stWidgetLabel"] { color:#172033 !important; }
    h1,h2,h3,h4,h5,h6 { color:#102a56 !important; }
    p { color:#334155; }

    .gi-brand { font-size:30px; line-height:1.1; font-weight:800; color:#102a56 !important;
        margin:0 0 4px; letter-spacing:-.7px; }
    .gi-brand span { color:#1769e0 !important; }
    .gi-tagline { color:#52637a !important; font-size:14px; margin:0 0 8px; }
    .gi-services { color:#52637a !important; font-size:13px; margin:0 0 22px; }

    .gi-hero { border:1px solid #d8e7fb; border-radius:22px; padding:34px 38px; margin-bottom:26px;
        background:linear-gradient(135deg,rgba(235,245,255,.98),rgba(255,255,255,.98));
        box-shadow:0 12px 35px rgba(31,72,125,.08); }
    .gi-hero h1 { color:#102a56 !important; font-size:36px; line-height:1.15; font-weight:800;
        letter-spacing:-1px; margin:0 0 12px; }
    .gi-hero-subtitle { color:#1769e0 !important; font-size:19px; font-weight:600; margin-bottom:12px; }
    .gi-hero-description { color:#475569 !important; font-size:15px; line-height:1.7; max-width:850px; margin:0; }

    .gi-kpi-panel { background:#fff; border:1px solid #dbe6f2; border-radius:16px;
        padding:18px 20px 8px; margin-bottom:10px; box-shadow:0 5px 20px rgba(15,23,42,.05); }
    .gi-kpi-title { color:#102a56 !important; font-size:18px; font-weight:800; margin:0 0 2px; }
    .gi-kpi-subtitle { color:#64748b !important; font-size:13px; margin:0 0 8px; }

    .stButton > button,.stLinkButton > a,[data-testid="stFormSubmitButton"] button {
        border-radius:10px !important; font-weight:600 !important; min-height:42px !important;
    }
    .stTextInput input,.stNumberInput input,.stTextArea textarea {
        color:#172033 !important; background:#fff !important; border:1px solid #cbd5e1 !important;
        border-radius:9px !important;
    }
    .stTextInput input::placeholder,.stTextArea textarea::placeholder { color:#64748b !important; opacity:1 !important; }
    [data-testid="stFileUploader"] { background:#fff; border:1px dashed #94a3b8; border-radius:14px; padding:10px; }
    button[data-baseweb="tab"] { color:#475569 !important; font-weight:600 !important; }
    button[data-baseweb="tab"][aria-selected="true"] { color:#1769e0 !important; }
    [data-testid="stMetric"] { background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:15px; }
    [data-testid="stMetricLabel"] { color:#475569 !important; }
    [data-testid="stMetricValue"] { color:#102a56 !important; }
    [data-testid="stSidebar"] { background:#f8fbff; border-right:1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color:#172033; }

    /* Streamlit/GitHub/cloud controls */
    header[data-testid="stHeader"] { background:transparent !important; height:0 !important; min-height:0 !important; }
    [data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],
    [data-testid="stHeaderActionElements"],.stAppDeployButton,
    button[title="Share"],button[aria-label="Share"],button[title="GitHub"],button[aria-label="GitHub"],
    button[title="Edit"],button[aria-label="Edit"],button[data-testid="stToolbarButton"] {
        display:none !important; visibility:hidden !important; opacity:0 !important; pointer-events:none !important;
    }
    footer { display:none !important; visibility:hidden !important; }
    [data-testid="stSidebarCollapsedControl"] { display:none !important; }

    @media (max-width:768px) {
        .main .block-container { max-width:100% !important; padding:.8rem .75rem 3rem !important; }
        .gi-brand { font-size:25px; }
        .gi-tagline { font-size:13px; }
        .gi-services { font-size:12px; line-height:1.6; }
        .gi-hero { border-radius:16px; padding:24px 20px; margin-bottom:18px; }
        .gi-hero h1 { font-size:28px; letter-spacing:-.5px; }
        .gi-hero-subtitle { font-size:17px; }
        .gi-hero-description { font-size:14px; line-height:1.6; }
        .gi-kpi-panel { border-radius:14px; padding:16px 14px 6px; }
        .gi-kpi-title { font-size:17px; }
        .gi-kpi-panel .stNumberInput { width:100% !important; }
        .stButton > button,.stLinkButton > a,[data-testid="stFormSubmitButton"] button { width:100% !important; }
        [data-testid="stMetric"] { margin-bottom:8px; }
        button[data-baseweb="tab"] { font-size:12px !important; padding-left:8px !important; padding-right:8px !important; }
    }
    @media (max-width:480px) {
        .main .block-container { padding-left:.55rem !important; padding-right:.55rem !important; }
        .gi-hero { padding:20px 16px; }
        .gi-hero h1 { font-size:24px; }
        .gi-hero-subtitle { font-size:16px; }
        .gi-hero-description { font-size:13px; }
        button[data-baseweb="tab"] { font-size:11px !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def secret(name, default=""):
    return st.secrets.get(name, default)


KPI_RULES = {
    "Productivity": {"higher_is_better": True, "unit": "%"},
    "Quality": {"higher_is_better": True, "unit": "%"},
    "SLA": {"higher_is_better": True, "unit": "%"},
    "AHT": {"higher_is_better": False, "unit": ""},
}


def get_kpi_status(kpi_name, actual, target):
    if kpi_name not in KPI_RULES:
        raise ValueError(f"Unknown KPI: {kpi_name}")
    actual, target = float(actual), float(target)
    higher = KPI_RULES[kpi_name]["higher_is_better"]
    gap = actual - target
    good = actual >= target if higher else actual <= target
    return {
        "name": kpi_name, "actual": actual, "target": target, "gap": gap,
        "is_good": good, "status": "GOOD" if good else "NEEDS ATTENTION",
        "icon": "🟢" if good else "🔴", "delta_color": "normal" if higher else "inverse",
        "unit": KPI_RULES[kpi_name]["unit"],
    }


def get_kpi_statuses(productivity, quality, sla, aht, productivity_target,
                     quality_target, sla_target, aht_target):
    return {
        "Productivity": get_kpi_status("Productivity", productivity, productivity_target),
        "Quality": get_kpi_status("Quality", quality, quality_target),
        "SLA": get_kpi_status("SLA", sla, sla_target),
        "AHT": get_kpi_status("AHT", aht, aht_target),
    }


def kpi_display_value(status):
    return f"{status['actual']:.2f}" if status["name"] == "AHT" else f"{status['actual']:.2f}%"


def kpi_delta_text(status):
    return f"{status['gap']:+.2f} vs target" if status["name"] == "AHT" else f"{status['gap']:+.2f}% vs target"


# ------------------------------------------------------------
# SUPABASE
# ------------------------------------------------------------
def get_supabase_client() -> Client:
    url, anon_key = secret("SUPABASE_URL"), secret("SUPABASE_ANON_KEY")
    if not url or not anon_key:
        raise RuntimeError("Supabase authentication is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY to Streamlit Secrets.")
    return create_client(url, anon_key)


def friendly_auth_error(error):
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
    return message


def sign_up_user(full_name, company_name, email, password):
    return get_supabase_client().auth.sign_up({
        "email": email.strip().lower(), "password": password,
        "options": {"data": {"full_name": full_name.strip(), "company_name": company_name.strip(), "plan": "Free"}},
    })


def sign_in_user(email, password):
    return get_supabase_client().auth.sign_in_with_password({"email": email.strip().lower(), "password": password})


def sign_out_user():
    try:
        get_supabase_client().auth.sign_out()
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
    for key, value in {
        "n8n_sent": False, "n8n_result": None, "copilot_answer": None, "last_question": "",
        "file_name": "", "analysis_result": None, "analysis_df": None,
        "report_pdf": None, "report_generated_at": None,
    }.items():
        st.session_state[key] = value


def clear_authentication():
    sign_out_user()
    for key, value in {"authenticated": False, "user_email": "", "user_id": "", "user_name": "",
                       "company_name": "", "user_plan": "Free"}.items():
        st.session_state[key] = value
    clear_analysis()


def get_plan_config(plan):
    configs = {
        "Free": {"max_mb": 5, "copilot": True, "pdf": True, "email": False, "automation": False, "price": "₹0"},
        "Professional": {"max_mb": 25, "copilot": True, "pdf": True, "email": True, "automation": True, "price": "₹1,999/mo"},
        "Business": {"max_mb": 100, "copilot": True, "pdf": True, "email": True, "automation": True, "price": "Custom"},
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
        answer = data.get("answer") or data.get("response") or data.get("output") or data.get("text") or data.get("message")
    if isinstance(answer, str):
        text = answer.strip()
        if text.startswith("```"):
            text = text[7:] if text.startswith("```json") else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return answer


def dataframe_to_text(df):
    return "No records available." if df is None or df.empty else df.to_string(index=False)


def build_copilot_context(company_name, report_name, result, productivity_target,
                          quality_target, sla_target, aht_target, risk_level, summary_points):
    overall = result["overall"]
    return f"""Company:\n{company_name}\n\nReport:\n{report_name}\n\nOperational KPIs:\n\nProductivity:\n{float(overall['productivity']):.2f}% | Target: {productivity_target}%\n\nQuality:\n{float(overall['quality']):.2f}% | Target: {quality_target}%\n\nSLA:\n{float(overall['sla']):.2f}% | Target: {sla_target}%\n\nAverage AHT:\n{float(overall['aht']):.2f} | Target: {aht_target}\n\nOverall Risk:\n{risk_level}\n\nOperational Findings:\n{dataframe_to_text(result.get('findings'))}\n\nRecommended Actions:\n{dataframe_to_text(result.get('actions'))}\n\nEmployee Risk Data:\n{dataframe_to_text(result.get('employees'))}\n\nTeam Performance:\n{dataframe_to_text(result.get('team'))}\n\nKPI Summary:\n{chr(10).join(summary_points)}""".strip()


# ------------------------------------------------------------
# PDF
# ------------------------------------------------------------
def create_pdf_report(company_name, report_name, result, risk_level, summary_points, recommendation):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ImportError as exc:
        raise RuntimeError("PDF generation requires reportlab. Add reportlab to requirements.txt.") from exc

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=14*mm, leftMargin=14*mm,
                            topMargin=14*mm, bottomMargin=14*mm,
                            title=f"{company_name} - {report_name}", author=APP_NAME)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("GI_Title", parent=styles["Title"], fontSize=20, leading=24, spaceAfter=8)
    heading_style = ParagraphStyle("GI_Heading", parent=styles["Heading2"], fontSize=13, leading=16, spaceBefore=10, spaceAfter=6)
    body_style = ParagraphStyle("GI_Body", parent=styles["BodyText"], fontSize=9, leading=12)
    overall, targets = result["overall"], result.get("_targets", {})
    story = [Paragraph("Generative Insight", title_style),
             Paragraph(f"<b>{company_name}</b> — {report_name}<br/>Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}", body_style), Spacer(1, 8),
             Paragraph("Executive Overview", heading_style), Paragraph(f"<b>Risk:</b> {risk_level}", body_style), Spacer(1, 5)]
    rows = [["KPI", "Actual", "Target"],
            ["Productivity", f"{float(overall['productivity']):.2f}%", f"{targets.get('productivity', '')}%"],
            ["Quality", f"{float(overall['quality']):.2f}%", f"{targets.get('quality', '')}%"],
            ["SLA", f"{float(overall['sla']):.2f}%", f"{targets.get('sla', '')}%"],
            ["Average AHT", f"{float(overall['aht']):.2f}", f"{targets.get('aht', '')}"]]
    table = Table(rows, colWidths=[55*mm, 45*mm, 45*mm])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#102a56")),
                               ("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.35,colors.grey),
                               ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
                               ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("BOTTOMPADDING",(0,0),(-1,-1),6),
                               ("TOPPADDING",(0,0),(-1,-1),6)]))
    story += [table, Paragraph("KPI Summary", heading_style)]
    for item in summary_points:
        story.append(Paragraph(item.replace("🔴 ","").replace("🟢 ","").replace("🟠 ","").replace("🟡 ",""), body_style))
    story += [Paragraph("Management Recommendation", heading_style), Paragraph(recommendation, body_style)]
    for title, key in [("Team Performance","team"),("Operational Findings","findings"),("Recommended Actions","actions"),("Employee Risk","employees")]:
        data_frame = result.get(key)
        if isinstance(data_frame, pd.DataFrame) and not data_frame.empty:
            story.append(Paragraph(title, heading_style))
            pdf_df = data_frame.iloc[:, :8].copy() if len(data_frame.columns) > 8 else data_frame.copy()
            headers = [str(c) for c in pdf_df.columns]
            pdf_rows = [headers] + [[str(v)[:90] for v in row.tolist()] for _, row in pdf_df.head(50).iterrows()]
            width = 180*mm / max(len(headers), 1)
            tbl = Table(pdf_rows, colWidths=[width]*len(headers), repeatRows=1)
            tbl.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#102a56")),
                                     ("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.grey),
                                     ("FONTSIZE",(0,0),(-1,-1),6),("VALIGN",(0,0),(-1,-1),"TOP")]))
            story += [tbl, Spacer(1,5)]
    story += [Spacer(1,8), Paragraph("Generated by Generative Insight AI Operations Copilot. AI recommendations should be validated against operational evidence before management action.", body_style)]
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def send_email_report(recipient, subject, body, pdf_bytes=None, pdf_filename="operations_report.pdf"):
    smtp_host = secret("SMTP_HOST")
    smtp_port = int(secret("SMTP_PORT", "587"))
    smtp_user = secret("SMTP_USERNAME")
    smtp_password = secret("SMTP_PASSWORD")
    smtp_from = secret("SMTP_FROM", smtp_user)
    if not all([smtp_host, smtp_user, smtp_password, smtp_from]):
        raise RuntimeError("SMTP settings are not configured in Streamlit Secrets.")
    message = EmailMessage()
    message["Subject"], message["From"], message["To"] = subject, smtp_from, recipient
    message.set_content(body)
    if pdf_bytes:
        message.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=pdf_filename)
    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls(); server.login(smtp_user, smtp_password); server.send_message(message)


def show_pricing():
    st.subheader("💳 Plans")
    c1, c2, c3 = st.columns(3)
    plans = [
        (c1,"Free","₹0",["5 MB file limit","Dashboard analytics","AI Copilot","PDF report"],"Current plan" if st.session_state.user_plan == "Free" else "Start Free"),
        (c2,"Professional","₹1,999/mo",["25 MB file limit","AI Copilot","PDF + email reports","n8n automation"],"Upgrade"),
        (c3,"Business","Custom",["100 MB file limit","Advanced automation","Custom workflows","Team deployment"],"Contact Sales"),
    ]
    for col, name, price, features, button in plans:
        with col:
            st.markdown(f"### {name}"); st.markdown(f"## {price}")
            for feature in features: st.write(f"✓ {feature}")
            url = secret(f"{name.upper()}_CHECKOUT_URL")
            if url:
                st.link_button(button, url, use_container_width=True)
            else:
                st.button(button, use_container_width=True, disabled=True, key=f"disabled_{name}")


# ============================================================
# AUTH SCREEN
# ============================================================
if not st.session_state.authenticated:
    st.markdown("""
        <div class="gi-brand">Generative <span>Insight</span></div>
        <div class="gi-tagline">Insights today. Intelligence tomorrow.</div>
        <div class="gi-services">AI / ML &nbsp; | &nbsp; Annotation &nbsp; | &nbsp; Web &amp; App Development</div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <section class="gi-hero">
            <h1>AI-powered operational intelligence</h1>
            <div class="gi-hero-subtitle">Turn operational data into management decisions.</div>
            <p class="gi-hero-description">Create your account, upload Excel/CSV operational data,
            identify KPI risks, investigate team and employee performance, ask the AI Operations Copilot
            questions, and generate management-ready reports.</p>
        </section>
    """, unsafe_allow_html=True)

    if not secret("SUPABASE_URL") or not secret("SUPABASE_ANON_KEY"):
        st.error("Authentication is not configured yet. Add SUPABASE_URL and SUPABASE_ANON_KEY in Streamlit Secrets.")
        st.stop()

    signup_tab, login_tab, pricing_tab = st.tabs(["🆕 Create Account", "🔐 Sign In", "💳 Plans"])
    with signup_tab:
        st.subheader("Create your Generative Insight account")
        st.caption("Start with the Free plan. You can upgrade later.")
        with st.form("signup_form", clear_on_submit=False):
            signup_name = st.text_input("Full Name", placeholder="e.g. Sunil Sethy")
            signup_company = st.text_input("Company / Organization", placeholder="e.g. ABC Technologies")
            signup_email = st.text_input("Work Email", placeholder="name@company.com")
            signup_password = st.text_input("Password", type="password")
            signup_confirm = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("🚀 Create Free Account", type="primary", use_container_width=True)
        if submitted:
            if not signup_name.strip(): st.warning("Please enter your full name.")
            elif not signup_company.strip(): st.warning("Please enter your company or organization.")
            elif not signup_email.strip() or "@" not in signup_email: st.warning("Please enter a valid email address.")
            elif len(signup_password) < 6: st.warning("Please use a password with at least 6 characters.")
            elif signup_password != signup_confirm: st.warning("Passwords do not match.")
            else:
                try:
                    with st.spinner("Creating your account..."):
                        response = sign_up_user(signup_name, signup_company, signup_email, signup_password)
                    user, session = getattr(response,"user",None), getattr(response,"session",None)
                    if user is not None and session is not None:
                        set_authenticated_user(response); st.success("Account created successfully."); st.rerun()
                    elif user is not None:
                        st.success("Account created. Please check your email and click the verification link.")
                    else:
                        st.info("If the email is valid, check your inbox.")
                except Exception as exc:
                    st.error("Could not create account: " + friendly_auth_error(exc))
    with login_tab:
        st.subheader("Welcome back")
        with st.form("login_form"):
            login_email = st.text_input("Email", placeholder="name@company.com")
            login_password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("🔐 Sign In", type="primary", use_container_width=True)
        if submitted:
            if not login_email.strip() or not login_password:
                st.warning("Please enter your email and password.")
            else:
                try:
                    with st.spinner("Signing you in..."):
                        response = sign_in_user(login_email, login_password)
                    set_authenticated_user(response); st.success("Signed in successfully."); st.rerun()
                except Exception as exc:
                    st.error("Sign in failed: " + friendly_auth_error(exc))
        st.info("If email confirmation is enabled in Supabase, verify your email before signing in.")
    with pricing_tab:
        show_pricing()
    st.stop()


# ============================================================
# AUTHENTICATED APP
# ============================================================
plan_config = get_plan_config(st.session_state.user_plan)

with st.sidebar:
    st.markdown("## 🤖 Generative Insight")
    st.caption("AI Operations Copilot")
    st.success(f"Plan: **{st.session_state.user_plan}**")
    if st.session_state.get("user_name"): st.caption(st.session_state.user_name)
    st.caption(st.session_state.user_email)
    st.divider()
    if st.button("💳 View Plans", use_container_width=True): st.session_state.show_plans = True; st.rerun()
    if st.button("🔄 Reset Analysis", use_container_width=True): clear_analysis(); st.rerun()
    if st.button("🚪 Sign Out", use_container_width=True): clear_authentication(); st.rerun()

if st.session_state.get("show_plans"):
    st.divider(); show_pricing(); st.divider()

st.markdown("""
    <div class="gi-brand">Generative <span>Insight</span></div>
    <div class="gi-tagline">Insights today. Intelligence tomorrow.</div>
    <div class="gi-services">AI / ML &nbsp; | &nbsp; Annotation &nbsp; | &nbsp; Web &amp; App Development</div>
""", unsafe_allow_html=True)

st.title("🤖 AI Operations Manager")
st.caption("Executive operational intelligence → risk detection → AI decisions → action plans → management reports")

# ============================================================
# KPI CONTROLS — MAIN PAGE, NOT SIDEBAR
# ============================================================
st.markdown("""
    <div class="gi-kpi-panel">
        <div class="gi-kpi-title">⚙️ KPI Controls</div>
        <div class="gi-kpi-subtitle">Set targets used for risk detection, dashboard status, AI insights and management recommendations.</div>
    </div>
""", unsafe_allow_html=True)

kc1, kc2, kc3, kc4 = st.columns(4)
with kc1:
    productivity_target = st.number_input("Productivity target %", min_value=1, max_value=200, value=90, step=1, key="main_productivity_target")
with kc2:
    quality_target = st.number_input("Quality target %", min_value=1, max_value=100, value=95, step=1, key="main_quality_target")
with kc3:
    sla_target = st.number_input("SLA target %", min_value=1, max_value=100, value=97, step=1, key="main_sla_target")
with kc4:
    aht_target = st.number_input("AHT target", min_value=1, max_value=1000, value=50, step=1, key="main_aht_target")

st.subheader("🏢 Report Setup")
col1, col2, col3 = st.columns(3)
with col1:
    company_name = st.text_input("Company Name", value=st.session_state.get("company_name", ""), placeholder="e.g. ABC Technologies", key="company_name_input")
with col2:
    manager_email = st.text_input("Manager Email", placeholder="manager@company.com", key="manager_email_input")
with col3:
    report_name = st.text_input("Report Name", value="Daily Operations Report", key="report_name_input")

uploaded = st.file_uploader(f"📁 Upload Excel or CSV operational data — max {plan_config['max_mb']} MB", type=["xlsx","xls","csv"], key="operations_file_uploader")

if not uploaded:
    st.info("Upload operational data to activate the executive dashboard.")
    st.markdown("### Required columns")
    st.code("Date, Employee_ID, Employee_Name, Team, Target, Production, AHT_Actual, AHT_Target, Quality_%, SLA_%, Attendance, Error_Count, Error_Category")
    st.markdown("### What you get")
    a,b,c,d = st.columns(4)
    a.metric("Risk Detection","✓"); b.metric("Employee Risk","✓"); c.metric("AI Copilot","✓"); d.metric("Management Report","✓")
    st.stop()

file_mb = uploaded.size / (1024 * 1024)
if file_mb > plan_config["max_mb"]:
    st.error(f"File is {file_mb:.2f} MB. Your {st.session_state.user_plan} plan supports files up to {plan_config['max_mb']} MB.")
    st.stop()

if st.session_state.file_name != uploaded.name:
    st.session_state.file_name = uploaded.name
    st.session_state.n8n_sent = False
    st.session_state.n8n_result = None
    st.session_state.copilot_answer = None
    st.session_state.last_question = ""
    st.session_state.analysis_result = None
    st.session_state.analysis_df = None
    st.session_state.report_pdf = None
    st.session_state.report_generated_at = None

n8n_url = secret("N8N_WEBHOOK_URL")
copilot_url = secret("N8N_COPILOT_WEBHOOK_URL")

try:
    uploaded.seek(0)
    if uploaded.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        xls = pd.ExcelFile(uploaded)
        sheet = "Operational_Data" if "Operational_Data" in xls.sheet_names else xls.sheet_names[0]
        df = pd.read_excel(uploaded, sheet_name=sheet)
except Exception as exc:
    st.error(f"Could not read the uploaded file: {exc}"); st.stop()

required_columns = ["Employee_ID","Employee_Name","Team","Target","Production","AHT_Actual","Quality_%","SLA_%"]
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    st.error("Required columns are missing."); st.write(missing_columns); st.stop()

try:
    result = analyze_data(df, productivity_target=productivity_target, quality_target=quality_target, sla_target=sla_target, aht_target=aht_target)
except Exception as exc:
    st.error(f"Analysis failed: {exc}"); st.stop()

st.session_state.analysis_result = result
st.session_state.analysis_df = df

overall = result["overall"]
productivity, quality, sla, aht = (float(overall[k]) for k in ["productivity","quality","sla","aht"])
kpi_statuses = get_kpi_statuses(productivity, quality, sla, aht, productivity_target, quality_target, sla_target, aht_target)

breaches = sum(not status["is_good"] for status in kpi_statuses.values())
risk_level = ["🟢 LOW RISK","🟡 MEDIUM RISK","🟠 HIGH RISK","🔴 CRITICAL RISK"][min(breaches,3)]

actions_df = result.get("actions", pd.DataFrame())
action_count = len(actions_df) if isinstance(actions_df, pd.DataFrame) else 0
high_priority_count = 0
if isinstance(actions_df, pd.DataFrame) and not actions_df.empty:
    for col in ["Priority","priority","Priority_Level","priority_level"]:
        if col in actions_df.columns:
            high_priority_count = len(actions_df[actions_df[col].astype(str).str.lower().isin(["high","critical"])])
            break

st.divider()
st.subheader(f"Executive Health: {risk_level}")
st.caption(f"{company_name or 'Your organization'} · {report_name}")
r1,r2,r3,r4 = st.columns(4)
r1.metric("Operational Risk", risk_level)
r2.metric("KPI Breaches", breaches, delta=f"{4-breaches} on target")
r3.metric("Action Items", action_count)
r4.metric("High/Critical Actions", high_priority_count)

st.subheader("📊 KPI Performance vs Target")
k1,k2,k3,k4 = st.columns(4)
for col, name in zip([k1,k2,k3,k4],["Productivity","Quality","SLA","AHT"]):
    status = kpi_statuses[name]
    col.metric("Average AHT" if name == "AHT" else name, kpi_display_value(status), delta=kpi_delta_text(status), delta_color=status["delta_color"])

summary_points = [
    f"{kpi_statuses['Productivity']['icon']} Productivity: {productivity:.1f}% vs {productivity_target}% target — {kpi_statuses['Productivity']['status']}.",
    f"{kpi_statuses['Quality']['icon']} Quality: {quality:.1f}% vs {quality_target}% target — {kpi_statuses['Quality']['status']}.",
    f"{kpi_statuses['SLA']['icon']} SLA: {sla:.1f}% vs {sla_target}% target — {kpi_statuses['SLA']['status']}.",
    f"{kpi_statuses['AHT']['icon']} AHT: {aht:.1f} vs {aht_target} target — {kpi_statuses['AHT']['status']}.",
]
if breaches >= 3:
    recommendation = "Immediate management attention is recommended. Multiple KPI thresholds are breached. Prioritize root-cause analysis, targeted corrective actions, and close monitoring."
elif breaches >= 1:
    recommendation = "Management should review the affected KPIs, validate contributing factors, and initiate targeted corrective actions."
else:
    recommendation = "Operations are within defined KPI thresholds. Continue monitoring performance and maintain current processes."
st.subheader("🧠 Executive Summary")
for point in summary_points: st.write(point)
st.info(f"💡 **Management Recommendation:** {recommendation}")

# ------------------------------------------------------------
# N8N AUTOMATION
# ------------------------------------------------------------
if n8n_url and not st.session_state.n8n_sent:
    if not company_name.strip() or not manager_email.strip():
        st.warning("Enter Company Name and Manager Email to run the configured n8n automation.")
    else:
        try:
            uploaded.seek(0)
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")}
            data = {"company_name": company_name.strip(), "manager_email": manager_email.strip(), "report_name": report_name.strip()}
            with st.spinner("🤖 Running operational automation..."):
                response = requests.post(n8n_url, files=files, data=data, timeout=120)
            if response.status_code < 300:
                st.session_state.n8n_result = normalize_n8n_response(response)
                st.session_state.n8n_sent = True
                st.success("Operational automation completed.")
            else:
                st.error(f"n8n workflow failed: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            st.warning("n8n timed out. The workflow may still be running.")
        except requests.exceptions.RequestException as exc:
            st.error(f"Could not connect to n8n: {exc}")

# ============================================================
# TABS
# ============================================================
tabs = st.tabs(["📊 Executive Dashboard","🚨 AI Insights","👥 Employee Risk","✅ Action Center","🤖 Management Copilot","📄 Reports","💳 Billing"])

with tabs[0]:
    left,right = st.columns([1.4,1])
    with left:
        st.subheader("Team Performance")
        team_df = result.get("team", pd.DataFrame())
        if isinstance(team_df,pd.DataFrame) and not team_df.empty:
            st.dataframe(team_df,use_container_width=True,hide_index=True)
            if "Team" in team_df.columns and "Productivity_%" in team_df.columns:
                st.subheader("Productivity by Team")
                st.bar_chart(team_df.set_index("Team")["Productivity_%"])
        else: st.info("No team-level data available.")
    with right:
        st.subheader("Management Snapshot")
        employees = result.get("employees",pd.DataFrame())
        if isinstance(employees,pd.DataFrame) and not employees.empty:
            st.metric("Employees analyzed",len(employees))
            if "Risk_Score" in employees.columns: st.metric("Highest employee risk score",f"{employees['Risk_Score'].max():.2f}")
        st.write("**Current KPI position**")
        for item in summary_points: st.write(item)

with tabs[1]:
    st.subheader("🚨 Automated Findings")
    findings_df = result.get("findings",pd.DataFrame())
    if isinstance(findings_df,pd.DataFrame) and not findings_df.empty: st.dataframe(findings_df,use_container_width=True,hide_index=True)
    else: st.success("No threshold breaches detected.")
    st.info("Root causes are evidence-based hypotheses. The available data may not prove causality.")

with tabs[2]:
    st.subheader("👥 Employee Risk")
    employee_data = result.get("employees",pd.DataFrame())
    if isinstance(employee_data,pd.DataFrame) and not employee_data.empty:
        sort_cols = [c for c in ["Risk_Score","Avg_Productivity"] if c in employee_data.columns]
        if sort_cols: employee_data = employee_data.sort_values(sort_cols,ascending=[False]*len(sort_cols))
        st.dataframe(employee_data,use_container_width=True,hide_index=True)
    else: st.info("No employee-level risk data available.")

with tabs[3]:
    st.subheader("✅ Recommended Actions")
    if isinstance(actions_df,pd.DataFrame) and not actions_df.empty: st.dataframe(actions_df,use_container_width=True,hide_index=True)
    else: st.success("No action items generated.")

with tabs[4]:
    st.subheader("🤖 Management Copilot")
    st.caption("Ask questions about the uploaded operational data. The Copilot uses the supplied operational context.")
    question = st.text_input("Ask your operational question",placeholder="Which team has the quality drop and what action should be taken?",key="copilot_question")
    ask_copilot = st.button("🚀 Ask Management Copilot",type="primary",use_container_width=True)
    if ask_copilot:
        if not question.strip(): st.warning("Please enter a question first.")
        elif not plan_config["copilot"]: st.error("Copilot is not available on this plan.")
        elif not copilot_url: st.error("N8N_COPILOT_WEBHOOK_URL is not configured in Streamlit Secrets.")
        else:
            payload = {"question":question.strip(),"company_name":company_name.strip(),"report_name":report_name.strip(),"context":build_copilot_context(company_name,report_name,result,productivity_target,quality_target,sla_target,aht_target,risk_level,summary_points)}
            try:
                with st.spinner("🤖 Management Copilot is analyzing..."):
                    response = requests.post(copilot_url,json=payload,headers={"Content-Type":"application/json"},timeout=120)
                if response.status_code < 300:
                    st.session_state.copilot_answer = parse_ai_answer(normalize_n8n_response(response)); st.session_state.last_question = question.strip()
                else: st.session_state.copilot_answer = None; st.error(f"Copilot workflow failed: HTTP {response.status_code}")
            except requests.exceptions.Timeout: st.session_state.copilot_answer=None; st.error("Management Copilot timed out.")
            except requests.exceptions.ConnectionError: st.session_state.copilot_answer=None; st.error("Could not connect to the n8n Copilot webhook.")
            except requests.exceptions.RequestException as exc: st.session_state.copilot_answer=None; st.error(f"Copilot request failed: {exc}")
            except Exception as exc: st.session_state.copilot_answer=None; st.error(f"Unexpected Copilot error: {exc}")
    if st.session_state.copilot_answer:
        st.divider(); st.markdown("### 🧠 Copilot Analysis"); st.caption(f"Question: {st.session_state.last_question}")
        answer = st.session_state.copilot_answer
        if isinstance(answer,dict):
            what=answer.get("what_is_happening"); factors=answer.get("contributing_factors",[]); rec_actions=answer.get("recommended_actions",[])
            priority=answer.get("priority",""); owner=answer.get("owner",""); timeline=answer.get("timeline",""); sufficiency=answer.get("data_sufficiency")
            if what: st.markdown("#### 🔎 What is happening"); st.info(what)
            if factors:
                st.markdown("#### 🔍 Contributing Factors")
                for factor in factors: st.write(f"• {factor}")
            if rec_actions:
                st.markdown("#### ✅ Recommended Actions")
                for i,action in enumerate(rec_actions,1): st.markdown(f"**{i}.** {action}")
            st.markdown("#### 📌 Management Decision")
            d1,d2,d3=st.columns(3); d1.metric("Priority",priority or "N/A"); d2.metric("Owner",owner or "N/A"); d3.metric("Timeline",timeline or "N/A")
            if sufficiency: st.markdown("#### 📊 Data Sufficiency"); st.warning(sufficiency)
        elif isinstance(answer,str): st.markdown(answer)
        else: st.code(str(answer),language="text")

with tabs[5]:
    st.subheader("📄 Management Reports")
    if not plan_config["pdf"]: st.warning("PDF reporting is not available on your current plan.")
    else:
        report_result=dict(result); report_result["_targets"]={"productivity":productivity_target,"quality":quality_target,"sla":sla_target,"aht":aht_target}
        if st.button("📄 Generate Executive PDF",type="primary",use_container_width=True):
            try:
                with st.spinner("Generating management report..."):
                    st.session_state.report_pdf=create_pdf_report(company_name or "Organization",report_name or "Operations Report",report_result,risk_level,summary_points,recommendation)
                st.session_state.report_generated_at=datetime.now()
            except Exception as exc: st.error(f"Could not generate PDF: {exc}")
        if st.session_state.report_pdf:
            filename=f"{company_name or 'operations'}_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            st.download_button("⬇️ Download Executive PDF",data=st.session_state.report_pdf,file_name=filename,mime="application/pdf",use_container_width=True)
            if st.session_state.report_generated_at: st.caption("Generated "+st.session_state.report_generated_at.strftime("%d %b %Y, %H:%M"))
        st.divider(); st.subheader("📧 Email Report")
        if not plan_config["email"]: st.info("Email delivery is available on Professional and Business plans.")
        else:
            recipient=st.text_input("Recipient email",value=manager_email,key="report_recipient")
            if st.button("📨 Email PDF Report",use_container_width=True):
                if not recipient.strip(): st.warning("Enter a recipient email address.")
                elif not st.session_state.report_pdf: st.warning("Generate the PDF first.")
                else:
                    try:
                        send_email_report(recipient.strip(),f"{company_name} - {report_name}","Please find attached the management report.\n\nGenerated by Generative Insight AI Operations Copilot.",st.session_state.report_pdf,"operations_report.pdf")
                        st.success("Report emailed successfully.")
                    except Exception as exc: st.error(f"Email failed: {exc}")
        st.divider(); st.subheader("📥 Data Exports")
        e1,e2=st.columns(2)
        with e1:
            team_df=result.get("team",pd.DataFrame())
            if isinstance(team_df,pd.DataFrame): st.download_button("⬇️ Team Analysis CSV",team_df.to_csv(index=False).encode("utf-8"),"team_analysis.csv","text/csv",use_container_width=True)
        with e2:
            if isinstance(actions_df,pd.DataFrame): st.download_button("⬇️ Action Plan CSV",actions_df.to_csv(index=False).encode("utf-8"),"action_plan.csv","text/csv",use_container_width=True)

with tabs[6]:
    st.subheader("💳 Subscription & Billing")
    st.info(f"You are currently using the **{st.session_state.user_plan}** plan.")
    show_pricing()
    st.caption("To activate real paid checkout, configure the plan checkout URLs in Streamlit Secrets using your payment provider.")

with st.expander("🧠 AI Analyst Context / Prompt",expanded=False):
    st.code(make_ai_prompt(result),language="text")

st.divider()
st.caption(f"© {datetime.now().year} Generative Insight · AI Operations Copilot v{APP_VERSION} · Validate AI recommendations before taking material business action.")
