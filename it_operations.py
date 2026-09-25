"""Cross-functional IT delivery reporting from current work-item exports."""
from io import BytesIO
import pandas as pd
import altair as alt
import streamlit as st
from bpo_trends import show_chart

WORKFLOWS = ['Service desk', 'Software delivery', 'QA/testing', 'AI/data operations', 'BPO']
STATES = ['Not started', 'In progress', 'Blocked', 'Completed']
REQUIRED = ['Work_Item_ID','Workflow','Assignee','Project','Status','Created_At']


def prepare_work(source):
    missing = sorted(set(REQUIRED)-set(source))
    if missing: raise ValueError('Missing columns: '+', '.join(missing))
    frame=source.copy()
    if frame.empty: raise ValueError('No work items found.')
    for col in REQUIRED[:-1]:
        if frame[col].isna().any() or frame[col].astype(str).str.strip().eq('').any():
            raise ValueError(f'{col} must be filled for every work item.')
        frame[col]=frame[col].astype(str).str.strip()
    if frame.Work_Item_ID.duplicated().any(): raise ValueError('Use one latest row per Work_Item_ID.')
    for col,values in [('Workflow',WORKFLOWS),('Status',STATES)]:
        frame[col]=frame[col].str.lower().map({v.lower():v for v in values})
        if frame[col].isna().any(): raise ValueError(f'{col} must use: '+', '.join(values))
    for col in ['Created_At','Completed_At','Due_At']:
        raw=frame[col] if col in frame else pd.Series(pd.NaT,index=frame.index)
        parsed=pd.to_datetime(raw,errors='coerce',utc=True,format='mixed').dt.tz_convert(None)
        supplied=raw.notna() & raw.astype(str).str.strip().ne('')
        if (supplied & parsed.isna()).any() or (col=='Created_At' and parsed.isna().any()):
            raise ValueError(f'{col} contains invalid or missing dates.')
        frame[col]=parsed
    if (frame.Completed_At < frame.Created_At).any(): raise ValueError('Completion cannot precede creation.')
    if (frame.Status.ne('Completed') & frame.Completed_At.notna()).any(): raise ValueError('Completion dates require Completed status.')
    frame['Cycle_Hours']=((frame.Completed_At-frame.Created_At).dt.total_seconds()/3600).where(frame.Status.eq('Completed'))
    return frame


def summarize_work(frame, now=None):
    now=pd.Timestamp.now(tz='UTC').tz_localize(None) if now is None else pd.Timestamp(now)
    opened=frame.Status.ne('Completed')
    measured=frame.Status.eq('Completed') & frame.Completed_At.notna() & frame.Due_At.notna()
    return {'Work items':len(frame),'Completed':int((~opened).sum()),'Open':int(opened.sum()),
            'Blocked':int(frame.Status.eq('Blocked').sum()),
            'Overdue open':int((opened & frame.Due_At.lt(now)).sum()),
            'On-time delivery %':100*frame.loc[measured,'Completed_At'].le(frame.loc[measured,'Due_At']).mean() if measured.any() else float('nan'),
            'Mean cycle hours':frame.Cycle_Hours.mean()}


def work_template():
    return pd.DataFrame([dict(Work_Item_ID=f'DEMO-{i+1}',Workflow=w,Assignee='Sample owner',Project='Demo project',Status='In progress',Created_At='2026-09-01T09:00:00Z',Due_At='2026-09-05T17:00:00Z',Completed_At='') for i,w in enumerate(WORKFLOWS)])


