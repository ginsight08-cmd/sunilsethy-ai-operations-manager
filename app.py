import io
import json
import smtplib
from datetime import datetime
from email.message import EmailMessage

import pandas as pd
import requests
import streamlit as st
from supabase import Client, create_client

from engine import analyze_data, make_ai_prompt


# ============================================================
# GENERATIVE INSIGHT
# AI OPERATIONS COPILOT
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
# CSS
#
# IMPORTANT:
# All HTML below uses st.markdown(...,
# unsafe_allow_html=True).
#
# DO NOT use st.code() for HTML UI.
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       STREAMLIT CHROME
       ======================================================== */

    #MainMenu {
        display: none !important;
        visibility: hidden !important;
    }

    footer {
        display: none !important;
        visibility: hidden !important;
    }

    [data-testid="stToolbar"] {
        display: none !important;
        visibility: hidden !important;
    }

    [data-testid="stDecoration"] {
        display: none !important;
        visibility: hidden !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }


    /* ========================================================
       APPLICATION
       ======================================================== */

    .stApp {
        background:
            radial-gradient(
                circle at top right,
                rgba(14, 165, 233, 0.08),
                transparent 36%
            ),
            linear-gradient(
                135deg,
                #ffffff 0%,
                #f8fbff 100%
            );
    }

    .block-container {
        max-width: 1280px !important;
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
    }


    /* ========================================================
       GENERATIVE INSIGHT BRAND
       ======================================================== */

    .gi-brand {
        margin-bottom: 1.4rem;
    }

    .gi-brand-name {
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.1;
        color: #071a3d;
        letter-spacing: -0.8px;
        margin-bottom: 0.35rem;
    }

    .gi-brand-name span {
        color: #1261d6;
    }

    .gi-tagline {
        font-size: 0.95rem;
        color: #64748b;
        margin-bottom: 0.25rem;
    }

    .gi-services {
        font-size: 0.82rem;
        color: #64748b;
    }

    .gi-services a {
        color: #1261d6;
        text-decoration: underline;
        font-weight: 600;
    }


    /* ========================================================
       HERO
       ======================================================== */

    .gi-hero {
        margin-top: 1rem;
        margin-bottom: 1.6rem;
        padding: 2.2rem 2.4rem;
        border-radius: 22px;

        border: 1px solid rgba(37, 99, 235, 0.14);

        background:
            radial-gradient(
                circle at top right,
                rgba(14, 165, 233, 0.10),
                transparent 40%
            ),
            linear-gradient(
                135deg,
                #eef7ff 0%,
                #f8fbff 55%,
                #ffffff 100%
            );

        box-shadow:
            0 10px 35px rgba(15, 23, 42, 0.05);
    }

    .gi-hero h1 {
        margin: 0;
        color: #071a3d;
        font-size: 2.45rem;
        line-height: 1.15;
        font-weight: 800;
        letter-spacing: -1px;
    }

    .gi-hero-subtitle {
        margin-top: 0.8rem;
        margin-bottom: 0.8rem;

        color: #1261d6;
        font-size: 1.15rem;
        font-weight: 700;
    }

    .gi-hero p {
        max-width: 850px;
        margin: 0;

        color: #475569;
        font-size: 1rem;
        line-height: 1.7;
    }


    /* ========================================================
       PLAN CARDS
       ======================================================== */

    .gi-plan-card {
        padding: 1.2rem;

        border: 1px solid #dbe7f5;
        border-radius: 16px;

        background: #ffffff;

        min-height: 250px;
    }


    /* ========================================================
       MOBILE
       ======================================================== */

    @media (max-width: 768px) {

        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        .gi-brand-name {
            font-size: 1.6rem;
        }

        .gi-hero {
            padding: 1.5rem;
            border-radius: 16px;
        }

        .gi-hero h1 {
            font-size: 1.8rem;
        }

        .gi-hero-subtitle {
            font-size: 1rem;
        }

    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPER
# ============================================================

def secret(name, default=""):
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default

    return value or default


# ============================================================
# CENTRALIZED KPI STATUS LOGIC
#
# Productivity = HIGHER is better
# Quality      = HIGHER is better
# SLA          = HIGHER is better
# AHT          = LOWER is better
# ============================================================

KPI_RULES = {
    "Productivity": {
        "higher_is_better": True,
        "unit": "%",
    },
    "Quality": {
        "higher_is_better": True,
        "unit": "%",
    },
    "SLA": {
        "higher_is_better": True,
        "unit": "%",
    },
    "AHT": {
        "higher_is_better": False,
        "unit": "",
    },
}


def get_kpi_status(kpi_name, actual, target):
    """
    ONE source of truth for KPI health.

    Productivity / Quality / SLA:
        actual >= target = GOOD

    AHT:
        actual <= target = GOOD
    """

    if kpi_name not in KPI_RULES:
        raise ValueError(
            f"Unknown KPI: {kpi_name}"
        )

    actual = float(actual)
    target = float(target)

    rule = KPI_RULES[kpi_name]

    if rule["higher_is_better"]:
        is_good = actual >= target
        delta_color = "normal"
    else:
        is_good = actual <= target
        delta_color = "inverse"

    gap = actual - target

    return {
        "name": kpi_name,
        "actual": actual,
        "target": target,
        "gap": gap,
        "is_good": is_good,
        "status": (
            "GOOD"
            if is_good
            else "NEEDS ATTENTION"
        ),
        "icon": (
            "🟢"
            if is_good
            else "🔴"
        ),
        "delta_color": delta_color,
        "unit": rule["unit"],
    }


def get_all_kpi_statuses(
    productivity,
    quality,
    sla,
    aht,
    productivity_target,
    quality_target,
    sla_target,
    aht_target,
):

    return {
        "Productivity": get_kpi_status(
            "Productivity",
            productivity,
            productivity_target,
        ),

        "Quality": get_kpi_status(
            "Quality",
            quality,
            quality_target,
        ),

        "SLA": get_kpi_status(
            "SLA",
            sla,
            sla_target,
        ),

        "AHT": get_kpi_status(
            "AHT",
            aht,
            aht_target,
        ),
    }


def format_kpi_value(status):

    if status["name"] == "AHT":
        return f"{status['actual']:.2f}"

    return f"{status['actual']:.2f}%"


def format_kpi_delta(status):

    if status["name"] == "AHT":
        return (
            f"{status['gap']:+.2f} vs target"
        )

    return (
        f"{status['gap']:+.2f}% vs target"
    )


# ============================================================
# SUPABASE
# ============================================================

def get_supabase_client() -> Client:

    url = secret("SUPABASE_URL")
    anon_key = secret("SUPABASE_ANON_KEY")

    if not url or not anon_key:
        raise RuntimeError(
            "Supabase authentication is not configured. "
            "Add SUPABASE_URL and SUPABASE_ANON_KEY "
            "to Streamlit Secrets."
        )

    return create_client(
        url,
        anon_key,
    )


def friendly_auth_error(error):

    message = str(
        getattr(
            error,
            "message",
            error,
        )
    )

    lowered = message.lower()

    if "invalid login credentials" in lowered:
        return "Invalid email or password."

    if "email not confirmed" in lowered:
        return (
            "Please verify your email address "
            "before signing in."
        )

    if "user already registered" in lowered:
        return (
            "An account with this email already exists. "
            "Please sign in."
        )

    if "password should be at least" in lowered:
        return (
            "Password does not meet Supabase's "
            "password requirements."
        )

    if "rate limit" in lowered:
        return (
            "Too many attempts. "
            "Please wait a moment and try again."
        )

    return message


def sign_up_user(
    full_name,
    company_name,
    email,
    password,
):

    supabase = get_supabase_client()

    return supabase.auth.sign_up(
        {
            "email": email.strip().lower(),
            "password": password,

            "options": {
                "data": {
                    "full_name": (
                        full_name.strip()
                    ),
                    "company_name": (
                        company_name.strip()
                    ),
                    "plan": "Free",
                }
            },
        }
    )


def sign_in_user(
    email,
    password,
):

    supabase = get_supabase_client()

    return supabase.auth.sign_in_with_password(
        {
            "email": (
                email.strip().lower()
            ),
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

    user = getattr(
        response,
        "user",
        None,
    )

    if user is None:
        raise RuntimeError(
            "Authentication succeeded but "
            "no user was returned."
        )

    metadata = (
        getattr(
            user,
            "user_metadata",
            {},
        )
        or {}
    )

    st.session_state.authenticated = True

    st.session_state.user_email = (
        user.email or ""
    ).lower()

    st.session_state.user_id = user.id

    st.session_state.user_name = (
        metadata.get(
            "full_name",
            "",
        )
    )

    st.session_state.company_name = (
        metadata.get(
            "company_name",
            "",
        )
    )

    st.session_state.user_plan = (
        metadata.get(
            "plan",
            "Free",
        )
        or "Free"
    )


# ============================================================
# PLANS
# ============================================================

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

    return configs.get(
        plan,
        configs["Free"],
    )


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

    clear_analysis()


# ============================================================
# N8N HELPERS
# ============================================================

def normalize_n8n_response(response):

    try:
        data = response.json()

    except ValueError:

        return {
            "answer": response.text
        }

    if isinstance(data, list) and data:
        data = data[0]

    if isinstance(data, dict):
        return data

    return {
        "answer": data
    }


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

        if text.startswith("```json"):
            text = text[7:].strip()

        elif text.startswith("```"):
            text = text[3:].strip()

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

    return df.to_string(
        index=False
    )


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

Productivity:
{float(overall["productivity"]):.2f}%
Target:
{productivity_target}%

Quality:
{float(overall["quality"]):.2f}%
Target:
{quality_target}%

SLA:
{float(overall["sla"]):.2f}%
Target:
{sla_target}%

Average AHT:
{float(overall["aht"]):.2f}
Target:
{aht_target}

Overall Risk:
{risk_level}

Operational Findings:
{dataframe_to_text(result.get("findings"))}

Recommended Actions:
{dataframe_to_text(result.get("actions"))}

Employee Risk:
{dataframe_to_text(result.get("employees"))}

Team Performance:
{dataframe_to_text(result.get("team"))}

KPI Summary:
{chr(10).join(summary_points)}
""".strip()


# ============================================================
# PDF
# ============================================================

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

    except ImportError as exc:

        raise RuntimeError(
            "PDF generation requires reportlab. "
            "Add reportlab to requirements.txt."
        ) from exc

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=(
            f"{company_name} - "
            f"{report_name}"
        ),
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

    story.append(
        Paragraph(
            "Generative Insight",
            title_style,
        )
    )

    story.append(
        Paragraph(
            (
                f"<b>{company_name}</b> — "
                f"{report_name}<br/>"
                f"Generated: "
                f"{datetime.now().strftime('%d %b %Y, %H:%M')}"
            ),
            body_style,
        )
    )

    story.append(
        Spacer(1, 8)
    )

    overall = result["overall"]

    targets = result.get(
        "_targets",
        {},
    )

    kpi_rows = [
        [
            "KPI",
            "Actual",
            "Target",
        ],

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

    story.append(
        Paragraph(
            "Executive Overview",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            f"<b>Risk:</b> {risk_level}",
            body_style,
        )
    )

    table = Table(
        kpi_rows,
        colWidths=[
            55 * mm,
            45 * mm,
            45 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#111827"
                    ),
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
                    0.35,
                    colors.grey,
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),

                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ]
        )
    )

    story.append(table)

    story.append(
        Paragraph(
            "KPI Summary",
            heading_style,
        )
    )

    for item in summary_points:

        clean_item = (
            item
            .replace("🔴 ", "")
            .replace("🟢 ", "")
            .replace("🟡 ", "")
            .replace("🟠 ", "")
        )

        story.append(
            Paragraph(
                clean_item,
                body_style,
            )
        )

    story.append(
        Paragraph(
            "Management Recommendation",
            heading_style,
        )
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

        if (
            isinstance(df, pd.DataFrame)
            and not df.empty
        ):

            story.append(
                Paragraph(
                    title,
                    heading_style,
                )
            )

            pdf_df = df.copy()

            if len(pdf_df.columns) > 8:
                pdf_df = pdf_df.iloc[:, :8]

            headers = [
                str(c)
                for c in pdf_df.columns
            ]

            rows = [headers]

            for _, row in pdf_df.head(50).iterrows():

                rows.append(
                    [
                        str(value)[:90]
                        for value in row.tolist()
                    ]
                )

            col_count = len(headers)

            width = (
                180 * mm
            ) / max(
                col_count,
                1,
            )

            table2 = Table(
                rows,
                colWidths=[
                    width
                    for _ in headers
                ],
                repeatRows=1,
            )

            table2.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor(
                                "#111827"
                            ),
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
                    ]
                )
            )

            story.append(table2)

            story.append(
                Spacer(1, 5)
            )

    story.append(
        Spacer(1, 8)
    )

    story.append(
        Paragraph(
            (
                "Generated by Generative Insight "
                "AI Operations Copilot. "
                "AI recommendations should be validated "
                "against operational evidence before "
                "management action."
            ),
            body_style,
        )
    )

    doc.build(story)

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# EMAIL
# ============================================================

def send_email_report(
    recipient,
    subject,
    body,
    pdf_bytes=None,
    pdf_filename="operations_report.pdf",
):

    smtp_host = secret("SMTP_HOST")
    smtp_port = int(
        secret(
            "SMTP_PORT",
            "587",
        )
    )

    smtp_user = secret(
        "SMTP_USERNAME"
    )

    smtp_password = secret(
        "SMTP_PASSWORD"
    )

    smtp_from = secret(
        "SMTP_FROM",
        smtp_user,
    )

    if not all(
        [
            smtp_host,
            smtp_user,
            smtp_password,
            smtp_from,
        ]
    ):
        raise RuntimeError(
            "SMTP settings are not configured."
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

        server.send_message(
            message
        )


# ============================================================
# PRICING
# ============================================================

def show_pricing():

    st.markdown(
        "### 💳 Plans"
    )

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
                if st.session_state.user_plan
                == "Free"
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

    for (
        col,
        name,
        price,
        features,
        button_text,
    ) in plans:

        with col:

            st.markdown(
                '<div class="gi-plan-card">',
                unsafe_allow_html=True,
            )

            st.markdown(
                f"#### {name}"
            )

            st.markdown(
                f"### {price}"
            )

            for feature in features:
                st.write(
                    f"✓ {feature}"
                )

            checkout_key = (
                f"{name.upper()}"
                "_CHECKOUT_URL"
            )

            checkout_url = secret(
                checkout_key
            )

            if checkout_url:

                st.link_button(
                    button_text,
                    checkout_url,
                    use_container_width=True,
                )

            else:

                st.button(
                    button_text,
                    use_container_width=True,
                    disabled=True,
                    key=(
                        f"disabled_"
                        f"{name}"
                    ),
                )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )


# ============================================================
# GENERATIVE INSIGHT BRAND HEADER
#
# IMPORTANT:
# This is st.markdown + unsafe_allow_html=True.
# It is NOT st.code().
# ============================================================

st.markdown(
    """
    <div class="gi-brand">

        <div class="gi-brand-name">
            Generative <span>Insight</span>
        </div>

        <div class="gi-tagline">
            Insights today. Intelligence tomorrow.
        </div>

        <div class="gi-services">
            AI / ML&nbsp;&nbsp;|&nbsp;&nbsp;
            Annotation&nbsp;&nbsp;|&nbsp;&nbsp;
            Web &amp; App Development
            &nbsp;&nbsp;·&nbsp;&nbsp;

            <a
                href="https://generativeinsight.in/"
                target="_blank"
                rel="noopener noreferrer"
            >
                Visit Website
            </a>
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# AI OPERATIONS HERO
#
# THIS FIXES THE <h1> / <div> ISSUE.
# ============================================================

st.markdown(
    """
    <section class="gi-hero">

        <h1>
            AI-powered operational intelligence
        </h1>

        <div class="gi-hero-subtitle">
            Turn operational data into management decisions.
        </div>

        <p>
            Create your account, upload Excel/CSV operational
            data, identify KPI risks, investigate team and
            employee performance, ask the AI Operations
            Copilot questions, and generate management-ready
            reports.
        </p>

    </section>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# AUTHENTICATION
# ============================================================

if not st.session_state.authenticated:

    if (
        not secret("SUPABASE_URL")
        or not secret("SUPABASE_ANON_KEY")
    ):

        st.error(
            "🔐 Authentication is not configured. "
            "Add SUPABASE_URL and SUPABASE_ANON_KEY "
            "in Streamlit Secrets."
        )

        st.stop()

    signup_tab, login_tab, pricing_tab = st.tabs(
        [
            "🆕 Create Account",
            "🔐 Sign In",
            "💳 Plans",
        ]
    )


    # ========================================================
    # SIGN UP
    # ========================================================

    with signup_tab:

        st.markdown(
            "### Create your Generative Insight account"
        )

        st.caption(
            "Start with the Free plan. "
            "You can upgrade later."
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
            )

            signup_confirm = st.text_input(
                "Confirm Password",
                type="password",
            )

            signup_submitted = (
                st.form_submit_button(
                    "🚀 Create Free Account",
                    type="primary",
                    use_container_width=True,
                )
            )

        if signup_submitted:

            if not signup_name.strip():

                st.warning(
                    "Please enter your full name."
                )

            elif not signup_company.strip():

                st.warning(
                    "Please enter your company "
                    "or organization."
                )

            elif (
                not signup_email.strip()
                or "@"
                not in signup_email
            ):

                st.warning(
                    "Please enter a valid "
                    "email address."
                )

            elif len(signup_password) < 6:

                st.warning(
                    "Please use a password with "
                    "at least 6 characters."
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

                        response = sign_up_user(
                            signup_name,
                            signup_company,
                            signup_email,
                            signup_password,
                        )

                    user = getattr(
                        response,
                        "user",
                        None,
                    )

                    session = getattr(
                        response,
                        "session",
                        None,
                    )

                    if (
                        user is not None
                        and session is not None
                    ):

                        set_authenticated_user(
                            response
                        )

                        st.success(
                            "✅ Account created successfully."
                        )

                        st.rerun()

                    elif user is not None:

                        st.success(
                            "✅ Account created. "
                            "Please verify your email "
                            "before signing in."
                        )

                    else:

                        st.info(
                            "Please check your email "
                            "for the verification link."
                        )

                except Exception as exc:

                    st.error(
                        "❌ Could not create account: "
                        f"{friendly_auth_error(exc)}"
                    )


    # ========================================================
    # LOGIN
    # ========================================================

    with login_tab:

        st.markdown(
            "### Welcome back"
        )

        with st.form(
            "login_form"
        ):

            login_email = st.text_input(
                "Email",
                placeholder="name@company.com",
            )

            login_password = st.text_input(
                "Password",
                type="password",
            )

            login_submitted = (
                st.form_submit_button(
                    "🔐 Sign In",
                    type="primary",
                    use_container_width=True,
                )
            )

        if login_submitted:

            if (
                not login_email.strip()
                or not login_password
            ):

                st.warning(
                    "Please enter your email "
                    "and password."
                )

            else:

                try:

                    with st.spinner(
                        "Signing you in..."
                    ):

                        response = sign_in_user(
                            login_email,
                            login_password,
                        )

                    set_authenticated_user(
                        response
                    )

                    st.success(
                        "✅ Signed in successfully."
                    )

                    st.rerun()

                except Exception as exc:

                    st.error(
                        "❌ Sign in failed: "
                        f"{friendly_auth_error(exc)}"
                    )

        st.info(
            "If email confirmation is enabled "
            "in Supabase, verify your email "
            "before signing in."
        )


    # ========================================================
    # PUBLIC PRICING
    # ========================================================

    with pricing_tab:
        show_pricing()

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

plan_config = get_plan_config(
    st.session_state.user_plan
)

with st.sidebar:

    st.markdown(
        "## 🤖 Generative Insight"
    )

    st.caption(
        "AI Operations Copilot"
    )

    st.success(
        f"Plan: **"
        f"{st.session_state.user_plan}"
        f"**"
    )

    if st.session_state.get(
        "user_name"
    ):

        st.caption(
            st.session_state.user_name
        )

    st.caption(
        st.session_state.user_email
    )

    st.divider()

    st.header(
        "⚙️ KPI Controls"
    )

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
    ):

        st.session_state.show_plans = True

    if st.button(
        "🔄 Reset Analysis",
        use_container_width=True,
    ):

        clear_analysis()
        st.rerun()

    if st.button(
        "🚪 Sign Out",
        use_container_width=True,
    ):

        clear_authentication()
        st.rerun()


if st.session_state.get(
    "show_plans"
):

    st.divider()

    show_pricing()

    st.divider()


# ============================================================
# APPLICATION HEADER
# ============================================================

st.markdown(
    "## 🤖 AI Operations Manager"
)

st.caption(
    "Executive operational intelligence → "
    "risk detection → AI decisions → "
    "action plans → management reports"
)


# ============================================================
# REPORT SETUP
# ============================================================

st.subheader(
    "🏢 Report Setup"
)

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
    type=[
        "xlsx",
        "xls",
        "csv",
    ],
)


if not uploaded:

    st.info(
        "Upload operational data to activate "
        "the executive dashboard."
    )

    st.markdown(
        "### Required columns"
    )

    st.code(
        "Date, Employee_ID, Employee_Name, Team, "
        "Target, Production, AHT_Actual, AHT_Target, "
        "Quality_%, SLA_%, Attendance, Error_Count, "
        "Error_Category"
    )

    st.markdown(
        "### What you get"
    )

    a, b, c, d = st.columns(4)

    a.metric(
        "Risk Detection",
        "✓",
    )

    b.metric(
        "Employee Risk",
        "✓",
    )

    c.metric(
        "AI Copilot",
        "✓",
    )

    d.metric(
        "Management Report",
        "✓",
    )

    st.stop()


# ============================================================
# FILE SIZE
# ============================================================

file_mb = (
    uploaded.size
    / (1024 * 1024)
)

if file_mb > plan_config["max_mb"]:

    st.error(
        f"File is {file_mb:.2f} MB. "
        f"Your {st.session_state.user_plan} "
        f"plan supports files up to "
        f"{plan_config['max_mb']} MB."
    )

    st.stop()


# ============================================================
# RESET WHEN NEW FILE
# ============================================================

if (
    st.session_state.file_name
    != uploaded.name
):

    st.session_state.file_name = (
        uploaded.name
    )

    st.session_state.n8n_sent = False
    st.session_state.n8n_result = None

    st.session_state.copilot_answer = None
    st.session_state.last_question = ""

    st.session_state.analysis_result = None
    st.session_state.analysis_df = None

    st.session_state.report_pdf = None
    st.session_state.report_generated_at = None


# ============================================================
# N8N URLs
# ============================================================

n8n_url = secret(
    "N8N_WEBHOOK_URL"
)

copilot_url = secret(
    "N8N_COPILOT_WEBHOOK_URL"
)


# ============================================================
# READ FILE
# ============================================================

try:

    uploaded.seek(0)

    if uploaded.name.lower().endswith(
        ".csv"
    ):

        df = pd.read_csv(
            uploaded
        )

    else:

        excel_file = pd.ExcelFile(
            uploaded
        )

        sheet_name = (
            "Operational_Data"
            if "Operational_Data"
            in excel_file.sheet_names
            else excel_file.sheet_names[0]
        )

        df = pd.read_excel(
            uploaded,
            sheet_name=sheet_name,
        )

except Exception as exc:

    st.error(
        f"❌ Could not read the uploaded file: "
        f"{exc}"
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

    st.write(
        missing_columns
    )

    st.stop()


# ============================================================
# ANALYZE
# ============================================================

try:

    result = analyze_data(
        df,
        productivity_target=(
            productivity_target
        ),
        quality_target=(
            quality_target
        ),
        sla_target=(
            sla_target
        ),
        aht_target=(
            aht_target
        ),
    )

except Exception as exc:

    st.error(
        f"❌ Analysis failed: {exc}"
    )

    st.stop()


st.session_state.analysis_result = result
st.session_state.analysis_df = df


# ============================================================
# KPI VALUES
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


# ============================================================
# CENTRAL KPI STATUS
# ============================================================

kpi_statuses = get_all_kpi_statuses(
    productivity,
    quality,
    sla,
    aht,
    productivity_target,
    quality_target,
    sla_target,
    aht_target,
)

productivity_status = (
    kpi_statuses["Productivity"]
)

quality_status = (
    kpi_statuses["Quality"]
)

sla_status = (
    kpi_statuses["SLA"]
)

aht_status = (
    kpi_statuses["AHT"]
)


# ============================================================
# RISK
# ============================================================

breaches = sum(
    not status["is_good"]
    for status
    in kpi_statuses.values()
)

if breaches == 0:

    risk_level = (
        "🟢 LOW RISK"
    )

elif breaches == 1:

    risk_level = (
        "🟡 MEDIUM RISK"
    )

elif breaches == 2:

    risk_level = (
        "🟠 HIGH RISK"
    )

else:

    risk_level = (
        "🔴 CRITICAL RISK"
    )


# ============================================================
# ACTION COUNTS
# ============================================================

actions_df = result.get(
    "actions",
    pd.DataFrame(),
)

action_count = (
    len(actions_df)
    if isinstance(
        actions_df,
        pd.DataFrame,
    )
    else 0
)

high_priority_count = 0

if (
    isinstance(
        actions_df,
        pd.DataFrame,
    )
    and not actions_df.empty
):

    for column in [
        "Priority",
        "priority",
        "Priority_Level",
        "priority_level",
    ]:

        if column in actions_df.columns:

            high_priority_count = len(
                actions_df[
                    actions_df[column]
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
# EXECUTIVE HEALTH HERO
# ============================================================

st.markdown(
    f"""
    <section class="gi-hero">

        <div class="gi-hero-subtitle">
            Executive Health: {risk_level}
        </div>

        <h1>
            {company_name or "Your organization"}
        </h1>

        <p>
            {report_name}
        </p>

    </section>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# EXECUTIVE METRICS
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
        delta=(
            f"{4 - breaches} on target"
        ),
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

        format_kpi_value(
            productivity_status
        ),

        delta=format_kpi_delta(
            productivity_status
        ),

        delta_color=(
            productivity_status[
                "delta_color"
            ]
        ),
    )


with k2:

    st.metric(
        "Quality",

        format_kpi_value(
            quality_status
        ),

        delta=format_kpi_delta(
            quality_status
        ),

        delta_color=(
            quality_status[
                "delta_color"
            ]
        ),
    )


with k3:

    st.metric(
        "SLA",

        format_kpi_value(
            sla_status
        ),

        delta=format_kpi_delta(
            sla_status
        ),

        delta_color=(
            sla_status[
                "delta_color"
            ]
        ),
    )


with k4:

    st.metric(
        "Average AHT",

        format_kpi_value(
            aht_status
        ),

        delta=format_kpi_delta(
            aht_status
        ),

        delta_color=(
            aht_status[
                "delta_color"
            ]
        ),
    )


# ============================================================
# EXECUTIVE SUMMARY
# ============================================================

summary_points = [

    (
        f"{productivity_status['icon']} "
        f"Productivity: "
        f"{productivity:.1f}% vs "
        f"{productivity_target}% target — "
        f"{productivity_status['status']}."
    ),

    (
        f"{quality_status['icon']} "
        f"Quality: "
        f"{quality:.1f}% vs "
        f"{quality_target}% target — "
        f"{quality_status['status']}."
    ),

    (
        f"{sla_status['icon']} "
        f"SLA: "
        f"{sla:.1f}% vs "
        f"{sla_target}% target — "
        f"{sla_status['status']}."
    ),

    (
        f"{aht_status['icon']} "
        f"AHT: "
        f"{aht:.1f} vs "
        f"{aht_target} target — "
        f"{aht_status['status']}."
    ),
]


if breaches >= 3:

    recommendation = (
        "Immediate management attention is recommended. "
        "Multiple KPI thresholds are breached. "
        "Prioritize root-cause analysis, targeted "
        "corrective actions, and close monitoring."
    )

elif breaches >= 1:

    recommendation = (
        "Management should review the affected KPIs, "
        "validate contributing factors, and initiate "
        "targeted corrective actions."
    )

else:

    recommendation = (
        "Operations are within defined KPI thresholds. "
        "Continue monitoring performance and maintain "
        "current processes."
    )


st.subheader(
    "🧠 Executive Summary"
)

for point in summary_points:

    st.write(point)

st.info(
    f"💡 **Management Recommendation:** "
    f"{recommendation}"
)


# ============================================================
# N8N AUTOMATION
# ============================================================

if (
    n8n_url
    and not st.session_state.n8n_sent
):

    if (
        not company_name.strip()
        or not manager_email.strip()
    ):

        st.warning(
            "Enter Company Name and Manager Email "
            "to run the configured n8n automation."
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
                "company_name": (
                    company_name.strip()
                ),
                "manager_email": (
                    manager_email.strip()
                ),
                "report_name": (
                    report_name.strip()
                ),
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
                    normalize_n8n_response(
                        response
                    )
                )

                st.session_state.n8n_sent = True

                st.success(
                    "✅ Operational automation completed."
                )

            else:

                st.error(
                    "❌ n8n workflow failed: "
                    f"HTTP {response.status_code}"
                )

                st.code(
                    response.text,
                    language="text",
                )

        except requests.exceptions.Timeout:

            st.warning(
                "⏱️ n8n timed out. "
                "The workflow may still be running."
            )

        except requests.exceptions.RequestException as exc:

            st.error(
                f"❌ Could not connect to n8n: {exc}"
            )


# ============================================================
# TABS
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
# TAB 1
# ============================================================

with tabs[0]:

    left, right = st.columns(
        [1.4, 1]
    )

    with left:

        st.subheader(
            "Team Performance"
        )

        team_df = result.get(
            "team",
            pd.DataFrame(),
        )

        if (
            isinstance(
                team_df,
                pd.DataFrame,
            )
            and not team_df.empty
        ):

            st.dataframe(
                team_df,
                use_container_width=True,
                hide_index=True,
            )

            if (
                "Team"
                in team_df.columns
                and "Productivity_%"
                in team_df.columns
            ):

                st.subheader(
                    "Productivity by Team"
                )

                st.bar_chart(
                    team_df.set_index(
                        "Team"
                    )[
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
            isinstance(
                employees,
                pd.DataFrame,
            )
            and not employees.empty
        ):

            st.metric(
                "Employees analyzed",
                len(employees),
            )

            if (
                "Risk_Score"
                in employees.columns
            ):

                st.metric(
                    "Highest employee risk score",
                    f"{employees['Risk_Score'].max():.2f}",
                )

        st.write(
            "**Current KPI position**"
        )

        for point in summary_points:

            st.write(point)


# ============================================================
# TAB 2
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
        isinstance(
            findings_df,
            pd.DataFrame,
        )
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
# TAB 3
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
        isinstance(
            employee_data,
            pd.DataFrame,
        )
        and not employee_data.empty
    ):

        sort_cols = [
            col
            for col in [
                "Risk_Score",
                "Avg_Productivity",
            ]
            if col in employee_data.columns
        ]

        if sort_cols:

            employee_data = (
                employee_data.sort_values(
                    sort_cols,
                    ascending=[
                        False
                        for _ in sort_cols
                    ],
                )
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
# TAB 4
# ============================================================

with tabs[3]:

    st.subheader(
        "✅ Recommended Actions"
    )

    if (
        isinstance(
            actions_df,
            pd.DataFrame,
        )
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
# TAB 5 - MANAGEMENT COPILOT
# ============================================================

with tabs[4]:

    st.subheader(
        "🤖 Management Copilot"
    )

    st.caption(
        "Ask questions about the uploaded operational "
        "data. The Copilot is instructed to use only "
        "the supplied operational context."
    )

    question = st.text_input(
        "Ask your operational question",

        placeholder=(
            "Which team has the quality drop "
            "and what action should be taken?"
        ),

        key="copilot_question",
    )

    ask_copilot = st.button(
        "🚀 Ask Management Copilot",
        type="primary",
        use_container_width=True,
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
                "company_name": (
                    company_name.strip()
                ),
                "report_name": (
                    report_name.strip()
                ),
                "context": context,
            }

            try:

                with st.spinner(
                    "🤖 Management Copilot is analyzing..."
                ):

                    response = requests.post(
                        copilot_url,
                        json=payload,
                        headers={
                            "Content-Type":
                            "application/json"
                        },
                        timeout=120,
                    )

                if response.status_code < 300:

                    raw = (
                        normalize_n8n_response(
                            response
                        )
                    )

                    answer = (
                        parse_ai_answer(
                            raw
                        )
                    )

                    st.session_state.copilot_answer = (
                        answer
                    )

                    st.session_state.last_question = (
                        question.strip()
                    )

                else:

                    st.session_state.copilot_answer = None

                    st.error(
                        "❌ Copilot workflow failed: "
                        f"HTTP {response.status_code}"
                    )

                    st.code(
                        response.text,
                        language="text",
                    )

            except requests.exceptions.Timeout:

                st.session_state.copilot_answer = None

                st.error(
                    "⏱️ Management Copilot timed out."
                )

            except requests.exceptions.ConnectionError:

                st.session_state.copilot_answer = None

                st.error(
                    "🔌 Could not connect to the "
                    "n8n Copilot webhook."
                )

            except requests.exceptions.RequestException as exc:

                st.session_state.copilot_answer = None

                st.error(
                    f"❌ Copilot request failed: {exc}"
                )

            except Exception as exc:

                st.session_state.copilot_answer = None

                st.error(
                    f"❌ Unexpected Copilot error: {exc}"
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

        answer = (
            st.session_state.copilot_answer
        )

        if isinstance(
            answer,
            dict,
        ):

            what = answer.get(
                "what_is_happening"
            )

            factors = answer.get(
                "contributing_factors",
                [],
            )

            recommended_actions = (
                answer.get(
                    "recommended_actions",
                    [],
                )
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

            if recommended_actions:

                st.markdown(
                    "#### ✅ Recommended Actions"
                )

                for index, action in enumerate(
                    recommended_actions,
                    1,
                ):

                    st.markdown(
                        f"**{index}.** {action}"
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

        elif isinstance(
            answer,
            str,
        ):

            st.markdown(answer)

        else:

            st.code(
                str(answer),
                language="text",
            )


# ============================================================
# TAB 6 - REPORTS
# ============================================================

with tabs[5]:

    st.subheader(
        "📄 Management Reports"
    )

    if not plan_config["pdf"]:

        st.warning(
            "PDF reporting is not available "
            "on your current plan."
        )

    else:

        report_result = dict(
            result
        )

        report_result["_targets"] = {

            "productivity":
                productivity_target,

            "quality":
                quality_target,

            "sla":
                sla_target,

            "aht":
                aht_target,
        }

        if st.button(
            "📄 Generate Executive PDF",
            type="primary",
            use_container_width=True,
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

                st.session_state.report_pdf = (
                    pdf
                )

                st.session_state.report_generated_at = (
                    datetime.now()
                )

            except Exception as exc:

                st.error(
                    f"❌ Could not generate PDF: {exc}"
                )


        if st.session_state.report_pdf:

            filename = (
                f"{company_name or 'operations'}_"
                f"report_"
                f"{datetime.now().strftime('%Y%m%d_%H%M')}"
                ".pdf"
            )

            st.download_button(
                "⬇️ Download Executive PDF",
                data=(
                    st.session_state.report_pdf
                ),
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
            )

            if (
                st.session_state.report_generated_at
            ):

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

                            (
                                f"{company_name} - "
                                f"{report_name}"
                            ),

                            (
                                "Please find attached the "
                                "management report for "
                                f"{company_name or 'your organization'}.\n\n"
                                "Generated by Generative Insight "
                                "AI Operations Copilot."
                            ),

                            st.session_state.report_pdf,

                            "operations_report.pdf",
                        )

                        st.success(
                            "✅ Report emailed successfully."
                        )

                    except Exception as exc:

                        st.error(
                            f"❌ Email failed: {exc}"
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
                )


# ============================================================
# TAB 7 - BILLING
# ============================================================

with tabs[6]:

    st.subheader(
        "💳 Subscription & Billing"
    )

    st.info(
        "You are currently using the "
        f"**{st.session_state.user_plan}** plan."
    )

    show_pricing()

    st.caption(
        "Configure your payment-provider checkout "
        "URLs in Streamlit Secrets to activate "
        "real paid checkout."
    )


# ============================================================
# AI PROMPT / DEBUG
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

st.caption(
    f"© {datetime.now().year} "
    f"Generative Insight · "
    f"AI Operations Copilot v{APP_VERSION} · "
    "Validate AI recommendations before taking "
    "material business action."
)
