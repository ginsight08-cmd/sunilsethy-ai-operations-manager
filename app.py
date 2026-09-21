import io
import time
import json
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from email.message import EmailMessage
from urllib.parse import urlparse

import pandas as pd
import altair as alt
import requests
import streamlit as st
from supabase import create_client, Client

from engine import analyze_data, make_ai_prompt
import procurement_engine
import case_management_engine
import vakil_case_manager
from work_hub import render_work_hub
from operations_excellence import render_operations_excellence


# ============================================================
# GENERATIVE INSIGHT | AI OPERATIONS COPILOT
# Complete Streamlit application
# ============================================================

from product_deployment import PRODUCTS, validate_deployment
from bpo_trends import render_bpo_trends

PRODUCT_ID = globals().get("DEPLOYMENT_PRODUCT")
PRODUCT = PRODUCTS[PRODUCT_ID] if PRODUCT_ID else None
PRODUCT_NAME = PRODUCT["name"] if PRODUCT else "AI Operations Copilot"
USE_NEON = bool(PRODUCT)
APP_NAME = f"Generative Insight | {PRODUCT_NAME}"
APP_VERSION = "1.0.0"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="assets/generative-insight-gi-mark-transparent.png",
    layout="wide",
    # "auto" keeps the desktop sidebar visible while allowing Streamlit
    # to start with a compact/collapsed navigation experience on phones.
    initial_sidebar_state="auto",
)


# ============================================================
# BRAND CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

# Brand image assets — keep BOTH files inside the assets/ folder.
# Horizontal wordmark: headers, auth topbar, sidebar.
# Square GI mark: favicon/page icon and 40–56 px badges.
HEADER_LOGO_PATH = BASE_DIR / "assets" / "generative-insight-logo-header-transparent.png"
MARK_LOGO_PATH = BASE_DIR / "assets" / "generative-insight-gi-mark-transparent.png"

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
    "supabase_access_token": "",
    "supabase_refresh_token": "",
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
    "account_created_at": "",
    # Free-tier (₹299/mo, post 3-day trial) billing — tracked
    # separately from the Professional Razorpay fields above so the
    # two subscriptions never collide.
    "free_billing_status": "",
    "free_subscription_id": "",
    "razorpay_checkout_url_free": "",
    # Industry — switchable anytime from the sidebar. "BPO" uses the
    # existing Productivity/Quality/SLA/AHT engine; "Manufacturing" uses
    # the separate procurement/vendor-comparison engine below.
    "industry": "BPO",
    "manufacturing_file_name": "",
    "manufacturing_result": None,
    "manufacturing_report_bytes": None,
    "manufacturing_report_generated_at": None,
    "case_file_name": "",
    "case_working_df": None,
    "case_audit_log": [],
}

# Free plan trial length. After this many days on the Free plan,
# the dashboard is locked and the user is shown an upgrade-only screen.
FREE_TRIAL_DAYS = 3

# ============================================================
# INDUSTRY REGISTRY
# Single source of truth for the sidebar dropdown. "built" industries
# have a real, complete flow (their own upload, engine, tabs, insights).
# Everything else in this dict shows a graceful "coming soon" screen
# instead of crashing or showing fake data — add a new engine module
# (like procurement_engine.py) and flip it into BUILT_INDUSTRIES when
# a module is ready.
# ============================================================

INDUSTRY_LABELS = {
    "BPO": "BPO / Call Center Operations",
    "Manufacturing": "Manufacturing (Procurement)",
    "CaseManagement": "Vakil / Legal Case Management",
    "Retail": "Retail / E-commerce",
    "Logistics": "Logistics / Delivery",
    "Healthcare": "Healthcare / Clinics",
}

BUILT_INDUSTRIES = {"BPO", "Manufacturing", "CaseManagement"}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# BRAND THEME
# ============================================================

