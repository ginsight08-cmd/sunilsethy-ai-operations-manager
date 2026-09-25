"""Email verification for Neon's free shared email provider."""
import streamlit as st


def render_verification(auth, key):
    with st.expander('Verify your email', expanded=bool(st.session_state.get('neon_pending_email'))):
        st.caption('Enter the verification code from your email. After verification, use Sign in to open your workspace.')
        with st.form(key):
            email=st.text_input('Account email',value=st.session_state.get('neon_pending_email',''))
            code=st.text_input('Email verification code',type='password',max_chars=12)
            verify=st.form_submit_button('Verify email',type='primary')
            resend=st.form_submit_button('Send a new code')
        if verify:
            try:
                auth.verify_email(email,code)
            except Exception:
                st.error('We could not verify that code. Check the email and code, or request a new one.')
            else:
                st.session_state.pop('neon_pending_email',None)
                st.success('Email verified. You can now sign in.')
        elif resend:
            try:
                auth.resend_verification(email)
            except Exception:
                st.error('The code could not be sent. Please check the email and try again later.')
            else:
                st.success('If this account needs verification, a new code has been sent. Check your inbox and spam folder.')
