import streamlit as st
from operations_excellence import render_operations_excellence
st.set_page_config(layout='wide')
st.session_state.user_id = 'local-test-user'
render_operations_excellence()
