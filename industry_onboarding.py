"""Industry selection before workspace navigation; no admin UI here."""
import streamlit as st


def render_industry_choice(labels, save_industry):
    st.title('Choose your industry')
    st.write('Select the workspace that matches your work. You can change it later.')
    descriptions = {
        'BPO': 'Operational performance, quality and improvement actions.',
        'Manufacturing': 'Procurement comparisons and operational work tracking.',
        'CaseManagement': 'Clients, legal matters and case workflows.',
        'Retail': 'Shared client, project and task tracking. Industry analytics coming soon.',
        'Logistics': 'Shared client, project and task tracking. Industry analytics coming soon.',
        'Healthcare': 'Shared administrative work tracking. Industry analytics coming soon.',
    }
    keys = list(labels)
    for start in range(0, len(keys), 2):
        for column, key in zip(st.columns(2), keys[start:start+2]):
            with column:
                with st.container(border=True):
                    st.subheader(labels[key])
                    st.write(descriptions.get(key, 'Your industry workspace.'))
                    if st.button('Choose ' + labels[key], key='choose_industry_' + key, use_container_width=True):
                        save_industry(key)
                        st.session_state.industry_selected_this_login = True
                        st.session_state.workspace_view = 'Industry tools' if key in {'BPO','Manufacturing','CaseManagement'} else 'Shared work hub'
                        st.session_state.pop('industry_selector', None)
                        st.rerun()
