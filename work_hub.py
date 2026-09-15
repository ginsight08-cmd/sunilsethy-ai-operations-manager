"""Persistent cross-industry work hub. No external sends or AI-provider calls."""
from datetime import date
from decimal import Decimal

import pandas as pd
import streamlit as st

from work_hub_domain import HubStore, STATUSES, PARENTS, estimate

SECTIONS = {'Overview': None, 'Clients & intake': 'client', 'Work records': 'work',
            'Tasks & deadlines': 'task', 'Document links': 'document',
            'Drafts & approvals': 'draft', 'Time & billing prep': 'time', 'Activity': 'activity'}
WORK_NAMES = {'BPO': 'Service / improvement project', 'Manufacturing': 'Procurement / production project',
              'CaseManagement': 'Legal matter', 'Retail': 'Customer / store project',
              'Logistics': 'Delivery / operations project', 'Healthcare': 'Administrative project'}


def _frame(rows):
    return pd.DataFrame([{k: r.get(k, '') for k in ['id','title','kind','status','owner_name','due_date','updated_at']} for r in rows])


def _overview(rows):
    today = date.today().isoformat()
    tasks = [r for r in rows if r['kind']=='task' and r['status']!='Done']
    overdue = [r for r in tasks if r.get('due_date') and r['due_date'] < today]
    reviews = [r for r in rows if r['kind']=='draft' and r['status']=='Pending review']
    a,b,c,d = st.columns(4)
    a.metric('Active work', sum(r['kind']=='work' and r['status']!='Completed' for r in rows))
    b.metric('Open tasks',len(tasks)); c.metric('Overdue',len(overdue)); d.metric('Awaiting review',len(reviews))
    st.subheader('Needs attention')
    if overdue or reviews:
        st.dataframe(_frame(overdue+reviews), hide_index=True, use_container_width=True)
    else:
        st.info('No overdue tasks or drafts waiting for review in the loaded records.')
    st.subheader('Upcoming deadlines')
    upcoming = sorted([r for r in tasks if r.get('due_date') and r['due_date'] >= today], key=lambda r:r['due_date'])
    if upcoming:
        st.dataframe(_frame(upcoming), hide_index=True, use_container_width=True)
    st.caption('Dates are entered by your team. Legal filing or limitation deadlines are not calculated automatically.')


def _save(store, row, existing=None):
    try:
        saved = store.save(row,existing)
        st.session_state['hub_next_selection'] = {'industry':store.industry,'kind':saved['kind'],'id':saved['id']}
        st.session_state['hub_notice'] = 'Saved to your account.'
        st.rerun()
    except ValueError as e:
        st.error(str(e))
    except Exception:
        st.error('Could not save. Reload to check for changes, or verify your database setup and login session.')


