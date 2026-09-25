"""Native Streamlit navigation; preserves widget state and keyboard controls."""
import streamlit as st


def reporting_navigation():
    with st.container(key='primary_reporting_nav'):
        overview, charts, actions, more = st.tabs(['Overview', 'Charts', 'Actions', 'More'])
        with more:
            insights, people, copilot, reports, billing = st.tabs(
                ['AI insights', 'Employee risk', 'Copilot', 'Reports', 'Billing'])
    return [overview, insights, people, actions, copilot, reports, billing, charts]
