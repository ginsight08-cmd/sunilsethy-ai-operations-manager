"""Operations Excellence workbench; existing app authentication/trial gate applies."""
import json
from datetime import date, datetime, timezone
from uuid import uuid4

import pandas as pd
import streamlit as st

from excellence_engine import capacity_plan, pareto, quality_rates, validate_project

STATUSES = ['Open', 'Investigating', 'Implementing', 'Effectiveness review', 'Closed']
STAGES = ['Define', 'Measure', 'Analyze', 'Improve', 'Control']
TEXT_FIELDS = ['title', 'owner', 'problem', 'customer_need', 'scope', 'sipoc', 'metric',
               'baseline', 'target', 'actual', 'measurement_plan', 'whys', 'fishbone',
               'root_cause', 'cause_evidence', 'containment', 'corrective_action',
               'preventive_action', 'pilot_plan', 'effectiveness_evidence', 'reviewer',
               'control_plan', 'customer_value', 'failure_mode', 'failure_effect', 'controls']


def _backup(projects):
    st.download_button('Download project backup', json.dumps({'version': 1, 'projects': projects}, indent=2),
                       'bpo_excellence_projects.json', 'application/json', key='ox_backup')
    with st.expander('Restore projects from a backup'):
        uploaded = st.file_uploader('Project backup JSON (up to 1 MB)', type=['json'], key='ox_restore_file')
        if st.button('Import projects', key='ox_restore') and uploaded:
            try:
                if uploaded.size > 1_000_000:
                    raise ValueError('Backup exceeds 1 MB.')
                payload = json.loads(uploaded.getvalue())
                if not isinstance(payload, dict) or payload.get('version') != 1:
                    raise ValueError('Unsupported backup version.')
                rows = payload.get('projects')
                if not isinstance(rows, list) or len(rows) + len(projects) > 100:
                    raise ValueError('A workspace supports up to 100 projects.')
                restored = []
                for row in rows:
                    if not isinstance(row, dict):
                        raise ValueError('Invalid project record.')
                    if any(not isinstance(row.get(k, ''), str) or len(row.get(k, '')) > 6000 for k in TEXT_FIELDS):
                        raise ValueError('Invalid or oversized project text.')
                    clean = {k: row.get(k, '') for k in TEXT_FIELDS}
                    for k in ['status', 'stage', 'due_date', 'severity', 'occurrence', 'detection']:
                        clean[k] = row.get(k)
                    clean['effectiveness_confirmed'] = row.get('effectiveness_confirmed') is True
                    errors = validate_project(clean)
                    if errors:
                        raise ValueError(errors[0])
                    clean['id'] = str(uuid4())
                    clean['updated_at'] = datetime.now(timezone.utc).isoformat()
                    restored.append(clean)
                projects.extend(restored)
                st.success(f'Imported {len(restored)} projects. Existing projects were retained.')
                st.rerun()
            except (ValueError, TypeError, KeyError):
                st.error('Could not import this backup. Check its version, required fields, scores, and size.')


def _portfolio(projects, result):
    st.subheader('Risk → improvement → customer value')
    st.write('Start with a measured gap, validate the cause, assign action, then verify the result before closure.')
    open_rows = [p for p in projects if p['status'] != 'Closed']
    overdue = [p for p in open_rows if p['due_date'] < date.today().isoformat()]
    a, b, c = st.columns(3)
    a.metric('Open improvements', len(open_rows))
    b.metric('Overdue actions', len(overdue))
    c.metric('Verified closures', len(projects) - len(open_rows))
    findings = result.get('findings') if isinstance(result, dict) else None
    if isinstance(findings, pd.DataFrame) and not findings.empty:
        st.markdown('#### Gaps from your latest operational upload')
        st.dataframe(findings, hide_index=True, use_container_width=True)
        options = findings.to_dict('records')
        choice = st.selectbox('Use a finding as a project starting point', range(len(options)),
                              format_func=lambda i: f"{options[i].get('Team', '')}: {options[i].get('Finding', '')}")
        if st.button('Use this gap in the project form', key='ox_seed'):
            st.session_state.ox_seed = str(options[choice].get('Finding', ''))
            st.success('Finding copied. Select New project in RCA & CAPA to continue.')
    else:
        st.info('Analyze a file in Performance Dashboard to bring measured gaps here, or create a project manually.')
    if projects:
        rows = [{**{k: p.get(k, '') for k in ['id', 'title', 'owner', 'stage', 'status', 'due_date', 'customer_value']},
                 'RPN': p['severity'] * p['occurrence'] * p['detection']} for p in projects]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    _backup(projects)


