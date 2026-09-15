"""Owner console. Every request is authorized again by PostgreSQL."""
import streamlit as st


def owner_snapshot(db):
    return db.rpc('owner_console', {'p_action': 'view', 'p_payload': {}}).execute().data


def render_owner_admin(db, snapshot):
    st.header('Owner dashboard')
    st.caption('Manage trial access. Changes are recorded in your audit history.')
    settings = snapshot['settings']
    st.metric('Registered accounts', snapshot['total_users'])
    st.caption('Showing the latest 200 accounts. Search by exact email to find an older account.')
    with st.form('owner_defaults'):
        st.subheader('Default trial for new sign-ups')
        days = st.number_input('Trial days', 1, 90, int(settings['trial_days']))
        analyses = st.number_input('Trial analyses', 1, 100, int(settings['analysis_limit']))
        st.caption('New defaults apply to future sign-ups. Existing account limits stay unchanged.')
        save = st.form_submit_button('Save trial defaults')
    if save:
        _change(db, 'defaults', {'trial_days': days, 'analysis_limit': analyses})
    st.subheader('Customer access')
    search = st.text_input('Find account by exact email')
    users = snapshot['users']
    if search.strip():
        try:
            users = db.rpc('owner_console', {'p_action':'search','p_payload':{'email':search.strip()}}).execute().data['users']
        except Exception:
            st.error('Could not search accounts. Sign in again and retry.')
            return
    if users:
        st.dataframe(users, hide_index=True, use_container_width=True)
        labels = {u['id']:u['email'] for u in users}
        selected = st.selectbox('Account to manage', list(labels), format_func=labels.get)
        user = next(u for u in users if u['id']==selected)
        with st.form(f'owner_access_{selected}'):
            blocked = st.checkbox('Suspend app access', value=user['blocked'])
            extra_days = st.number_input('Add trial days', 0, 90, 0)
            extra_analyses = st.number_input('Add analysis credits', 0, 100, 0)
            reason = st.text_input('Reason for this change', max_chars=500)
            st.caption('Suspension takes effect on the next app interaction. Existing login credentials remain unchanged.')
            submit = st.form_submit_button('Save access change')
        if submit:
            if not reason.strip():
                st.error('Enter a reason for the audit history.')
            else:
                _change(db,'access', {'user_id':selected,'blocked':blocked,'extra_days':extra_days,
                                     'extra_analyses':extra_analyses,'reason':reason.strip()})
    else:
        st.info('No matching accounts.')
    st.subheader('Recent admin changes')
    st.dataframe(snapshot['audit'], hide_index=True, use_container_width=True)
    st.caption('Latest 100 changes. This page does not expose passwords, API keys or customer document contents.')


def _change(db, action, payload):
    try:
        db.rpc('owner_console', {'p_action':action,'p_payload':payload}).execute()
    except Exception:
        st.error('The change was not confirmed. Reload before retrying; check your owner access.')
        return
    st.rerun()
