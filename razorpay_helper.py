import razorpay
import streamlit as st


def get_razorpay_client():
    """
    Creates a Razorpay API client using Streamlit Secrets.
    Never expose the Key Secret to the browser.
    """

    key_id = st.secrets.get("RAZORPAY_KEY_ID", "")
    key_secret = st.secrets.get("RAZORPAY_KEY_SECRET", "")

    if not key_id or not key_secret:
        raise RuntimeError(
            "Razorpay is not configured. "
            "Add RAZORPAY_KEY_ID and "
            "RAZORPAY_KEY_SECRET to Streamlit Secrets."
        )

    return razorpay.Client(
        auth=(key_id, key_secret)
    )


def get_razorpay_key_id():
    """
    Returns the public Razorpay Key ID.
    This can be used by the frontend if required.
    """

    key_id = st.secrets.get(
        "RAZORPAY_KEY_ID",
        ""
    )

    if not key_id:
        raise RuntimeError(
            "RAZORPAY_KEY_ID is missing."
        )

    return key_id


def get_professional_plan_id():
    """
    Returns the Razorpay Professional Plan ID.
    """

    plan_id = st.secrets.get(
        "RAZORPAY_PROFESSIONAL_PLAN_ID",
        ""
    )

    if not plan_id:
        raise RuntimeError(
            "RAZORPAY_PROFESSIONAL_PLAN_ID "
            "is missing."
        )

    return plan_id


def create_professional_subscription(
    user_email,
    user_name="",
):
    """
    Creates a Razorpay subscription
    for the Generative Insight Professional plan.

    Returns the Razorpay subscription object.
    """

    client = get_razorpay_client()

    plan_id = get_professional_plan_id()

    user_email = (
        user_email or ""
    ).strip().lower()

    user_name = (
        user_name or ""
    ).strip()

    if not user_email:
        raise ValueError(
            "Customer email is required."
        )

    subscription_data = {
        "plan_id": plan_id,

        # 120 monthly billing cycles
        # = 10 years of monthly billing.
        # We can change this later if required.
        "total_count": 120,

        "quantity": 1,

        "customer_notify": 1,

        "notes": {
            "product": "Generative Insight",
            "plan": "Professional",
            "customer_email": user_email,
            "customer_name": user_name,
        },
    }

    subscription = (
        client.subscription.create(
            subscription_data
        )
    )

    return subscription


def fetch_subscription(
    subscription_id
):
    """
    Fetch an existing Razorpay subscription.
    """

    client = get_razorpay_client()

    return (
        client.subscription.fetch(
            subscription_id
        )
    )


def cancel_subscription(
    subscription_id
):
    """
    Cancel a Razorpay subscription.
    """

    client = get_razorpay_client()

    return (
        client.subscription.cancel(
            subscription_id,
            {
                "cancel_at_cycle_end": 1
            }
        )
    )