def render_it_operations(plan_config, admit):
    st.subheader('IT Operations — delivery and control centre')
    st.caption('Service desk · Software delivery · QA/testing · AI/data operations · BPO')
    with st.expander('Upload guide and template'):
        st.write('Use one current row per ticket, issue or task. Choose the workflow that describes each item. This dashboard measures delivery operations; it does not monitor live infrastructure or replace your ticketing system.')
        st.code(', '.join(REQUIRED))
        st.write('Optional: Due_At and Completed_At. Status: Not started / In progress / Blocked / Completed. Use ISO dates with timezones; dates without timezones are treated as UTC.')
        st.download_button('Download IT operations template',work_template().to_csv(index=False).encode(),'it-operations-template.csv','text/csv')
        st.caption('Template rows are examples; replace them before analysis.')
    upload=st.file_uploader(f'Upload IT work-item export — max {plan_config["max_mb"]} MB',type=['csv','xlsx'],key='it_ops_upload')
    if upload is None:
        st.info('Upload your work-item export to see delivery, workload and risk dashboards. For detailed label-review metrics, select AI/ML Annotation in Workspace settings.')
        return
    if upload.size > plan_config['max_mb']*1024*1024:
        st.error('File exceeds your plan upload limit.');return
    try:
        source=pd.read_csv(BytesIO(upload.getvalue())) if upload.name.lower().endswith('.csv') else pd.read_excel(BytesIO(upload.getvalue()))
    except Exception:
        st.error('Could not read this file. Use a valid CSV or Excel workbook.');return
    try: frame=prepare_work(source)
    except ValueError as error: st.error(str(error));return
    admit(upload,'IT Operations',{'schema_version':1})
    a,b,c=st.columns(3)
    workflows=a.multiselect('Workflows',WORKFLOWS,default=WORKFLOWS)
    projects=b.multiselect('Projects',sorted(frame.Project.unique()),default=sorted(frame.Project.unique()))
    dates=c.date_input('Creation dates (UTC)',value=(frame.Created_At.min().date(),frame.Created_At.max().date()),key='it_ops_dates')
    if len(dates)!=2: st.info('Choose both dates.');return
    frame=frame[frame.Workflow.isin(workflows)&frame.Project.isin(projects)&frame.Created_At.dt.date.between(*dates)]
    if frame.empty: st.info('No work items match your filters.');return
    metrics=summarize_work(frame)
    st.caption(f'{len(frame):,} work items in the selected creation-date cohort. All sections use these filters.')
    for col,(name,value) in zip(st.columns(4),list(metrics.items())[:4]):col.metric(name,f'{value:,}')
    with st.container(key='it_reporting_nav'):
        overview,delivery,workforce,quality,risks,reports=st.tabs(['Overview','Delivery','Workforce','Quality','Risks & Actions','Reports'])
    with overview:
        counts=frame.groupby(['Workflow','Status']).size().reset_index(name='Items')
        show_chart(alt.Chart(counts).mark_bar(size=28).encode(x=alt.X('Items:Q',axis=alt.Axis(tickMinStep=1,format='d')),y=alt.Y('Workflow:N',title=None),color=alt.Color('Status:N',scale=alt.Scale(domain=STATES,range=['#94a3b8','#155eef','#d97706','#0f8b8d'])),tooltip=['Workflow','Status','Items']))
    with delivery:
        cols=st.columns(3)
        for col,key in zip(cols,['Overdue open','On-time delivery %','Mean cycle hours']):
            col.metric(key,'—' if pd.isna(metrics[key]) else f'{metrics[key]:.1f}')
        st.caption('On-time delivery uses completed work with both due and completion dates. Cycle time includes elapsed waiting time. Overdue uses the current UTC time.')
        done=frame[frame.Status.eq('Completed')&frame.Completed_At.notna()]
        if done.empty: st.info('Completion dates are needed to display delivery history.')
        else:
            daily=done.assign(Day=done.Completed_At.dt.normalize()).groupby(['Day','Workflow']).size().reset_index(name='Completed')
            show_chart(alt.Chart(daily).mark_bar(size=28).encode(x=alt.X('Day:T',axis=alt.Axis(format='%d %b',tickCount=6)),y='Completed:Q',color='Workflow:N',tooltip=['Day:T','Workflow','Completed']))
    with workforce:
        counts=frame[frame.Status.ne('Completed')].groupby(['Assignee','Workflow']).size().reset_index(name='Open items')
        if counts.empty: st.info('No open work items in this cohort.')
        else: show_chart(alt.Chart(counts).mark_bar(size=28).encode(x=alt.X('Open items:Q',axis=alt.Axis(tickMinStep=1,format='d')),y=alt.Y('Assignee:N',sort='-x'),color='Workflow:N',tooltip=['Assignee','Workflow','Open items']),height=max(260,30*counts.Assignee.nunique()))
        st.caption('Open-item count is workload visibility, not utilisation or capacity. Those require effort estimates, availability and shift data.')
    with quality:
        st.info('Quality measurements are not inferred from task completion. Use AI/ML Annotation for review acceptance and rework. Defect rates, test coverage and incident recurrence require their own measured exports.')
        qa=frame[frame.Workflow.eq('QA/testing')]
        st.dataframe(qa[['Work_Item_ID','Project','Assignee','Status']],hide_index=True,use_container_width=True)
    with risks:
        now=pd.Timestamp.now(tz='UTC').tz_localize(None)
        issues=frame[frame.Status.eq('Blocked')|(frame.Status.ne('Completed')&frame.Due_At.lt(now))].copy()
        st.write('Review blocked and overdue work with its assigned owner. Confirm the cause, agree a corrective action and due date, then verify completion. Use Shared work hub to track follow-up work.')
        st.dataframe(issues[['Work_Item_ID','Workflow','Project','Assignee','Status','Due_At']],hide_index=True,use_container_width=True)
    with reports:
        st.dataframe(frame,hide_index=True,use_container_width=True)
        st.download_button('Download filtered work-item report',frame.to_csv(index=False).encode(),'it-operations-report.csv','text/csv')
        if plan_config.get('pdf'):
            from annotation_operations import report_pdf
            st.download_button('Download summary PDF',report_pdf(metrics,title='IT Operations Manager',note='Current work-item snapshot filtered by creation date, workflow and project. On-time delivery uses completed items with due and completion dates. Missing measurements are not estimated.'),'it-operations-summary.pdf','application/pdf')
