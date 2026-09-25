"""Task-level annotation operations reporting; no synthetic quality measurements."""
from io import BytesIO
import pandas as pd
import altair as alt
import streamlit as st
from bpo_trends import show_chart

MODALITIES = ['Image', 'Video', 'Text', 'Audio']
STATUSES = ['Not started', 'In progress', 'Completed']
REVIEWS = ['Not reviewed', 'Accepted', 'Rejected']
REQUIRED = ['Task_ID', 'Modality', 'Annotator', 'Project', 'Status', 'Created_At']


def prepare_tasks(source):
    missing = sorted(set(REQUIRED) - set(source.columns))
    if missing:
        raise ValueError('Missing columns: ' + ', '.join(missing))
    frame = source.copy()
    if frame.empty:
        raise ValueError('The file has no task rows.')
    for col in REQUIRED[:5]:
        if frame[col].isna().any() or frame[col].astype(str).str.strip().eq('').any():
            raise ValueError(f'{col} must be filled for every task.')
        frame[col] = frame[col].astype(str).str.strip()
    if frame.Task_ID.duplicated().any():
        raise ValueError('Use one latest row per Task_ID; duplicate task IDs would double-count work.')
    for col, allowed in [('Modality', MODALITIES), ('Status', STATUSES), ('Review_Status', REVIEWS)]:
        if col not in frame:
            frame[col] = 'Not reviewed'
        frame[col] = frame[col].fillna('Not reviewed').astype(str).str.strip().str.title()
        lookup = {value.lower(): value for value in allowed}
        frame[col] = frame[col].str.lower().map(lookup)
        if frame[col].isna().any():
            raise ValueError(f'{col} must use: ' + ', '.join(allowed))
    for col in ['Created_At', 'Completed_At']:
        if col not in frame:
            frame[col] = pd.NaT
        original = frame[col]
        parsed = pd.to_datetime(original, errors='coerce', utc=True).dt.tz_convert(None)
        present = original.notna() & original.astype(str).str.strip().ne('')
        if (present & parsed.isna()).any() or (col == 'Created_At' and parsed.isna().any()):
            raise ValueError(f'{col} contains missing or invalid dates; use ISO dates, for example 2026-09-01.')
        frame[col] = parsed
    if ((frame.Completed_At < frame.Created_At).fillna(False)).any():
        raise ValueError('Completed_At cannot be earlier than Created_At.')
    if ((frame.Status != 'Completed') & (frame.Review_Status != 'Not reviewed')).any():
        raise ValueError('Accepted or rejected review results require Status = Completed.')
    for col in ['Rework_Count', 'Annotation_Minutes']:
        raw = frame[col] if col in frame else pd.Series(float('nan'), index=frame.index)
        values = pd.to_numeric(raw, errors='coerce')
        supplied = raw.notna() & raw.astype(str).str.strip().ne('')
        invalid = supplied & (values.isna() | ~values.abs().lt(float('inf')) | values.lt(0))
        if invalid.any() or (col == 'Rework_Count' and (values.dropna() % 1 != 0).any()):
            raise ValueError(f'{col} must contain non-negative ' + ('whole counts.' if col == 'Rework_Count' else 'minutes.'))
        frame[col] = values
    frame['Turnaround_Hours'] = ((frame.Completed_At - frame.Created_At).dt.total_seconds()/3600).where(frame.Status.eq('Completed'))
    return frame


def summarize(frame):
    completed = frame.Status.eq('Completed')
    reviewed = frame.Review_Status.isin(['Accepted', 'Rejected'])
    return {
        'Tasks': len(frame), 'Completed': int(completed.sum()),
        'Open backlog': int((~completed).sum()),
        'Review backlog': int((completed & ~reviewed).sum()),
        'Acceptance %': 100 * frame.Review_Status.eq('Accepted').sum()/reviewed.sum() if reviewed.any() else float('nan'),
        'Rework %': 100 * frame.Rework_Count.gt(0).sum()/frame.Rework_Count.notna().sum() if frame.Rework_Count.notna().any() else float('nan'),
        'Turnaround hours': frame.Turnaround_Hours.mean(),
        'Annotation minutes': frame.Annotation_Minutes.mean(),
    }


