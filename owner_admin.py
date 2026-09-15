"""Owner console. Every request is authorized again by PostgreSQL."""
import streamlit as st
import json


def owner_snapshot(db):
    return db.rpc('owner_console', {'p_action': 'view', 'p_payload': {}}).execute().data


def render_owner_admin(db, snapshot):
    st.header('Owner dashboard')
    if st.session_state.get('owner_save_notice'):
        st.success(st.session_state.pop('owner_save_notice'))
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
        own_account = selected == st.session_state.get('user_id')
        if own_account:
            st.info('This is your owner account. Trial extensions, credits and suspension cannot be changed here. Select a customer account to manage its access.')
        with st.form(f'owner_access_{selected}'):
            blocked = st.checkbox('Suspend app access', value=user['blocked'], disabled=own_account)
            extra_days = st.number_input('Add trial days', 0, 90, 0, disabled=own_account)
            extra_analyses = st.number_input('Add analysis credits', 0, 100, 0, disabled=own_account)
            reason = st.text_input('Reason for this change', max_chars=500, disabled=own_account)
            st.caption('Suspension takes effect on the next app interaction. Existing login credentials remain unchanged.')
            submit = st.form_submit_button('Save access change', disabled=own_account)
        if submit and not own_account:
            if not reason.strip():
                st.error('Enter a reason for the audit history.')
            else:
                _change(db,'access', {'user_id':selected,'blocked':blocked,'extra_days':extra_days,
                                     'extra_analyses':extra_analyses,'reason':reason.strip()})
    else:
        st.info('No matching accounts.')
    st.subheader('Recent admin changes')
    audit_rows = [dict(row, details=json.dumps(row.get('details', {}), ensure_ascii=False, default=str))
                  for row in snapshot['audit']]
    st.dataframe(audit_rows, hide_index=True, use_container_width=True)
    st.caption('Latest 100 changes. This page does not expose passwords, API keys or customer document contents.')


def _change(db, action, payload):
    try:
        db.rpc('owner_console', {'p_action':action,'p_payload':payload}).execute()
    except Exception as exc:
        # Only map known server messages; never expose raw database details.
        message = str(getattr(exc, 'message', ''))
        if 'Owner access cannot be edited here' in message:
            st.error('Owner accounts cannot be changed here. Select a customer account.')
        elif 'Owner access required' in message:
            st.error('Your session is not authorised for this change. Sign in with your owner account again.')
        elif 'Invalid access change' in message or 'Invalid defaults' in message:
            st.error('Check the entered limits and provide a reason before saving.')
        else:
            st.error('Save could not be confirmed. Reload and check the account values and admin history before retrying, to avoid adding the same credits twice.')
        return
    st.session_state.owner_save_notice = 'Access change saved.' if action == 'access' else 'Trial defaults saved.'
    st.rerun()