def _editor(store, rows, kind, industry):
    current_rows = [r for r in rows if r['kind']==kind]
    filtered = st.text_input('Search records', key=f'hub_search_{industry}_{kind}')
    if filtered.strip():
        current_rows = [r for r in current_rows if filtered.casefold() in (r['title']+' '+r.get('owner_name','')).casefold()]
    if current_rows:
        st.dataframe(_frame(current_rows), hide_index=True, use_container_width=True)
    parents = [r for r in rows if r['kind']==PARENTS.get(kind)]
    if kind in PARENTS and not parents:
        st.info('Create a client first.' if kind=='work' else 'Create a work record first.')
        return
    labels = {r['id']:r['title'] for r in current_rows}
    selected = st.selectbox('Create or edit', ['New']+list(labels), format_func=lambda i:labels.get(i,i), key=f'hub_selected_{industry}_{kind}')
    old = next((r for r in current_rows if r['id']==selected),None)
    details = old.get('details',{}) if old else {}
    parent_ids = [r['id'] for r in parents]
    parent_labels = {r['id']:r['title'] for r in parents}
    if old and kind in PARENTS and old['parent_id'] not in parent_ids:
        st.warning('The related record is outside the loaded view. This record cannot be edited here until its parent is loaded.')
        return
    if kind=='draft':
        st.info('Draft → Pending review → Approved or Rejected. Approval records your sign-off; it does not send, file or bill anything.')
    if kind=='time':
        st.caption('Manual time entries and fee estimates. These are not issued invoices or payment records.')
    with st.form(f'hub_form_{industry}_{kind}_{selected}'):
        title = st.text_input('Name' if kind=='client' else 'Title',value=old['title'] if old else '',max_chars=300)
        owner = st.text_input('Responsible person',value=old.get('owner_name','') if old else '',max_chars=200)
        parent = None
        if parents:
            parent = st.selectbox('Client' if kind=='work' else 'Related work',parent_ids,
                index=parent_ids.index(old['parent_id']) if old and old['parent_id'] in parent_ids else 0,
                format_func=lambda i:parent_labels[i])
        due = None
        if kind in ['work','task']:
            due = st.date_input('Due date',value=date.fromisoformat(old['due_date']) if old and old.get('due_date') else None)
        data = {}
        if kind=='client':
            data['email'] = st.text_input('Contact email',value=details.get('email',''),max_chars=250)
            data['phone'] = st.text_input('Contact phone',value=details.get('phone',''),max_chars=100)
            data['source'] = st.text_input('Inquiry source',value=details.get('source',''),max_chars=250)
        if kind in ['client','work','task']:
            data['notes'] = st.text_area('Context / requirements',value=details.get('notes',''),max_chars=12000)
        if kind=='document':
            data['url'] = st.text_input('HTTPS document link',value=details.get('url',''),max_chars=2000)
            data['notes'] = st.text_area('Document description',value=details.get('notes',''),max_chars=12000)
            st.caption('Stores a reference only. Access remains controlled by the document provider; no file is copied here.')
        if kind=='draft':
            data['recipient'] = st.text_input('Intended recipient',value=details.get('recipient',''),max_chars=250)
            data['body'] = st.text_area('Draft content',value=details.get('body',''),height=220,max_chars=16000)
            st.caption('Saving an edit returns it to Draft and requires another review. Drafting is manual in this release.')
        if kind=='time':
            data['minutes'] = st.number_input('Minutes worked',min_value=1,max_value=1440,value=int(details.get('minutes',60)))
            data['hourly_rate'] = st.number_input('Hourly rate',min_value=0.0,max_value=1000000.0,value=float(details.get('hourly_rate',0)),step=50.0)
            currencies = ['INR','USD','EUR','GBP']
            data['currency'] = st.selectbox('Currency',currencies,index=currencies.index(details.get('currency','INR')))
            data['worked_on'] = st.date_input('Work date',value=date.fromisoformat(details['worked_on']) if details.get('worked_on') else date.today()).isoformat()
        status = 'Draft' if kind=='draft' else st.selectbox('Status',STATUSES[kind],index=STATUSES[kind].index(old['status']) if old else 0)
        save = st.form_submit_button('Save record',type='primary')
    if save:
        _save(store,{'kind':kind,'industry':industry,'title':title.strip(),'owner_name':owner.strip(),'parent_id':parent,
                     'status':status,'due_date':due.isoformat() if due else None,'details':data},old)
    if old and kind=='document':
        # Revalidate URLs loaded from storage before offering navigation.
        from work_hub_domain import validate
        try:
            validate(old)
            st.link_button('Open document',old['details']['url'])
        except ValueError:
            st.warning('Update this record with a valid HTTPS link.')
    if old and kind=='draft':
        st.write(f"**Review status:** {old['status']}")
        transitions = {'Draft':['Pending review'],'Pending review':['Approved','Rejected'],'Approved':[],'Rejected':[]}
        choices = transitions[old['status']]
        if choices:
            decision = st.selectbox('Review decision',choices,key=f'hub_decision_{old["id"]}')
            confirmed = st.checkbox('I reviewed this saved draft and confirm this decision.',key=f'hub_confirm_{old["id"]}_{old["version"]}')
            if st.button('Record decision',disabled=not confirmed,key=f'hub_review_{old["id"]}'):
                saved = {k:old.get(k) for k in ['kind','industry','title','owner_name','parent_id','due_date','details']}
                _save(store,dict(saved,status=decision),old)
        st.caption('The review applies to the saved version, not unsaved edits in the form above.')
    if kind=='time' and current_rows:
        totals = {}
        for row in current_rows:
            d=row['details']; currency=d['currency']
            totals[currency]=totals.get(currency,Decimal(0))+estimate(d['minutes'],d['hourly_rate'])
        for currency,total in totals.items():
            st.metric(f'Fee estimate ({currency})',f'{total:,.2f}')
        st.caption('Totals cover the displayed time records. Taxes, expenses and invoice issuance are not included.')


def render_work_hub(db,user_id,industry):
    st.header('Shared work hub')
    st.caption(f'{WORK_NAMES.get(industry,"Work")} · Client intake → work → tasks → review')
    st.caption('Records are saved to your signed-in account and separated by industry. Team sharing is not enabled.')
    if st.session_state.get('hub_identity') != user_id:
        for key in list(st.session_state):
            if key.startswith('hub_'):
                del st.session_state[key]
        st.session_state.hub_identity=user_id
    if st.session_state.get('hub_notice'):
        st.success(st.session_state.pop('hub_notice'))
    pending = st.session_state.pop('hub_next_selection',None)
    if pending and pending['industry'] == industry:
        st.session_state[f'hub_selected_{industry}_{pending["kind"]}'] = pending['id']
    store=HubStore(db,user_id,industry)
    try:
        rows,truncated=store.load()
    except Exception:
        st.error('The shared work hub is not available yet. Its database migration must be installed, and your login must be active.')
        st.caption('Setup file: supabase_work_hub.sql. Existing industry tools remain available.')
        return
    if truncated:
        st.warning('Showing the 500 most recently updated records in this industry. Older records are retained but not loaded in this view.')
    section=st.selectbox('Workspace section',list(SECTIONS),key=f'hub_section_{industry}')
    kind=SECTIONS[section]
    if kind is None:
        _overview(rows)
    elif kind=='activity':
        try:
            events=db.table('work_hub_events').select('created_at,record_id,event,version,title,status').eq('user_id',user_id).eq('industry',industry).order('created_at',desc=True).limit(100).execute().data
            st.dataframe(pd.DataFrame(events or []),hide_index=True,use_container_width=True)
            st.caption('Latest 100 changes, recorded by the database. Approvals are account-owner sign-offs, not independent team approvals.')
        except Exception:
            st.error('Could not load activity. Check your session and database setup.')
    else:
        _editor(store,rows,kind,industry)