def template():
    return pd.DataFrame([
        dict(Task_ID=f'DEMO-{i+1}', Modality=kind, Annotator='Sample annotator', Project='Demo project',
             Status='Completed', Created_At='2026-09-01T09:00:00Z', Completed_At='2026-09-01T11:00:00Z',
             Review_Status='Accepted', Rework_Count=0, Annotation_Minutes=12)
        for i, kind in enumerate(MODALITIES)])


def report_pdf(metrics, title='AI/ML Annotation Operations', note='Task snapshot filtered by creation date, project and modality. Acceptance measures accepted tasks among accepted/rejected tasks; it is not ground-truth accuracy. Missing measurements are not estimated.'):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    output = BytesIO()
    rows = [['Metric', 'Filtered result']] + [[key, 'Unavailable' if pd.isna(value) else f'{value:,.2f}'] for key, value in metrics.items()]
    table = Table(rows, colWidths=[250, 180])
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#155eef')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('BOTTOMPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),10),('GRID',(0,0),(-1,-1),.5,colors.HexColor('#dce5ef'))]))
    styles = getSampleStyleSheet()
    SimpleDocTemplate(output).build([Paragraph(title,styles['Title']),Spacer(1,20),table,Spacer(1,20),Paragraph(note,styles['BodyText'])])
    return output.getvalue()


