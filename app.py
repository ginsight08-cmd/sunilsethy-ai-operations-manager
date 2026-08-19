import io
import json
import smtplib
from datetime import datetime, timedelta
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
    "account_created_at": "",
    # Free-tier (₹299/mo, post 15-day trial) billing — tracked
    # separately from the Professional Razorpay fields above so the
    # two subscriptions never collide.
    "free_billing_status": "",
    "free_subscription_id": "",
    "razorpay_checkout_url_free": "",
}

# Free plan trial length. After this many days on the Free plan,
@@ -526,6 +532,34 @@
    st.session_state.razorpay_subscription_id = metadata.get("razorpay_subscription_id", "")


def update_free_billing_status(status, subscription_id=""):
    """
    Tracks the ₹299/mo Free-tier subscription (post 15-day trial) WITHOUT
    changing the user's 'plan' field — someone on this billing plan is
    still logically on 'Free' feature limits, just paying to keep access
    past the trial window.
    """
    if not st.session_state.get("user_id"):
        raise RuntimeError("No authenticated user is available.")
    admin = get_supabase_admin_client()
    current = admin.auth.admin.get_user_by_id(st.session_state.user_id)
    user = getattr(current, "user", None)
    metadata = dict(getattr(user, "user_metadata", {}) or {}) if user else {}
    metadata.update({
        "free_billing_status": status,
        "free_subscription_id": subscription_id or metadata.get("free_subscription_id", ""),
        "free_billing_updated_at": datetime.utcnow().isoformat() + "Z",
    })
    admin.auth.admin.update_user_by_id(st.session_state.user_id, {"user_metadata": metadata})
    st.session_state.free_billing_status = status
    st.session_state.free_subscription_id = metadata.get("free_subscription_id", "")


def free_billing_is_active():
    """True once the ₹299/mo Free-tier subscription is confirmed active."""
    return st.session_state.get("free_billing_status", "") == "active"


