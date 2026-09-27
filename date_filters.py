"""Explicit inclusive date ranges shared by operational dashboards."""
import streamlit as st
from datetime import date


def date_range(minimum, maximum, key, label='Reporting dates'):
    minimum, maximum = minimum.date(), maximum.date()
    signature = (minimum.isoformat(), maximum.isoformat())
    start_key, end_key = key + '_start', key + '_end'
    if st.session_state.get(key + '_bounds') != signature:
        st.session_state[start_key] = minimum
        st.session_state[end_key] = maximum
        st.session_state[key + '_bounds'] = signature
    st.caption(label + ' · both dates included')
    if st.button('Use all available dates', key=key + '_reset'):
        st.session_state[start_key] = minimum
        st.session_state[end_key] = maximum
    lower=min(minimum,date(1900,1,1))
    upper=max(maximum,date(2100,12,31))
    left, right = st.columns(2)
    start = left.date_input('Start date', min_value=lower, max_value=upper,
                           key=start_key, format='DD/MM/YYYY')
    end = right.date_input('End date', min_value=lower, max_value=upper,
                          key=end_key, format='DD/MM/YYYY')
    st.caption(f'Available data: {minimum:%d %b %Y} to {maximum:%d %b %Y}')
    if minimum == maximum:
        st.caption('This upload contains one date. You can select any range; only matching records are shown.')
    if start > end:
        st.error('Start date must be on or before end date.')
        return None
    return start, end

