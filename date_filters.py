"""Explicit inclusive date ranges shared by operational dashboards."""
import streamlit as st


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
    left, right = st.columns(2)
    start = left.date_input('Start date', min_value=minimum, max_value=maximum,
                           key=start_key, format='DD/MM/YYYY')
    end = right.date_input('End date', min_value=minimum, max_value=maximum,
                          key=end_key, format='DD/MM/YYYY')
    st.caption(f'Available data: {minimum:%d %b %Y} to {maximum:%d %b %Y}')
    if minimum == maximum:
        st.caption('This upload contains one date. Upload more dates to compare periods.')
    if start > end:
        st.error('Start date must be on or before end date.')
        return None
    return start, end