def render_annotation_operations(plan_config, admit):
    st.subheader('AI/ML Annotation Operations')
    st.caption('Image · Video · Text · Audio — task throughput, review quality and delivery health')
    with st.expander('Data format and sample template'):
        st.write('Upload one current row per task. Counts represent tasks, not frames, objects, tokens or audio duration. Compare workloads within the same modality and project.')
        st.code(', '.join(REQUIRED))
        st.write('Optional: Completed_At, Review_Status (Not reviewed / Accepted / Rejected), Rework_Count, Annotation_Minutes. Dates use ISO format; timezone-free dates are treated as UTC. Status: Not started / In progress / Completed.')
        st.download_button('Download annotation template', template().to_csv(index=False).encode(), 'annotation-template.csv', 'text/csv')
        st.caption('Template rows are fictional examples. Replace them with your task export. Raw images, videos and audio files are not required.')
    upload = st.file_uploader(f'Upload annotation task export — max {plan_config["max_mb"]} MB', type=['csv','xlsx'], key='annotation_upload')
    if upload is None:
        st.info('Upload a task export to open your annotation dashboard.')
        return
    if upload.size > plan_config['max_mb']*1024*1024:
        st.error('This file exceeds your plan upload limit.')
        return
    try:
        source = pd.read_csv(BytesIO(upload.getvalue())) if upload.name.lower().endswith('.csv') else pd.read_excel(BytesIO(upload.getvalue()))
    except Exception:
        st.error('Could not read this export. Upload a valid CSV or Excel workbook.')
        return
    try:
        frame = prepare_tasks(source)
    except ValueError as error:
        st.error(str(error))
        return
    admit(upload, 'Annotation', {'schema_version': 1})
    a,b,c = st.columns(3)
    modalities = a.multiselect('Annotation modality', MODALITIES, default=MODALITIES)
    projects = b.multiselect('Projects', sorted(frame.Project.unique()), default=sorted(frame.Project.unique()))
    dates = c.date_input('Task creation dates (UTC)', value=(frame.Created_At.min().date(),frame.Created_At.max().date()), key='annotation_dates')
    if len(dates) != 2:
        st.info('Choose both dates.')
        return
    selected = frame[frame.Modality.isin(modalities) & frame.Project.isin(projects) & frame.Created_At.dt.date.between(*dates)]
    if selected.empty:
        st.info('No tasks match these filters.')
        return
    st.caption(f'{len(selected):,} tasks · creation-date cohort {dates[0]} to {dates[1]} · all charts and reports use these filters')
    metrics = summarize(selected)
    for offset in [0,4]:
        for col,(name,value) in zip(st.columns(4), list(metrics.items())[offset:offset+4]):
            col.metric(name, '—' if pd.isna(value) else (f'{int(value):,}' if offset == 0 else f'{value:.1f}'))
    st.caption('Acceptance is review acceptance, not model accuracy or inter-annotator agreement. Rework uses tasks with recorded rework counts. Turnaround includes elapsed waiting time; annotation minutes are recorded effort. Missing fields remain unavailable.')
    with st.container(key='primary_reporting_nav'):
        overview, charts, actions, reports = st.tabs(['Overview','Charts','Actions','Reports'])
    with overview:
        a,b = st.columns(2)
        with a:
            st.markdown('**Task status**')
            counts=selected.groupby('Status').size().reset_index(name='Tasks')
            show_chart(alt.Chart(counts).mark_bar(size=28,color='#155eef').encode(x=alt.X('Tasks:Q',title='Tasks',axis=alt.Axis(tickMinStep=1,format='d')), y=alt.Y('Status:N',sort=STATUSES),tooltip=['Status','Tasks']))
        with b:
            st.markdown('**Review outcomes**')
            counts=selected.groupby('Review_Status').size().reset_index(name='Tasks')
            show_chart(alt.Chart(counts).mark_bar(size=28,color='#0f8b8d').encode(x=alt.X('Tasks:Q',axis=alt.Axis(tickMinStep=1,format='d')),y=alt.Y('Review_Status:N',title='Review result'),tooltip=['Review_Status','Tasks']))
    with charts:
        completed=selected[selected.Status.eq('Completed') & selected.Completed_At.notna()]
        st.markdown('**Completed tasks by day and modality**')
        if completed.empty:
            st.info('Completion dates are needed for throughput charts.')
        else:
            daily=completed.assign(Day=completed.Completed_At.dt.normalize()).groupby(['Day','Modality']).size().reset_index(name='Tasks')
            show_chart(alt.Chart(daily).mark_bar(size=28).encode(x=alt.X('Day:T',axis=alt.Axis(format='%d %b',tickCount=6),title='Completion date (UTC)'),y='Tasks:Q',color=alt.Color('Modality:N',scale=alt.Scale(scheme='tableau10')),tooltip=['Day:T','Modality','Tasks']))
        st.caption(f'{int((selected.Status.eq("Completed") & selected.Completed_At.isna()).sum())} completed tasks have no completion date and are excluded from the throughput chart. Historical backlog is not inferred from a current snapshot.')
        st.markdown('**Annotator comparison — task counts**')
        by_person=selected.groupby(['Annotator','Modality']).size().reset_index(name='Tasks')
        show_chart(alt.Chart(by_person).mark_bar(size=28).encode(x=alt.X('Tasks:Q',axis=alt.Axis(tickMinStep=1,format='d')),y=alt.Y('Annotator:N',sort='-x',title=None),color='Modality:N',tooltip=['Annotator','Modality','Tasks']),height=max(260,30*selected.Annotator.nunique()))
        st.caption('Task counts do not measure difficulty-adjusted productivity and should not be used alone to rank people.')
    with actions:
        st.markdown('**Review priorities**')
        review=selected[selected.Status.eq('Completed') & selected.Review_Status.eq('Not reviewed')]
        rejected=selected[selected.Review_Status.eq('Rejected')]
        st.write(f'{len(review):,} completed tasks await review. {len(rejected):,} tasks have a rejected review result.')
        st.write('Next steps: assign pending reviews; sample rejected tasks against the annotation guidelines; confirm the cause; agree a correction and owner; then re-review corrected tasks. These are suggested actions, not confirmed root causes.')
        st.dataframe(selected[selected.Task_ID.isin(pd.concat([review,rejected]).Task_ID)][['Task_ID','Project','Modality','Annotator','Status','Review_Status']],hide_index=True,use_container_width=True)
    with reports:
        st.dataframe(selected,hide_index=True,use_container_width=True)
        st.download_button('Download filtered task report', selected.to_csv(index=False).encode(), 'annotation-report.csv','text/csv')
        if plan_config.get('pdf'):
            st.download_button('Download summary PDF',report_pdf(metrics),'annotation-summary.pdf','application/pdf')