def _workforce():
    st.subheader('Workforce capacity planning')
    st.caption('Scenario inputs are for one planning period. Enter AHT in seconds, including after-contact work.')
    a, b = st.columns(2)
    volume = a.number_input('Forecast contacts / cases', min_value=0, value=1000, key='ox_volume')
    aht = b.number_input('Average handling time (seconds)', min_value=1, value=300, key='ox_aht')
    hours = a.number_input('Paid hours per person in the period', min_value=0.25, value=8.0, step=0.25, key='ox_hours')
    available = b.number_input('Available scheduled staff', min_value=0, value=15, key='ox_staff')
    occupancy = a.number_input('Target occupancy (%)', min_value=1.0, max_value=100.0, value=85.0, key='ox_occupancy')
    shrinkage = b.number_input('Shrinkage (%)', min_value=0.0, max_value=99.0, value=30.0, key='ox_shrinkage')
    st.caption('Shrinkage covers paid time unavailable for contacts, such as breaks, training and absence. Do not deduct it twice.')
    plan = capacity_plan(volume, aht, hours, occupancy, shrinkage, available)
    a, b, c = st.columns(3)
    a.metric('Workload hours', f"{plan['workload_hours']:.1f}")
    b.metric('Required scheduled staff', plan['required_staff'])
    c.metric('Staff gap (+ shortage)', plan['staff_gap'])
    st.info('This is a workload capacity estimate. It does not predict voice queue service level or replace interval-level Erlang/skill-based scheduling.')
    rows = []
    for factor in [0.9, 1.0, 1.1, 1.2]:
        forecast = round(volume * factor)
        p = capacity_plan(forecast, aht, hours, occupancy, shrinkage, available)
        rows.append({'Volume scenario': f'{factor:.0%}', 'Contacts': forecast,
                     'Required staff': p['required_staff'], 'Staff gap': p['staff_gap']})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.download_button('Export workforce scenarios', pd.DataFrame(rows).to_csv(index=False), 'workforce_scenarios.csv', 'text/csv')
    st.write('**Planning actions:** validate demand by interval and skill; compare coverage with breaks and leave; test overflow/cross-training; review actual volume, AHT and adherence daily.')


def _quality(df):
    st.subheader('Quality tools')
    st.markdown('#### Defect Pareto')
    table, excluded = pareto(df)
    if table.empty or table.Errors.sum() <= 0:
        st.info('Analyze operational data containing Error_Category and nonnegative Error_Count to build a Pareto.')
    else:
        st.bar_chart(table.set_index('Category')['Errors'])
        st.dataframe(table, hide_index=True, use_container_width=True)
        if excluded:
            st.warning(f'{excluded} rows excluded because Error_Count was missing, invalid or negative.')
        st.caption('Categories identify where to investigate; they do not establish a root cause.')
    st.markdown('#### Inspection yield and defects per million opportunities')
    st.caption('Use one consistent inspected population and a defined number of defect opportunities per unit. Defective units and total defects are different measures.')
    a, b = st.columns(2)
    units = a.number_input('Inspected units', min_value=1, value=1000, key='ox_units')
    defective = b.number_input('Units with at least one defect', min_value=0, value=30, key='ox_defective')
    defects = a.number_input('Total defects observed', min_value=0, value=40, key='ox_defects')
    opportunities = b.number_input('Defect opportunities per unit', min_value=1, value=5, key='ox_opportunities')
    try:
        rates = quality_rates(units, defective, defects, opportunities)
        a.metric('Inspection yield', f"{rates['yield']:.2f}%")
        b.metric('DPMO', f"{rates['dpmo']:,.0f}")
    except ValueError as e:
        st.error(str(e))
    st.markdown('#### Lean flow efficiency')
    a, b = st.columns(2)
    va = a.number_input('Value-added time per case (minutes)', min_value=0.0, value=5.0, key='ox_va')
    lead = b.number_input('End-to-end lead time per case (minutes)', min_value=0.01, value=60.0, key='ox_lead')
    if va > lead:
        st.error('Value-added time cannot exceed end-to-end lead time.')
    else:
        st.metric('Process cycle efficiency', f'{va / lead * 100:.1f}%')
    st.write('Map handoffs and waiting time; review rework, over-processing, duplicate entry and bottlenecks. Record a pilot and quality guardrails in the improvement project.')