def get_razorpay_subscription(subscription_id):
    key_id, key_secret = secret("RAZORPAY_KEY_ID"), secret("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
@@ -550,18 +584,18 @@
    return data


def razorpay_activation_ready():
def razorpay_activation_ready(plan_id_secret="RAZORPAY_PROFESSIONAL_PLAN_ID", plan_label="Professional"):
    if not st.session_state.get("authenticated") or not st.session_state.get("user_id"):
        return False, "Please create an account or sign in before starting a Professional subscription."
        return False, f"Please create an account or sign in before starting a {plan_label} subscription."
    if not secret("SUPABASE_SERVICE_ROLE_KEY"):
        return False, "Secure plan activation is not configured. Add SUPABASE_SERVICE_ROLE_KEY to Streamlit Secrets."
    if not razorpay_is_configured():
        return False, "Razorpay is not fully configured. Add RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET and RAZORPAY_PROFESSIONAL_PLAN_ID to Streamlit Secrets."
    if not razorpay_is_configured(plan_id_secret):
        return False, f"Razorpay is not fully configured. Add RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET and {plan_id_secret} to Streamlit Secrets."
    return True, ""


def verify_professional_subscription():
    ready, message = razorpay_activation_ready()
    ready, message = razorpay_activation_ready("RAZORPAY_PROFESSIONAL_PLAN_ID", "Professional")
    if not ready:
        raise RuntimeError(message)
    subscription_id = st.session_state.get("razorpay_subscription_id", "")
@@ -582,6 +616,29 @@
    return False, status


def verify_free_billing_subscription():
    """Verify the ₹299/mo Free-tier subscription. Does NOT change 'plan'."""
    ready, message = razorpay_activation_ready("RAZORPAY_FREE_PLAN_ID", "Free")
    if not ready:
        raise RuntimeError(message)
    subscription_id = st.session_state.get("free_subscription_id", "")
    if not subscription_id:
        admin = get_supabase_admin_client()
        current = admin.auth.admin.get_user_by_id(st.session_state.user_id)
        user = getattr(current, "user", None)
        metadata = getattr(user, "user_metadata", {}) or {} if user else {}
        subscription_id = metadata.get("free_subscription_id", "")
    if not subscription_id:
        raise RuntimeError("No Razorpay subscription ID is available. Start the ₹299/mo checkout first.")
    data = get_razorpay_subscription(subscription_id)
    status = str(data.get("status", "")).lower()
    if status == "active":
        update_free_billing_status("active", subscription_id)
        return True, status
    update_free_billing_status(status, subscription_id)
    return False, status


def friendly_auth_error(error) -> str:
    """Convert Supabase auth errors into user-friendly messages."""
    message = str(getattr(error, "message", error))
@@ -664,6 +721,8 @@
    st.session_state.company_name = metadata.get("company_name", "")
    st.session_state.user_plan = metadata.get("plan", "Free") or "Free"
    st.session_state.razorpay_subscription_id = metadata.get("razorpay_subscription_id", "")
    st.session_state.free_billing_status = metadata.get("free_billing_status", "")
    st.session_state.free_subscription_id = metadata.get("free_subscription_id", "")

    # Supabase sets this automatically when the account is created — used
    # to work out how many days are left in the Free trial.
@@ -684,6 +743,9 @@
    st.session_state.razorpay_checkout_url = ""
    st.session_state.razorpay_subscription_id = ""
    st.session_state.account_created_at = ""
    st.session_state.free_billing_status = ""
    st.session_state.free_subscription_id = ""
    st.session_state.razorpay_checkout_url_free = ""

    clear_analysis()

@@ -710,7 +772,7 @@
            "pdf": True,
            "email": False,
            "automation": False,
            "price": "₹0",
            "price": "₹299/mo (15 days free)",
        },
        "Professional": {
            "max_mb": 25,
@@ -1331,29 +1393,35 @@
RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


def razorpay_is_configured():
def razorpay_is_configured(plan_id_secret="RAZORPAY_PROFESSIONAL_PLAN_ID"):
    return all(
        [
            secret("RAZORPAY_KEY_ID"),
            secret("RAZORPAY_KEY_SECRET"),
            secret("RAZORPAY_PROFESSIONAL_PLAN_ID"),
            secret(plan_id_secret),
        ]
    )


def create_razorpay_subscription(customer_email="", customer_name=""):
def create_razorpay_subscription(
    customer_email="",
    customer_name="",
    plan_id_secret="RAZORPAY_PROFESSIONAL_PLAN_ID",
    plan_label="Professional",
    total_count_secret="RAZORPAY_PROFESSIONAL_TOTAL_COUNT",
):
    key_id = secret("RAZORPAY_KEY_ID")
    key_secret = secret("RAZORPAY_KEY_SECRET")
    plan_id = secret("RAZORPAY_PROFESSIONAL_PLAN_ID")
    plan_id = secret(plan_id_secret)

    if not key_id or not key_secret or not plan_id:
        raise RuntimeError(
            "Razorpay is not configured. Add RAZORPAY_KEY_ID, "
            "RAZORPAY_KEY_SECRET and RAZORPAY_PROFESSIONAL_PLAN_ID "
            f"Razorpay is not configured. Add RAZORPAY_KEY_ID, "
            f"RAZORPAY_KEY_SECRET and {plan_id_secret} "
            "to Streamlit Secrets."
        )

    raw_total_count = secret("RAZORPAY_PROFESSIONAL_TOTAL_COUNT", "12")
    raw_total_count = secret(total_count_secret, "12")
    try:
        total_count = int(raw_total_count)
    except (TypeError, ValueError):
@@ -1368,7 +1436,7 @@
        "customer_notify": 1,
        "notes": {
            "application": APP_NAME,
            "plan": "Professional",
            "plan": plan_label,
            "customer_email": str(customer_email or "")[:255],
            "customer_name": str(customer_name or "")[:255],
        },
@@ -1440,8 +1508,9 @@
        (
            c1,
            "Free",
            "₹0",
            "₹299/mo",
            [
                "Free for first 15 days",
                "5 MB file limit",
                "Dashboard analytics",
                "AI Copilot",
@@ -1450,7 +1519,7 @@
            (
                "Current plan"
                if st.session_state.user_plan == "Free"
                else "Start Free"
                else "Start Free Trial"
            ),
        ),
        (
@@ -1484,7 +1553,7 @@
    for col, name, price, features, button in plans:
        with col:
            plan_visuals = {
                "Free": ("🌱", "Start your AI operations journey"),
                "Free": ("🌱", "15 days free, then ₹299/mo"),
                "Professional": ("🚀", "Advanced intelligence & automation"),
                "Business": ("🏢", "Scale AI operations across teams"),
            }
@@ -1592,6 +1661,99 @@
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
@@ -1609,6 +1771,21 @@
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
@@ -1926,21 +2103,40 @@
    )

    if st.session_state.user_plan == "Free":
        remaining = trial_days_remaining()
        if remaining is not None:
            if remaining <= 0:
                st.error(
                    f"Your {FREE_TRIAL_DAYS}-day Free trial has ended. "
                    "Upgrade to keep using AI Operations Manager."
                )
            elif remaining <= 3:
                st.warning(
                    f"⏳ {remaining} day(s) left in your Free trial."
                )
            else:
                st.caption(
                    f"{remaining} days left in your Free trial."
                )
        if free_billing_is_active():
            st.caption("✅ ₹299/mo billing active — trial limits don't apply.")
        else:
            remaining = trial_days_remaining()
            if remaining is not None:
                if remaining <= 0:
                    st.error(
                        f"Your {FREE_TRIAL_DAYS}-day free trial has ended. "
                        "Continue for ₹299/mo to keep using AI Operations Manager."
                    )
                elif remaining <= 3:
                    st.warning(
                        f"⏳ {remaining} day(s) left in your free trial "
                        "(then ₹299/mo)."
                    )
                elif remaining <= 5:
                    # Soft nudge before the hard wall hits — people convert
                    # better when they choose to upgrade early than when
                    # they're forced to at day 0.
                    st.info(
                        f"🙂 {remaining} days left in your trial. "
                        "Lock in ₹299/mo now to avoid any interruption."
                    )
                    if st.button(
                        "Continue for ₹299/mo",
                        use_container_width=True,
                        key="sidebar_early_continue",
                    ):
                        st.session_state.show_plans = True
                        st.rerun()
                else:
                    st.caption(
                        f"{remaining} days left in your free trial (then ₹299/mo)."
                    )

    if st.session_state.get("user_name"):
        st.caption(
@@ -2024,7 +2220,7 @@
# the user upgrades to a paid plan.
# ============================================================

if st.session_state.user_plan == "Free":
if st.session_state.user_plan == "Free" and not free_billing_is_active():

    _trial_remaining = trial_days_remaining()

@@ -2038,15 +2234,38 @@
        )

        st.warning(
            f"Your {FREE_TRIAL_DAYS}-day Free trial ended "
            f"{abs(_trial_remaining)} day(s) ago. Upgrade to Professional "
            "or Business to keep analyzing operational data."
            f"Your {FREE_TRIAL_DAYS}-day free trial ended "
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
@@ -2172,6 +2391,22 @@

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
