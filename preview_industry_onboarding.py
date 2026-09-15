import streamlit as st
from industry_onboarding import render_industry_choice

def save(industry):
    st.session_state.industry=industry

if not st.session_state.get('industry_selected_this_login'):
    render_industry_choice({'BPO':'BPO','Retail':'Retail'},save)
else:
    st.success('Workspace selected')