def _project_editor(projects):
    st.subheader('RCA & CAPA — DMAIC improvement project')
    if 'ox_selected_next' in st.session_state:
        st.session_state.ox_project_choice = st.session_state.pop('ox_selected_next')
        st.success('Project saved for this session. Download a backup from Overview before leaving.')
    selected = st.selectbox('Project', ['New project'] + [p['id'] for p in projects],
                            format_func=lambda x: next((p['title'] for p in projects if p['id'] == x), x), key='ox_project_choice')
    p = next((row for row in projects if row['id'] == selected), {})
    with st.form(f'ox_form_{selected}'):
        draft = {}
        def text(field, label, multiline=False, default=''):
            fn = st.text_area if multiline else st.text_input
            draft[field] = fn(label, value=p.get(field, default), max_chars=6000, key=f'ox_{selected}_{field}')
        st.markdown('#### Define — customer need and process scope')
        text('title', 'Project title')
        text('owner', 'Accountable owner')
        text('problem', 'Measured problem / gap', True, st.session_state.get('ox_seed', ''))
        text('customer_need', 'Voice of customer → critical-to-quality requirement', True)
        text('scope', 'Scope and boundaries', True)
        text('sipoc', 'SIPOC: suppliers → inputs → process → outputs → customers', True)
        draft['due_date'] = st.date_input('Action due date', value=date.fromisoformat(p['due_date']) if p else date.today()).isoformat()
        draft['stage'] = st.selectbox('DMAIC stage', STAGES, index=STAGES.index(p.get('stage', 'Define')))
        draft['status'] = st.selectbox('Action status', STATUSES, index=STATUSES.index(p.get('status', 'Open')))
        st.markdown('#### Measure — baseline, target and data definition')
        for field, label in [('metric', 'Success metric and unit'), ('baseline', 'Baseline value and period'),
                             ('target', 'Target value and due period'), ('measurement_plan', 'Sampling / measurement plan and source')]:
            text(field, label)
        st.markdown('#### Analyze — validate the root cause')
        text('whys', '5 Whys: record each why and supporting evidence', True)
        text('fishbone', 'Fishbone hypotheses: people, method, system, measurement, materials, environment', True)
        text('root_cause', 'Validated root cause', True)
        text('cause_evidence', 'Evidence confirming the cause (test, sample, observation)', True)
        st.markdown('#### Risk assessment — FMEA')
        text('failure_mode', 'Failure mode')
        text('failure_effect', 'Effect on the customer / operation')
        text('controls', 'Current preventive and detection controls', True)
        st.caption('Score 1–10: severity (10 = most serious), occurrence (10 = most frequent), detection (10 = hardest to detect). RPN = S × O × D; also review severity independently.')
        for field in ['severity', 'occurrence', 'detection']:
            draft[field] = st.number_input(field.capitalize(), min_value=1, max_value=10, value=int(p.get(field, 1)))
        st.markdown('#### Improve — containment, correction and prevention')
        for field, label in [('containment', 'Immediate containment'), ('corrective_action', 'Corrective action to remove the cause'),
                             ('preventive_action', 'Preventive action for similar processes'), ('pilot_plan', 'Pilot / PDCA plan: test, guardrails, results and adoption decision')]:
            text(field, label, True)
        st.markdown('#### Control — effectiveness and customer value')
        text('actual', 'Actual result and measurement period')
        text('effectiveness_evidence', 'Effectiveness evidence and review date', True)
        text('reviewer', 'Effectiveness reviewer')
        text('control_plan', 'Control plan: metric, frequency, owner, trigger and response', True)
        text('customer_value', 'Verified customer value: faster resolution, fewer repeats, better accuracy or effort reduction', True)
        draft['effectiveness_confirmed'] = st.checkbox('Reviewer confirmed the action is effective', value=p.get('effectiveness_confirmed', False))
        saved = st.form_submit_button('Save project')
    if saved:
        errors = validate_project(draft)
        if errors:
            for error in errors:
                st.error(error)
        elif not p and len(projects) >= 100:
            st.error('Workspace limit is 100 projects. Export a backup before starting another workspace.')
        else:
            draft['id'] = p.get('id', str(uuid4()))
            draft['updated_at'] = datetime.now(timezone.utc).isoformat()
            if p:
                projects[projects.index(p)] = draft
            else:
                projects.append(draft)
            st.session_state.ox_selected_next = draft['id']
            st.rerun()
    if p:
        st.metric('Risk priority number', p['severity'] * p['occurrence'] * p['detection'])
        if p['severity'] >= 9:
            st.warning('High severity: review this risk even if the overall RPN is low.')


def render_operations_excellence():
    st.header('BPO Operations Excellence')
    st.caption('Workforce • Quality • Lean Six Sigma • RCA & CAPA • Customer value')
    user_id = st.session_state.get('user_id', '')
    if st.session_state.get('ox_user') != user_id:
        for key in list(st.session_state):
            if key.startswith('ox_'):
                del st.session_state[key]
        st.session_state.ox_user = user_id
    projects = st.session_state.setdefault('ox_projects', [])
    st.info('Projects are session drafts. Download a project backup before signing out or reloading; restore it here next time.')
    tab = st.radio('Excellence workspace', ['Overview', 'Workforce planning', 'Quality & Lean tools', 'RCA & CAPA'], horizontal=True, key='ox_tab')
    if tab == 'Overview':
        _portfolio(projects, st.session_state.get('analysis_result'))
    elif tab == 'Workforce planning':
        _workforce()
    elif tab == 'Quality & Lean tools':
        _quality(st.session_state.get('analysis_df'))
    else:
        _project_editor(projects)
    with st.expander('Framework references'):
        st.markdown('[ASQ DMAIC](https://asq.org/quality-resources/dmaic) · [ASQ Five Whys](https://asq.org/quality-resources/five-whys) · [ASQ FMEA](https://asq.org/quality-resources/fmea) · [Genesys workforce management](https://docs.genesys.com/Documentation/WM)')