st.markdown(
    f"""
<style>

    /* ============================================================
       DESIGN TOKENS — matched to the approved mockups: minimal
       black/white surface, green for "good"/Free, amber for trial
       urgency, red for risk, blue reserved for links/the "Insight"
       wordmark accent. Card shapes, spacing, and button style below
       all follow the mockups; every widget/function is unchanged.
       ============================================================ */
    :root {{
        --ink: #0F1115;
        --ink-soft: #4B5262;
        --muted: #6B7280;
        --paper: #FFFFFF;
        --bg: #FAFAFA;
        --border: #E7E8EC;
        --border-soft: #EFEFF2;
        --black: #111114;
        --black-hover: #26272C;
        --green-bg: #E8F8EE;
        --green-ink: #1D8A4A;
        --amber-bg: #FDF3DA;
        --amber-ink: #8A6100;
        --red-bg: #FDEBEC;
        --red-ink: #B42318;
        --blue-link: {BRAND_BLUE};
        --radius-lg: 20px;
        --radius-md: 14px;
        --radius-sm: 10px;
        --shadow-card: 0 1px 2px rgba(15,17,21,0.04), 0 8px 20px rgba(15,17,21,0.04);
    }}

    .stApp {{
        background: var(--bg);
    }}

    .main {{
        padding-top: 0.6rem;
    }}

    /* ---------- Typography ---------- */
    .main-title {{
        font-size: 2.1rem;
        font-weight: 800;
        color: var(--ink);
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }}

    .brand-subtitle {{
        color: var(--muted) !important;
        -webkit-text-fill-color: var(--muted) !important;
        font-size: 1rem;
        font-weight: 500;
        margin-bottom: 1rem;
        opacity: 1 !important;
        visibility: visible !important;
    }}

    /* ---------- Logo mark (dedicated GI mark when assets/generative-insight-gi-mark-transparent.png
       exists — see logo_mark_html(); falls back to a CSS-drawn black
       rounded-square sparkle icon only when no logo file is present). ---------- */
    .gi-logo-mark {{
        width: 100px; height: 40px; border-radius: 11px;
        background: var(--black);
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 18px; color: #FFFFFF; flex-shrink: 0;
        box-shadow: 0 2px 6px rgba(17,17,20,0.25);
    }}
    .gi-brand-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 2px; }}

    /* ---------- Auth screen — matched to the provided reference
       design (Tailwind neutral-950/500/200 palette, rounded-2xl
       card, size-14 icon badge). Same form fields/logic underneath,
       purely presentational wrapper. ---------- */
    .gi-auth-topbar {{
        display: flex; align-items: center; justify-content: space-between;
        padding: 18px 8px; border-bottom: 1px solid #E5E5E5;
        margin-bottom: 8px;
    }}
    .gi-auth-icon-sm {{
        width: 40px; height: 40px; border-radius: 12px;
        background: #0A0A0A; color: #FFFFFF;
        display: flex; align-items: center; justify-content: center;
        font-size: 18px; flex-shrink: 0;
    }}
    .gi-auth-icon-lg {{
        width: 56px; height: 56px; border-radius: 16px;
        background: #0A0A0A; color: #FFFFFF;
        display: flex; align-items: center; justify-content: center;
        font-size: 26px; margin: 0 auto 14px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }}
    .gi-auth-hero {{ text-align: center; margin-bottom: 4px; }}
    .gi-auth-hero-title {{
        font-size: 1.85rem; font-weight: 700; letter-spacing: -0.02em;
        color: #0A0A0A; margin-bottom: 6px;
    }}
    .gi-auth-hero-sub {{
        font-size: 0.9rem; color: #737373; max-width: 380px;
        margin: 0 auto;
    }}
    .gi-auth-card-title {{
        font-size: 1.25rem; font-weight: 700; color: #0A0A0A;
        margin-bottom: 2px;
    }}
    .gi-auth-card-desc {{
        font-size: 0.88rem; color: #737373; margin-bottom: 18px;
    }}
    .gi-field-label-row {{
        display: flex; align-items: center; gap: 7px;
        font-size: 0.85rem; font-weight: 600; color: #0A0A0A;
        margin-bottom: 4px; margin-top: 2px;
    }}
    .gi-auth-footer-note {{
        text-align: center; font-size: 0.78rem; color: #737373;
        margin-top: 18px; line-height: 1.5;
    }}
    .gi-auth-shell {{
        max-width: 460px; margin: 8px auto 0;
        background: #FFFFFF; border: 1px solid #E5E5E5;
        border-radius: 16px; padding: 2rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }}

    /* Compact, centered account panel on laptop screens. The marker is
       rendered only inside the Create Account tab, so pricing remains wide. */
    [role="tabpanel"]:has(.gi-signup-marker) {{
        width: min(100%, 480px);
        margin-inline: auto;
        padding-top: 1rem;
    }}

    [role="tabpanel"]:has(.gi-signup-marker) [data-testid="stVerticalBlockBorderWrapper"] {{
        background: #FFFFFF;
        border-radius: 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,.04);
    }}

    .gi-auth-hero-logo {{
        width: clamp(104px, 10vw, 142px);
        height: auto;
        display: block;
        margin: 0 auto 14px;
        object-fit: contain;
    }}

    /* Authentication navigation sits directly beneath the brand header. */
    body:has(.gi-auth-tabs-marker) .main .block-container {{
        position: relative !important;
    }}

    body:has(.gi-auth-tabs-marker) [role="tablist"] {{
        position: relative !important;
        z-index: 20 !important;
        justify-content: flex-end !important;
        align-items: center !important;
        gap: 1.25rem !important;
        width: max-content !important;
        max-width: 68%;
        min-height: 42px;
        margin: 0 0 -42px auto !important;
        transform: translateY(-63px) !important;
        padding: 0 !important;
        border-bottom: 0 !important;
        background: transparent !important;
    }}

    body:has(.gi-auth-tabs-marker) [role="tab"] {{
        position: relative !important;
        min-height: 42px !important;
        padding: 0 .15rem !important;
        border-radius: 0 !important;
        color: #737373 !important;
        font-size: .88rem !important;
        font-weight: 600 !important;
    }}

    body:has(.gi-auth-tabs-marker) [role="tab"][aria-selected="true"],
    body:has(.gi-auth-tabs-marker) [role="tab"][aria-selected="true"] * {{
        color: #0A0A0A !important;
        -webkit-text-fill-color: #0A0A0A !important;
    }}

    body:has(.gi-auth-tabs-marker) [role="tab"][aria-selected="true"]::after {{
        content:"";
        position:absolute;
        left:0; right:0; bottom:0;
        height: 2px !important;
        background: #0A0A0A !important;
    }}

    body:has(.gi-auth-tabs-marker) [role="tablist"] [data-baseweb="tab-highlight"],
    body:has(.gi-auth-tabs-marker) [role="tablist"] [data-baseweb="tab-border"] {{
        display:none !important;
    }}

    .gi-brand {{
        font-size: 1.3rem;
        font-weight: 800;
        color: var(--ink);
        letter-spacing: -0.02em;
        line-height: 1.15;
    }}

    .gi-brand span {{
        color: var(--blue-link);
    }}

    .gi-tagline {{
        color: var(--muted);
        font-size: 0.78rem;
        margin-top: 0.1rem;
    }}

    /* ---------- Hero / info cards ---------- */
    .hero {{
        padding: 1.4rem 1.6rem;
        border-radius: var(--radius-lg);
        border: 1px solid var(--border);
        background: var(--paper);
        box-shadow: var(--shadow-card);
        margin-bottom: 1.2rem;
    }}

    .small-muted {{
        color: var(--muted);
        font-size: .88rem;
    }}

    /* ---------- st.metric cards ---------- */
    div[data-testid="stMetric"]industry flow: upload a Price Comparative Sheet workbook
    (one sheet per Purchase Requisition, multiple vendor quote blocks per
    sheet), get vendor-comparison analysis, recommended vendor per item,
    savings vs alternatives, and risk flags. Uses procurement_engine.py,
    a self-contained module with no dependency on engine.py / analyze_data.
    """

    st.subheader("🏭 Procurement Setup")

    col1, col2 = st.columns(2)
    with col1:
        company_name = st.text_input(
            "Company Name",
            value=st.session_state.get("company_name", ""),
            placeholder="e.g. ABC Manufacturing Pvt. Ltd.",
            key="mfg_company_name",
        )
    with col2:
        report_name = st.text_input(
            "Report Name",
            value="Procurement Price Comparison",
            key="mfg_report_name",
        )

    uploaded = st.file_uploader(
        f"📁 Upload Price Comparative Sheet workbook (.xlsx) — max {plan_config['max_mb']} MB",
        type=["xlsx"],
        key="mfg_file_uploader",
    )

    if not uploaded:
        st.info(
            "Upload a Price Comparative Sheet workbook to compare vendor quotes, "
            "identify the best price per item, and flag procurement risks."
        )
        st.markdown("### Expected format")
        st.caption(
            "One sheet per Purchase Requisition. Each sheet needs a header row with "
            "S.N., PR NO, Item Code, Item Name, Qty, UM, then one 5-column block per "
            "vendor (Make, Quoted Price, Dis %, Dis Price, Total Price), followed by "
            "Doc. Date, Vendor, and DPTPL (previous order unit price) columns."
        )
        st.markdown("### What you get")
        a, b, c, d = st.columns(4)
        with a:
            render_check_card("Vendor Comparison")
        with b:
            render_check_card("Recommended Vendor")
        with c:
            render_check_card("Savings Analysis")
        with d:
            render_check_card("Risk Flags")
        render_footer()
        return

    file_mb = uploaded.size / (1024 * 1024)
    if file_mb > plan_config["max_mb"]:
        st.error(
            f"File is {file_mb:.2f} MB. Your {st.session_state.user_plan} plan "
            f"supports files up to {plan_config['max_mb']} MB."
        )
        render_footer()
        return

    if st.session_state.manufacturing_file_name != uploaded.name:
        st.session_state.manufacturing_file_name = uploaded.name
        st.session_state.manufacturing_result = None
        st.session_state.manufacturing_report_bytes = None

    _mfg_start_time = time.time()

    try:
        with st.spinner("🔄 Fetching and reading your procurement workbook..."):
            prs = procurement_engine.parse_workbook(uploaded)
            if not prs:
                st.error(
                    "❌ No Price Comparative Sheet-style data found in this workbook. "
                    "Check that at least one sheet has a header row starting with 'S.N.'"
                )
                render_footer()
                return
        require_trial_analysis(uploaded, "Manufacturing")
        with st.spinner("🧠 Comparing vendor quotes and flagging risk..."):
            result = procurement_engine.analyze_procurement(prs)
    except Exception as e:
        st.error(f"❌ Could not analyze the uploaded file: {e}")
        render_footer()
        return

    _mfg_elapsed = time.time() - _mfg_start_time

    st.session_state.manufacturing_result = result
    overall = result["overall"]

    st.markdown(
        f"""<div class="hero">
<h3>Procurement Overview</h3>
<p class="small-muted">{company_name or "Your organization"} · {report_name}</p>
<p class="small-muted">⏱️ Data fetched and analyzed in {_mfg_elapsed:.2f}s · {overall['total_items']} item(s) across {overall['total_prs']} PR sheet(s)</p>
</div>""",
        unsafe_allow_html=True,
    )

    r1, r2, r3, r4 = st.columns(4)
    with r1:
        render_metric_card("💰", "Recommended Spend", f"₹{overall['total_recommended_spend']:,.0f}")
    with r2:
        render_metric_card("🔎", "Highest-Quote Spend", f"₹{overall['total_highest_quote_spend']:,.0f}")
    with r3:
        render_metric_card(
            "📉", "Potential Savings", f"₹{overall['total_potential_savings']:,.0f}",
            delta=f"{overall['overall_savings_pct']}%" if overall['overall_savings_pct'] is not None else None,
            delta_tone="good" if (overall['overall_savings_pct'] or 0) > 0 else "neutral",
        )
    with r4:
        render_metric_card("📋", "Purchase Requisitions", overall["total_prs"])

    risk1, risk2, risk3 = st.columns(3)
    with risk1:
        render_metric_card(
            "⚠️", "Single-Vendor Items", overall["total_single_vendor_items"],
            delta_tone="bad" if overall["total_single_vendor_items"] > 0 else "good",
        )
    with risk2:
        render_metric_card(
            "📈", "Price-Increase Items", overall["total_price_increase_items"],
            delta_tone="bad" if overall["total_price_increase_items"] > 0 else "good",
        )
    with risk3:
        render_metric_card(
            "❓", "No-Quote Items", overall["total_no_quote_items"],
            delta_tone="bad" if overall["total_no_quote_items"] > 0 else "good",
        )

    # ============================================================
    # EXECUTIVE SUMMARY — risk level, summary bullets, and the
    # recommendation are all computed once in procurement_engine.py
    # (single source of truth shared with the Excel report and the
    # AI Copilot context), mirroring the BPO engine's insight pattern.
    # ============================================================

    mfg_insights = procurement_engine.build_insights(result)
    mfg_risk_level = mfg_insights["risk_level"]
    mfg_summary_points = mfg_insights["summary_points"]
    mfg_recommendation = mfg_insights["recommendation"]

    st.subheader("🧠 Executive Summary")
    render_risk_card("🚦", "Procurement Risk", mfg_risk_level)
    for point in mfg_summary_points:
        st.write(point)
    st.info(f"💡 **Procurement Recommendation:** {mfg_recommendation}")

    mfg_tabs = st.tabs(["📋 PR Summary", "📦 Item Detail", "⚠️ Risk Items", "🤖 Procurement Copilot", "📄 Report", "💳 Billing"])

    with mfg_tabs[0]:
        st.subheader("Purchase Requisition Summary")
        pr_df = pd.DataFrame(result["pr_rows"])
        if not pr_df.empty:
            render_searchable_procurement_table(
                pr_df,
                "procurement_pr_summary",
                "procurement_pr_summary.csv",
            )
        else:
            st.info("No PR-level data available.")

    with mfg_tabs[1]:
        st.subheader("Item-Level Comparison")
        item_df = pd.DataFrame(result["item_rows"])
        if not item_df.empty:
            render_searchable_procurement_table(
                item_df,
                "procurement_item_detail",
                "procurement_item_detail.csv",
            )
        else:
            st.info("No item-level data available.")

    with mfg_tabs[2]:
        st.subheader("⚠️ Flagged Items")
        item_df = pd.DataFrame(result["item_rows"])
        if not item_df.empty:
            risk_df = item_df[item_df["Risk Flags"].astype(str).str.len() > 0]
            if not risk_df.empty:
                render_searchable_procurement_table(
                    risk_df,
                    "procurement_risk_items",
                    "procurement_risk_items.csv",
                )
            else:
                st.success("✅ No flagged items — every item has multiple quotes with no unusual price movement.")
        else:
            st.info("No item-level data available.")

    with mfg_tabs[3]:
        st.subheader("🤖 Procurement Copilot")
        st.caption(
            "Ask questions about this procurement data. The Copilot is "
            "instructed to use only the supplied vendor comparison context."
        )

        mfg_question = st.text_input(
            "Ask your procurement question",
            placeholder="Which items have the biggest savings opportunity and which vendor should we use?",
            key="mfg_copilot_question",
        )

        mfg_ask_copilot = st.button(
            "🚀 Ask Procurement Copilot",
            type="primary",
            use_container_width=True,
            key="mfg_ask_copilot",
        )

        mfg_copilot_url = secret("N8N_COPILOT_WEBHOOK_URL")

        if mfg_ask_copilot:
            if not mfg_question.strip():
                st.warning("⚠️ Please enter a question first.")
            elif not mfg_copilot_url:
                st.error("❌ N8N_COPILOT_WEBHOOK_URL is not configured in Streamlit Secrets.")
            else:
                mfg_context = (
                    f"Company:\n{company_name}\n\nReport:\n{report_name}\n\n"
                    + procurement_engine.make_ai_prompt(result, mfg_insights)
                )
                mfg_payload = {
                    "question": mfg_question.strip(),
                    "company_name": company_name.strip(),
                    "report_name": report_name.strip(),
                    "context": mfg_context,
                    "user_id": st.session_state.user_id,
                    "user_email": st.session_state.user_email,
                }
                try:
                    with st.spinner("🤖 Procurement Copilot is analyzing..."):
                        mfg_copilot_response = requests.post(
                            mfg_copilot_url,
                            json=mfg_payload,
                            headers={"Content-Type": "application/json"},
                            timeout=120,
                        )
                    if mfg_copilot_response.status_code < 300:
                        mfg_raw = normalize_n8n_response(mfg_copilot_response)
                        st.session_state.copilot_answer = parse_ai_answer(mfg_raw)
                        st.session_state.last_question = mfg_question.strip()
                    else:
                        st.session_state.copilot_answer = None
                        st.error(f"❌ Copilot workflow failed: HTTP {mfg_copilot_response.status_code}")
                        st.code(mfg_copilot_response.text, language="text")
                except requests.exceptions.Timeout:
                    st.session_state.copilot_answer = None
                    st.error("⏱️ Procurement Copilot timed out. Please try again.")
                except requests.exceptions.RequestException as e:
                    st.session_state.copilot_answer = None
                    st.error(f"❌ Copilot request failed: {e}")

        if st.session_state.copilot_answer:
            st.divider()
            st.markdown("### 🧠 Copilot Analysis")
            st.caption("Question: " + st.session_state.last_question)
            mfg_answer = st.session_state.copilot_answer
            if isinstance(mfg_answer, dict):
                if mfg_answer.get("what_is_happening"):
                    st.markdown("#### 🔎 What is happening")
                    st.info(mfg_answer["what_is_happening"])
                if mfg_answer.get("recommended_actions"):
                    st.markdown("#### ✅ Recommended Actions")
                    for i, action in enumerate(mfg_answer["recommended_actions"], 1):
                        st.markdown(f"**{i}.** {action}")
            elif isinstance(mfg_answer, str):
                st.markdown(mfg_answer)
            else:
                st.code(str(mfg_answer), language="text")

    with mfg_tabs[4]:
        st.subheader("📄 Procurement Report")
        if st.button("📄 Generate Report", type="primary", use_container_width=True, key="mfg_generate_report"):
            try:
                with st.spinner("Generating procurement report..."):
                    report_bytes = build_procurement_report_bytes(prs, result)
                st.session_state.manufacturing_report_bytes = report_bytes
                st.session_state.manufacturing_report_generated_at = datetime.now()
            except Exception as e:
                st.error(f"❌ Could not generate report: {e}")

        if st.session_state.manufacturing_report_bytes:
            filename = (
                f"{company_name or 'procurement'}_comparison_"
                f"{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            )
            st.download_button(
                "⬇️ Download Procurement Report (.xlsx)",
                data=st.session_state.manufacturing_report_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="mfg_download_report",
            )
            if st.session_state.manufacturing_report_generated_at:
                st.caption(
                    "Generated "
                    + st.session_state.manufacturing_report_generated_at.strftime("%d %b %Y, %H:%M")
                )

    with mfg_tabs[5]:
        st.subheader("💳 Subscription & Billing")
        st.info(f"You are currently using the **{st.session_state.user_plan}** plan.")
        show_pricing("billing_manufacturing")

    with st.expander("🧠 AI Analyst Context / Prompt", expanded=False):
        st.code(procurement_engine.make_ai_prompt(result, mfg_insights), language="text")

    render_footer()


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


def razorpay_is_configured(plan_id_secret="RAZORPAY_PROFESSIONAL_PLAN_ID"):
    return all(
        [
            secret("RAZORPAY_KEY_ID"),
            secret("RAZORPAY_KEY_SECRET"),
            secret(plan_id_secret),
        ]
    )


def create_razorpay_subscription(
    customer_email="",
    customer_name="",
    plan_id_secret="RAZORPAY_PROFESSIONAL_PLAN_ID",
    plan_label="Professional",
    total_count_secret="RAZORPAY_PROFESSIONAL_TOTAL_COUNT",
):
    key_id = secret("RAZORPAY_KEY_ID")
    key_secret = secret("RAZORPAY_KEY_SECRET")
    plan_id = secret(plan_id_secret)

    if not key_id or not key_secret or not plan_id:
        raise RuntimeError(
            f"Razorpay is not configured. Add RAZORPAY_KEY_ID, "
            f"RAZORPAY_KEY_SECRET and {plan_id_secret} "
            "to Streamlit Secrets."
        )

    raw_total_count = secret(total_count_secret, "12")
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
            "plan": plan_label,
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
            "₹299/mo",
            [
                f"{FREE_TRIAL_DAYS}-day trial: {FREE_TRIAL_ANALYSES} analyses total",
                "5 MB file limit",
                "Dashboard analytics",
                "AI Copilot",
                "PDF report",
            ],
            (
                "Current plan"
                if st.session_state.user_plan == "Free"
                else "Start Free Trial"
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
                "Free": ("🌱", f"{FREE_TRIAL_DAYS} days free, then ₹299/mo"),
                "Professional": ("🚀", "Advanced intelligence & automation"),
                "Business": ("🏢", "Scale AI operations across teams"),
            }
            icon, description = plan_visuals.get(name, ("✨", "Operational intelligence"))
            popular_badge = '<div class="plan-badge-popular">Most popular</div>' if name == "Professional" else ""

            st.markdown(
                f'''<div class="plan-card">{popular_badge}
<div class="plan-icon-badge">{icon}</div>
<div class="plan-name" style="font-size:1.15rem; font-weight:800;">{name}</div>
<div class="plan-price" style="font-size:1.65rem; font-weight:850; margin:.35rem 0;">{price}</div>
<div class="plan-description" style="font-size:.86rem; margin-bottom:.8rem;">{description}</div>
{''.join(f'<div class="plan-feature" style="margin:.35rem 0;">✓ {feature}</div>' for feature in features)}
</div>''',
                unsafe_allow_html=True,
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
                        ready, message = razorpay_activation_ready()
                        if not ready:
                            st.error(f"❌ {message}")
                        else:
                            subscription = None
                            try:
                                with st.spinner("Creating secure Razorpay subscription..."):
                                    subscription = create_razorpay_subscription(
                                        customer_email=st.session_state.get("user_email", ""),
                                        customer_name=st.session_state.get("user_name", ""),
                                    )
                            except Exception as exc:
                                st.session_state.razorpay_checkout_url = ""
                                st.error(f"❌ Razorpay could not create the subscription: {exc}")

                            if subscription is not None:
                                try:
                                    # Save tracking first. Checkout URL is exposed only after
                                    # Supabase tracking succeeds, eliminating the previous
                                    # "checkout created but subscription tracking could not be saved" state.
                                    update_user_plan(
                                        "Free",
                                        subscription["id"],
                                        subscription.get("status", "created"),
                                    )
                                    st.session_state.razorpay_checkout_url = subscription["short_url"]
                                    st.session_state.razorpay_subscription_id = subscription["id"]
                                    st.success("Subscription created. Continue to secure Razorpay checkout.")
                                except Exception as exc:
                                    st.session_state.razorpay_checkout_url = ""
                                    st.error(
                                        f"❌ Razorpay subscription {subscription['id']} was created, "
                                        f"but saving it to your account (Supabase) failed: {exc}\n\n"
                                        "This usually means SUPABASE_SERVICE_ROLE_KEY is missing, wrong, "
                                        "or swapped with the anon key in Streamlit Secrets."
                                    )

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

            elif name == "Free":
                if free_billing_is_active():
                    st.button(
                        "✅ Active (₹299/mo)",
                        use_container_width=True,
                        disabled=True,
                        key=f"free_active_{section_id}",
                    )
                elif st.session_state.user_plan != "Free":
                    st.button(
                        "Included",
                        use_container_width=True,
                        disabled=True,
                        key=f"free_included_{section_id}",
                    )
                elif not razorpay_is_configured("RAZORPAY_FREE_PLAN_ID"):
                    st.button(
                        button,
                        use_container_width=True,
                        disabled=True,
                        key=f"free_disabled_{section_id}",
                    )
                    st.caption("Razorpay checkout for this plan is not configured yet.")
                else:
                    _remaining = trial_days_remaining()
                    _label = (
                        "💳 Continue for ₹299/mo"
                        if _remaining is not None and _remaining <= 0
                        else "💳 Start Free Trial"
                    )
                    if st.button(
                        _label,
                        use_container_width=True,
                        key=f"razorpay_free_{section_id}",
                    ):
                        ready, message = razorpay_activation_ready("RAZORPAY_FREE_PLAN_ID", "Free")
                        if not ready:
                            st.error(f"❌ {message}")
                        else:
                            subscription = None
                            try:
                                with st.spinner("Creating secure Razorpay subscription..."):
                                    subscription = create_razorpay_subscription(
                                        customer_email=st.session_state.get("user_email", ""),
                                        customer_name=st.session_state.get("user_name", ""),
                                        plan_id_secret="RAZORPAY_FREE_PLAN_ID",
                                        plan_label="Free",
                                        total_count_secret="RAZORPAY_FREE_TOTAL_COUNT",
                                    )
                            except Exception as exc:
                                st.session_state.razorpay_checkout_url_free = ""
                                st.error(f"❌ Razorpay could not create the subscription: {exc}")

                            if subscription is not None:
                                try:
                                    update_free_billing_status(
                                        subscription.get("status", "created"),
                                        subscription["id"],
                                    )
                                    st.session_state.razorpay_checkout_url_free = subscription["short_url"]
                                    st.success("Subscription created. Continue to secure Razorpay checkout.")
                                except Exception as exc:
                                    st.session_state.razorpay_checkout_url_free = ""
                                    st.error(
                                        f"❌ Razorpay subscription {subscription['id']} was created, "
                                        f"but saving it to your account (Supabase) failed: {exc}\n\n"
                                        "This usually means SUPABASE_SERVICE_ROLE_KEY is missing, wrong, "
                                        "or swapped with the anon key in Streamlit Secrets."
                                    )

                if st.session_state.get("razorpay_checkout_url_free"):
                    st.link_button(
                        "💳 Continue to Razorpay Checkout",
                        st.session_state.razorpay_checkout_url_free,
                        use_container_width=True,
                    )
                    _free_sub_id = st.session_state.get("free_subscription_id", "")
                    if _free_sub_id:
                        st.caption(f"Subscription ID: {_free_sub_id}")
                        if st.button("🔄 Verify Payment", use_container_width=True, key=f"verify_free_{section_id}"):
                            try:
                                with st.spinner("Verifying your Razorpay subscription..."):
                                    active, status = verify_free_billing_subscription()
                                if active:
                                    st.success("✅ Payment verified. ₹299/mo billing is now active.")
                                    st.session_state.razorpay_checkout_url_free = ""
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

    # Optional annual billing option — only shown if configured, so
    # nothing breaks for anyone who hasn't set this up yet.
    annual_url = secret("RAZORPAY_ANNUAL_CHECKOUT_URL")
    if annual_url:
        st.caption(
            "💡 Prefer to pay yearly? Save with annual billing on "
            "Professional."
        )
        st.link_button(
            "📅 See annual pricing",
            annual_url,
            use_container_width=False,
            key=f"annual_billing_{section_id}",
        )


# ============================================================
# AUTHENTICATION PAGE
# ============================================================

try:
    _offer = get_supabase_client().rpc("public_trial_offer", {}).execute().data
    FREE_TRIAL_DAYS = int(_offer["trial_days"])
    FREE_TRIAL_ANALYSES = int(_offer["analysis_limit"])
except Exception:
    st.error("Account settings are temporarily unavailable. Please try again shortly.")
    st.stop()

if not st.session_state.authenticated:

    # Topbar: logo + wordmark/tagline left, matching the reference design.
    # (The React reference shows "Need an account? Create account" here —
    # since Streamlit tabs don't support a clickable header-level tab
    # switch, this is a plain informational line instead.) Rendered as one
    # flex row (not st.columns) so the note stays close to the logo
    # instead of drifting to the far edge on a wide monitor.
    # The horizontal source image contains generous transparent padding, which
    # makes the header unnecessarily tall. Use the compact mark + live text in
    # the app bar; the full horizontal asset remains available elsewhere.
    st.markdown(
        f"""<div class="gi-auth-topbar">
<div class="gi-brand-row">
<div class="gi-auth-icon-sm" style="background:transparent;">{logo_mark_html(40, 12, 18)}</div>
<div>
<div class="gi-brand">Generative <span>Insight</span></div>
<div class="gi-tagline">{PRODUCT_NAME}</div>
</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    # Use the real horizontal brand logo inside the selected auth view. This
    # avoids displaying an empty black square when the mark asset is missing.
    _hero_logo_uri = _header_logo_data_uri()
    if _hero_logo_uri:
        _hero_icon_html = (
            f'<img class="gi-auth-hero-logo" src="{_hero_logo_uri}" '
            f'alt="Generative Insight" />'
        )
    else:
        _hero_icon_html = (
            '<div class="gi-brand" style="text-align:center; margin-bottom:14px;">'
            'Generative <span>Insight</span></div>'
        )
    if (
        not USE_NEON and (not secret("SUPABASE_URL")
        or not secret("SUPABASE_ANON_KEY"))
    ):
        st.error(
            "🔐 Authentication is not configured yet. "
            "Add SUPABASE_URL and SUPABASE_ANON_KEY in "
            "Streamlit → App Settings → Secrets."
        )
        st.stop()

    st.markdown('<span class="gi-auth-tabs-marker"></span>', unsafe_allow_html=True)

    signup_tab, login_tab, pricing_tab = st.tabs(
        [
            "Create account",
            "Sign in",
            "Plans",
        ]
    )

    # --------------------------------------------------------
    # SIGN UP
    # --------------------------------------------------------

    with signup_tab:

        # CSS hook used to constrain only this tab to a comfortable form width.
        st.markdown('<span class="gi-signup-marker"></span>', unsafe_allow_html=True)

        st.markdown(
            """<div class="gi-auth-hero" style="margin:4px 0 18px;">
<div class="gi-auth-hero-title" style="font-size:1.5rem;">Create your account</div>
<div class="gi-auth-hero-sub">Bring your operations, quality and improvement work together.</div>
</div>""".format(hero_logo=_hero_icon_html),
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""<div class="gi-auth-card-title">Get started with {PRODUCT_NAME}</div>
<div class="gi-auth-card-desc">Start your {FREE_TRIAL_DAYS}-day free trial: {FREE_TRIAL_ANALYSES} analyses total, uploads up to 5 MB, and PDF reports. Then continue from ₹299/month.</div>""",
            unsafe_allow_html=True,
        )

        with st.container(border=False):

            with st.form(
                "signup_form",
                clear_on_submit=False,
            ):

                signup_name = st.text_input(
                    "Full Name",
                    placeholder="e.g. Sunil Sethy",
                    label_visibility="visible",
                )

                signup_email = st.text_input(
                    "Work Email",
                    placeholder="name@company.com",
                    label_visibility="visible",
                )

                signup_company = st.text_input(
                    "Company / Organization",
                    placeholder="e.g. ABC Technologies",
                    label_visibility="visible",
                )

                signup_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Create a secure password",
                    label_visibility="visible",
                )
                st.caption(
                    "Use at least 6 characters. Your password must meet the "
                    "configured password policy."
                )

                signup_confirm = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Re-enter your password",
                    label_visibility="visible",
                )

                signup_terms_agreed = st.checkbox(
                    "I agree to the Terms of Service and Privacy Policy.",
                )

                signup_submitted = st.form_submit_button(
                    "Create account →",
                    type="primary",
                    use_container_width=True,
                )

        st.markdown(
            """<div class="gi-auth-footer-note">
Your data is protected with enterprise-grade security. By creating an account, you agree to use the platform responsibly and validate AI recommendations before taking material business action.
</div>""",
            unsafe_allow_html=True,
        )

        if signup_submitted:

            if not signup_name.strip():
                st.warning(
                    "Please enter your full name."
                )

            elif (
                not signup_email.strip()
                or "@" not in signup_email
            ):
                st.warning(
                    "Please enter a valid email address."
                )

            elif not signup_company.strip():
                st.warning(
                    "Please enter your company or organization."
                )

            elif len(signup_password) < 6:
                st.warning(
                    "Please use a password with at least 6 characters."
                )

            elif signup_password != signup_confirm:
                st.warning(
                    "Passwords do not match."
                )

            elif not signup_terms_agreed:
                st.warning(
                    "Please agree to the Terms of Service and Privacy Policy to continue."
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
                        if USE_NEON:
                            st.session_state.neon_pending_email = signup_email.strip().lower()
                            st.success("Account created. Enter the code from your email below, then sign in.")
                        else:
                            st.success("Account created. Check your email and click the verification link before signing in.")

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

        if USE_NEON:
            from neon_verification import render_verification
            render_verification(get_neon_client().auth, "signup_email_verification")

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    with login_tab:
        if USE_NEON:
            from neon_verification import render_verification
            render_verification(get_neon_client().auth, "login_email_verification")

        st.markdown('<span class="gi-login-marker"></span>', unsafe_allow_html=True)

        st.markdown(
            """<div class="gi-auth-hero" style="margin:4px 0 18px;">
<div class="gi-auth-hero-title" style="font-size:1.5rem;">Welcome back</div>
<div class="gi-auth-hero-sub">Your operations workspace, ready when you are.</div>
</div>""".format(hero_logo=_hero_icon_html),
            unsafe_allow_html=True,
        )

        st.markdown(
            """<div class="gi-auth-card-title">Sign in to your account</div>
<div class="gi-auth-card-desc">Enter your work email and password to continue.</div>""",
            unsafe_allow_html=True,
        )

        with st.container(border=False):

            with st.form("login_form"):

                login_email = st.text_input(
                    "Email",
                    placeholder="name@company.com",
                    label_visibility="visible",
                )

                login_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                    label_visibility="visible",
                )

                login_submitted = st.form_submit_button(
                    "Sign in →",
                    type="primary",
                    use_container_width=True,
                )

        st.markdown(
            """<div class="gi-auth-footer-note">
If you received a verification email, confirm your address before signing in.
</div>""",
            unsafe_allow_html=True,
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

    # --------------------------------------------------------
    # PRICING ON LOGIN PAGE
    # --------------------------------------------------------

    with pricing_tab:
        show_pricing("login")

    st.markdown(
        """<div style="text-align:center; margin-top:28px; padding-top:16px;
border-top:1px solid var(--border); color:#737373; font-size:0.85rem;">
🛡️ Enterprise-grade security for your operational data
</div>""",
        unsafe_allow_html=True,
    )

    st.stop()


# Owner permission and suspension are rechecked on every app rerun.
try:
    _access_db = get_authenticated_supabase_client()
    _access = _access_db.rpc("my_app_access", {}).execute().data
    st.session_state.account_access = _access
except Exception:
    st.error("We couldn't verify your account access. Please sign in again.")
    if st.button("Return to sign in", key="access_signout"):
        clear_authentication()
        st.rerun()
    st.stop()
if _access["blocked"]:
    st.error("Your app access is suspended. Contact the account owner for assistance.")
    if st.button("Sign out", key="blocked_signout"):
        clear_authentication()
        st.rerun()
    st.stop()
if not st.session_state.get("industry_selected_this_login", False):
    from industry_onboarding import render_industry_choice
    render_industry_choice(INDUSTRY_LABELS, update_user_industry)
    st.stop()

if _access["is_owner"]:
    _owner_view = st.sidebar.radio("Account area", ["My workspace", "Owner dashboard"], key="owner_area")
    if _owner_view == "Owner dashboard":
        from owner_admin import owner_snapshot, render_owner_admin
        try:
            _owner_data = owner_snapshot(_access_db)
        except Exception:
            st.error("Your owner account is recognised, but dashboard data could not load. Please retry.")
            if st.button("Retry dashboard", key="owner_retry"):
                st.rerun()
        else:
            render_owner_admin(_access_db, _owner_data)
        st.stop()

# ============================================================
# SIDEBAR
# ============================================================

plan_config = get_plan_config(
    st.session_state.user_plan
)

st.markdown('<span class="gi-workspace-marker"></span>', unsafe_allow_html=True)
st.markdown(
    "<style>" + (BASE_DIR / "dashboard_theme.css").read_text(encoding="utf-8") + "</style>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        f"""<div class="gi-brand-row">
{logo_mark_html(40, 11, 18)}
<div><div class="gi-brand">Generative <span>Insight</span></div>
<div class="gi-tagline">Operations workspace</div></div>
</div>""",
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown(
        f'<div class="gi-pill green">Plan: {st.session_state.user_plan}</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.user_plan == "Free":
        if free_billing_is_active():
            st.markdown(
                '<div class="gi-pill green">✅ ₹299/mo billing active — trial limits don\'t apply.</div>',
                unsafe_allow_html=True,
            )
        else:
            remaining = trial_days_remaining()
            if remaining is not None:
                if remaining <= 0:
                    st.markdown(
                        '<div class="gi-pill red">Your free trial has ended. '
                        'Continue for ₹299/mo to keep using AI Operations Manager.</div>',
                        unsafe_allow_html=True,
                    )
                elif remaining <= 3:
                    st.markdown(
                        f'<div class="gi-pill amber">⏳ {remaining} day(s) left in your free trial '
                        '(then ₹299/mo).</div>',
                        unsafe_allow_html=True,
                    )
                elif remaining <= 5:
                    # Soft nudge before the hard wall hits — people convert
                    # better when they choose to upgrade early than when
                    # they're forced to at day 0.
                    st.markdown(
                        f'<div class="gi-pill amber">🙂 {remaining} days left in your trial. '
                        'Lock in ₹299/mo now to avoid any interruption.</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Continue for ₹299/mo",
                        use_container_width=True,
                        key="sidebar_early_continue",
                    ):
                        st.session_state.show_plans = True
                        st.rerun()
                else:
                    st.markdown(
                        f'<div class="gi-pill neutral">{remaining} days left in your free trial (then ₹299/mo).</div>',
                        unsafe_allow_html=True,
                    )

    render_user_badge(st.session_state.get("user_name", ""), st.session_state.user_email)

    st.divider()

    st.radio("Workspace view", ["Industry tools", "Shared work hub"], key="workspace_view")

    st.subheader("Workspace")

    if PRODUCT:
        st.caption(PRODUCT_NAME)
    else:
        _current_industry = st.session_state.get("industry", "BPO")
        _selected_label = st.selectbox(
            "Analyze data for",
            options=list(INDUSTRY_LABELS.values()),
            index=list(INDUSTRY_LABELS.keys()).index(_current_industry)
            if _current_industry in INDUSTRY_LABELS else 0,
            key="industry_selector",
        )
        _selected_industry = next(
            k for k, v in INDUSTRY_LABELS.items() if v == _selected_label
        )
        if _selected_industry != _current_industry:
            update_user_industry(_selected_industry)
            clear_analysis()
            st.session_state.manufacturing_file_name = ""
            st.session_state.manufacturing_result = None
            st.session_state.manufacturing_report_bytes = None
            st.rerun()

    st.divider()

    if st.session_state.industry == "BPO":

        st.radio(
            "BPO workspace",
            ["Performance Dashboard", "Operations Excellence"],
            key="bpo_workspace",
        )
        with st.expander("KPI targets", expanded=False):
            st.caption("Set the thresholds used by your operational analysis.")
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
        "View plans",
        use_container_width=True,
        key="sidebar_view_plans",
    ):
        st.session_state.show_plans = True

    if st.button(
        "Reset analysis",
        use_container_width=True,
        key="sidebar_reset_analysis",
    ):
        clear_analysis()
        st.rerun()

    if st.button(
        "Sign out",
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
# FREE TRIAL GATE
# 3 days of Free access, then the dashboard is locked until
# the user upgrades to a paid plan.
# ============================================================

if st.session_state.user_plan == "Free" and not free_billing_is_active():

    _trial_remaining = trial_days_remaining()

    if _trial_remaining is not None and _trial_remaining <= 0:

        show_brand_header(compact=True)

        st.markdown(
            '<div class="main-title">Your Free trial has ended</div>',
            unsafe_allow_html=True,
        )

        st.warning(
            "Your free trial ended "
            f"{abs(_trial_remaining)} day(s) ago. Continue on Free for "
            "₹299/mo, or upgrade to Professional or Business, to keep "
            "analyzing operational data."
        )

        show_pricing("trial_expired")

        st.stop()

    elif _trial_remaining is not None and _trial_remaining <= 5:

        # Soft nudge before the hard wall — shown once trial is running
        # low but access is still allowed. Distinct from the sidebar
        # caption: this sits at the top of the main dashboard where it
        # can't be missed, with a direct link to upgrade now.
        nudge_col1, nudge_col2 = st.columns([4, 1])
        with nudge_col1:
            st.warning(
                f"⏳ **{_trial_remaining} day(s) left** in your free trial. "
                "Continue on Free for ₹299/mo, or upgrade to Professional, "
                "to avoid losing access to your dashboard."
            )
        with nudge_col2:
            if st.button(
                "View Plans",
                use_container_width=True,
                key="trial_nudge_view_plans",
            ):
                st.session_state.show_plans = True
                st.rerun()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """<div class="gi-dashboard-heading">
<div>
<div class="gi-dashboard-title">Operations Dashboard</div>
<div class="gi-dashboard-subtitle">Turn operational data into management decisions</div>
</div>
</div>""",
    unsafe_allow_html=True,
)

# ============================================================
# INDUSTRY DISPATCH
# Manufacturing gets its own complete, self-contained flow. Anything
# not yet in BUILT_INDUSTRIES gets the coming-soon screen. Both stop
# here. Everything below this point (Report Setup, file upload, KPI
# analysis, tabs) is BPO-only and assumes productivity_target etc.
# exist, which they only do when industry == "BPO".
# ============================================================

if st.session_state.get("workspace_view") == "Shared work hub":
    try:
        hub_db = get_authenticated_supabase_client()
    except Exception:
        st.error("Could not open your workspace. Please sign out and sign in again.")
        st.stop()
    render_work_hub(hub_db, st.session_state.user_id, st.session_state.industry)
    st.stop()

if st.session_state.industry == "Manufacturing":
    render_manufacturing_flow(plan_config)
    st.stop()

elif st.session_state.industry == "CaseManagement":
    render_case_management_flow(plan_config)
    st.stop()

elif st.session_state.industry not in BUILT_INDUSTRIES:
    render_coming_soon_flow(st.session_state.industry)
    st.stop()


if st.session_state.get("bpo_workspace") == "Operations Excellence":
    render_operations_excellence()
    st.stop()


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

    st.download_button(
        "⬇️ Download Data Template (.xlsx)",
        data=build_data_template_bytes(),
        file_name="AI_Operations_Manager_Data_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="download_data_template",
    )

    st.caption(
        "Includes example rows and a column-by-column guide — "
        "delete the sample rows and paste in your own data."
    )

    st.markdown("### What you get")

    a, b, c, d = st.columns(4)

    with a:
        render_check_card("Risk Detection")
    with b:
        render_check_card("Employee Risk")
    with c:
        render_check_card("AI Copilot")
    with d:
        render_check_card("Management Report")

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

elif (
    st.session_state.user_plan != "Professional"
    and file_mb > plan_config["max_mb"] * 0.8
):

    # Contextual upsell — shown right where the constraint actually
    # bites, not on a separate pricing page.
    st.warning(
        f"This file is {file_mb:.2f} MB, close to your "
        f"{plan_config['max_mb']} MB limit. Professional supports files "
        "up to 25 MB plus PDF + email reports and n8n automation."
    )
    if st.button("🚀 See Professional plan", key="upsell_filesize"):
        st.session_state.show_plans = True
        st.rerun()


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

n8n_url_raw = secret(
    "N8N_WEBHOOK_URL"
)

copilot_url_raw = secret(
    "N8N_COPILOT_WEBHOOK_URL"
)

n8n_url = normalize_webhook_url(n8n_url_raw)
copilot_url = normalize_webhook_url(copilot_url_raw)

if n8n_url_raw and not n8n_url:
    st.error("❌ N8N_WEBHOOK_URL is not a valid HTTP(S) URL in Streamlit Secrets.")

if copilot_url_raw and not copilot_url:
    st.error("❌ N8N_COPILOT_WEBHOOK_URL is not a valid HTTP(S) URL in Streamlit Secrets.")

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

_analysis_start_time = time.time()

with st.spinner("🔄 Fetching and reading your uploaded data..."):

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
    # These two matter: engine.py's analyze_data() requires them too
    # (see its REQUIRED list). Without checking for them here, a file
    # could pass this gate cleanly and then crash a moment later
    # inside analyze_data() with a confusing "Missing columns" error.
    "Attendance",
    "Error_Count",
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

require_trial_analysis(uploaded, st.session_state.industry, {"productivity": productivity_target, "quality": quality_target, "sla": sla_target, "aht": aht_target})

with st.spinner("🧠 Analyzing operational data against your KPI targets..."):

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

_analysis_elapsed = time.time() - _analysis_start_time

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
# KPI PERFORMANCE
# ============================================================

st.markdown(
    f'<div class="small-muted" style="margin:.25rem 0 1rem;">'
    f'{company_name or "Your organization"} · {report_name} · '
    f'{len(df)} rows analyzed in {_analysis_elapsed:.2f}s</div>',
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)

with k1:
    render_metric_card(
        "📈", "Productivity", f"{productivity:.2f}%",
        delta=f"{productivity_gap:+.2f}% vs target",
        delta_tone="good" if productivity_gap >= 0 else "bad",
    )

with k2:
    render_metric_card(
        "✔️", "Quality", f"{quality:.2f}%",
        delta=f"{quality_gap:+.2f}% vs target",
        delta_tone="good" if quality_gap >= 0 else "bad",
    )

with k3:
    render_metric_card(
        "⏱️", "SLA", f"{sla:.2f}%",
        delta=f"{sla_gap:+.2f}% vs target",
        delta_tone="good" if sla_gap >= 0 else "bad",
    )

with k4:
    render_metric_card(
        "⌛", "Average AHT", f"{aht:.2f}",
        delta=f"{aht_gap:+.2f} vs target",
        delta_tone="bad" if aht_gap > 0 else "good",
    )


# ============================================================
# PERFORMANCE TREND + RISK ALERTS
# ============================================================

trend_data = pd.DataFrame()
if "Date" in df.columns:
    _trend_source = df.copy()
    _trend_source["Date"] = pd.to_datetime(_trend_source["Date"], errors="coerce")
    _trend_source = _trend_source.dropna(subset=["Date"])
    if not _trend_source.empty:
        _trend_source["Period"] = _trend_source["Date"].dt.to_period("W").astype(str)
        _trend_rows = []
        for _period, _group in _trend_source.groupby("Period", sort=True):
            _row = {"Period": _period}
            if "Production" in _group.columns and "Target" in _group.columns:
                _target_sum = pd.to_numeric(_group["Target"], errors="coerce").sum()
                _production_sum = pd.to_numeric(_group["Production"], errors="coerce").sum()
                if _target_sum:
                    _row["Productivity"] = (_production_sum / _target_sum) * 100
            if "Quality_%" in _group.columns:
                _row["Quality"] = pd.to_numeric(_group["Quality_%"], errors="coerce").mean()
            if "SLA_%" in _group.columns:
                _row["SLA"] = pd.to_numeric(_group["SLA_%"], errors="coerce").mean()
            _trend_rows.append(_row)
        trend_data = pd.DataFrame(_trend_rows).set_index("Period") if _trend_rows else pd.DataFrame()

# A stable current-period view keeps the dashboard useful when the uploaded
# file has no Date column or contains only one reporting period.
if trend_data.empty:
    trend_data = pd.DataFrame(
        {
            "Productivity": [productivity],
            "Quality": [quality],
            "SLA": [sla],
        },
        index=["Current upload"],
    )

trend_col, alerts_col = st.columns([2.15, 1])

with trend_col:
    with st.container(border=True):
        st.markdown('<div class="gi-panel-title">KPI Performance Trend</div>', unsafe_allow_html=True)
        _has_real_trend = len(trend_data.index) >= 2
        _chart_subtitle = (
            "Productivity, quality and SLA over time"
            if _has_real_trend
            else "Current KPI position — add multiple dates to display a trend"
        )
        st.markdown(
            f'<div class="gi-panel-subtitle">{_chart_subtitle}</div>',
            unsafe_allow_html=True,
        )

        if _has_real_trend:
            _chart_frame = (
                trend_data.reset_index()
                .melt(id_vars=[trend_data.index.name or "index"], var_name="KPI", value_name="Value")
            )
            _period_column = trend_data.index.name or "index"
            _chart = (
                alt.Chart(_chart_frame)
                .mark_line(point=alt.OverlayMarkDef(size=55), strokeWidth=2.5)
                .encode(
                    x=alt.X(f"{_period_column}:N", title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("Value:Q", title="Percent", scale=alt.Scale(zero=True)),
                    color=alt.Color(
                        "KPI:N",
                        scale=alt.Scale(
                            domain=["Productivity", "Quality", "SLA"],
                            range=["#0EA5E9", "#0F766E", "#EF4444"],
                        ),
                        legend=alt.Legend(orient="bottom", title=None),
                    ),
                    tooltip=[_period_column, "KPI", alt.Tooltip("Value:Q", format=".1f")],
                )
            )
        else:
            _current_kpis = pd.DataFrame(
                {
                    "KPI": ["Productivity", "Quality", "SLA"],
                    "Value": [productivity, quality, sla],
                }
            )
            _chart = (
                alt.Chart(_current_kpis)
                .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=54)
                .encode(
                    x=alt.X("KPI:N", title=None, sort=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("Value:Q", title="Percent", scale=alt.Scale(zero=True)),
                    color=alt.Color(
                        "KPI:N",
                        scale=alt.Scale(
                            domain=["Productivity", "Quality", "SLA"],
                            range=["#0EA5E9", "#0F766E", "#EF4444"],
                        ),
                        legend=None,
                    ),
                    tooltip=["KPI", alt.Tooltip("Value:Q", format=".1f")],
                )
            )

        _chart = _chart.properties(height=300).configure(
            background="#FFFFFF"
        ).configure_view(
            stroke=None
        ).configure_axis(
            labelColor="#52525B",
            titleColor="#52525B",
            domainColor="#E5E7EB",
            tickColor="#E5E7EB",
            gridColor="#EEF0F3",
        ).configure_legend(
            labelColor="#27272A"
        )
        st.altair_chart(_chart, use_container_width=True, theme=None)

with alerts_col:
    with st.container(border=True):
        st.markdown('<div class="gi-panel-title">⚠ Risk Alerts</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="gi-panel-subtitle">{breaches} active signal(s)</div>',
            unsafe_allow_html=True,
        )

        _alerts = []
        if productivity < productivity_target:
            _alerts.append(("Productivity below target", f"{productivity:.1f}% vs {productivity_target}%", "High"))
        if quality < quality_target:
            _alerts.append(("Quality below target", f"{quality:.1f}% vs {quality_target}%", "High"))
        if sla < sla_target:
            _alerts.append(("SLA below target", f"{sla:.1f}% vs {sla_target}%", "Medium"))
        if aht > aht_target:
            _alerts.append(("Average AHT rising", f"{aht:.1f} vs {aht_target}", "Medium"))

        if not _alerts:
            st.success("All monitored KPIs are within target.")
        else:
            for _name, _meta, _level in _alerts:
                st.markdown(
                    f'''<div class="gi-risk-alert">
<div><div class="gi-risk-name">{_name}</div><div class="gi-risk-meta">{_meta}</div></div>
<div class="gi-risk-level">{_level}</div>
</div>''',
                    unsafe_allow_html=True,
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

                st.error("❌ " + n8n_failure_message(response, "n8n workflow"))
                error_detail = safe_n8n_error_detail(response)
                if error_detail:
                    st.code(error_detail, language="text")

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
        "📈 Performance Trends",
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

                    st.error("❌ " + n8n_failure_message(copilot_response, "Copilot workflow"))
                    error_detail = safe_n8n_error_detail(copilot_response)
                    if error_detail:
                        st.code(error_detail, language="text")

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
    f"""<div class="gi-footer">
<strong>Generative Insight</strong> · AI Operations Copilot v{APP_VERSION}
<br>
Insights today. Intelligence tomorrow.
<br>
<a class="website-link" href="{WEBSITE_URL}" target="_blank" rel="noopener noreferrer">generativeinsight.in</a>
&nbsp;·&nbsp;
© {datetime.now().year}
<br>
🛡️ Enterprise-grade security for your operational data
</div>""",
    unsafe_allow_html=True,
)



with tabs[7]:
    render_bpo_trends(df, {"Productivity": productivity_target,
        "Quality": quality_target, "SLA": sla_target, "AHT": aht_target})
