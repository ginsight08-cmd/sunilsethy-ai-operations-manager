"""Date-based BPO reporting. Never invent historical observations."""
import pandas as pd
import altair as alt
import streamlit as st

METRICS = {'Productivity': 'Productivity', 'Quality': 'Quality_%', 'SLA': 'SLA_%', 'AHT': 'AHT_Actual'}

def prepare(source):
    frame = source.copy()
    if 'Date' not in frame:
        return frame.iloc[:0], len(frame)
    frame['Date'] = pd.to_datetime(frame['Date'], errors='coerce', utc=True).dt.tz_convert(None).dt.normalize()
    invalid = int(frame['Date'].isna().sum())
    for col in ['Production','Target','Quality_%','SLA_%','AHT_Actual','Error_Count']:
        if col in frame:
            frame[col] = pd.to_numeric(frame[col],errors='coerce').replace([float('inf'),float('-inf')],float('nan'))
    return frame.dropna(subset=['Date']), invalid

def aggregate(frame, frequency):
    rows=[]
    for period, group in frame.groupby(pd.Grouper(key='Date',freq=frequency)):
        if group.empty:
            continue
        row={'Period':period,'Records':len(group)}
        pairs=group[['Production','Target']].dropna() if {'Production','Target'} <= set(group) else pd.DataFrame()
        denominator=pairs['Target'].sum() if not pairs.empty else 0
        row['Productivity']=100*pairs['Production'].sum()/denominator if denominator>0 else float('nan')
        for metric,col in METRICS.items():
            if metric!='Productivity':
                row[metric]=group[col].mean() if col in group else float('nan')
        row['Errors']=group['Error_Count'].sum(min_count=1) if 'Error_Count' in group else float('nan')
        rows.append(row)
    return pd.DataFrame(rows)

def show_chart(chart, height=260):
    chart = chart.properties(height=height, background='#ffffff').configure_view(stroke=None).configure_axis(
        labelColor='#52657c', titleColor='#354c67', gridColor='#e7edf5',
        labelFontSize=11, titleFontSize=12, titlePadding=12, labelLimit=140
    ).configure_legend(labelColor='#354c67', titleColor='#354c67', orient='bottom')
    st.altair_chart(chart, use_container_width=True, theme=None)


def render_bpo_trends(source, targets):
    st.subheader('Analytics dashboard')
    st.caption('Explore the uploaded data by reporting period and team. Filters below affect this section only.')
    frame,invalid=prepare(source)
    if frame.empty:
        st.info('Upload records with valid dates to view trends. No historical values are estimated.')
        return
    if invalid:
        st.warning(f'{invalid} records with missing or invalid dates are excluded from these charts.')
    a,b,c=st.columns([2,2,1])
    dates=a.date_input('Reporting dates',value=(frame.Date.min().date(),frame.Date.max().date()),key='bpo_trend_dates')
    teams=sorted(frame['Team'].dropna().astype(str).unique()) if 'Team' in frame else []
    chosen=b.multiselect('Teams',teams,default=teams,key='bpo_trend_teams') if teams else []
    granularity=c.selectbox('Period',['Daily','Weekly','Monthly'],key='bpo_trend_period')
    if len(dates)!=2:
        st.info('Choose a start and end date.')
        return
    frame=frame[frame.Date.between(pd.Timestamp(dates[0]),pd.Timestamp(dates[1]))]
    if teams:
        frame=frame[frame.Team.astype(str).isin(chosen)]
    if frame.empty:
        st.info('No records match these filters.')
        return
    summary=aggregate(frame,{'Daily':'D','Weekly':'W-SUN','Monthly':'MS'}[granularity])
    st.caption(f'{len(frame):,} records · {frame.Date.min():%d %b %Y} – {frame.Date.max():%d %b %Y} · {granularity} view')
    columns=st.columns(4)
    for col,metric in zip(columns,METRICS):
        latest=summary.iloc[-1][metric]
        previous=summary.iloc[-2][metric] if len(summary)>1 else float('nan')
        delta=None if pd.isna(latest) or pd.isna(previous) else f'{latest-previous:+.2f}'+('' if metric=='AHT' else ' pp')
        col.metric(metric,'—' if pd.isna(latest) else f'{latest:.2f}'+('' if metric=='AHT' else '%'),delta,delta_color='inverse' if metric=='AHT' else 'normal')
    st.caption('Cards compare the latest populated period with the previous populated period; partial periods may not be comparable.')
    if len(summary) == 1:
        st.info('One reporting period is available. Points show the current position; upload multiple periods to see a trend.')
    st.caption('Weekly dates label the week ending Sunday; monthly dates label the first day of the month.')
    for start in [0,2]:
        for col,metric in zip(st.columns(2),list(METRICS)[start:start+2]):
            with col:
                st.markdown(f'**{metric} — '+('current period' if len(summary) == 1 else 'over time')+'**')
                plotted=summary[['Period',metric]].dropna()
                if plotted.empty:
                    st.info('No valid values for this metric.')
                    continue
                base=alt.Chart(plotted)
                base=(base.mark_circle(size=100, color='#155eef') if len(plotted)==1 else base.mark_line(point=True, color='#155eef', strokeWidth=3)).encode(
                    x=alt.X('Period:T',title='Reporting period',axis=alt.Axis(format='%d %b', tickCount=5, labelAngle=0)),
                    y=alt.Y(f'{metric}:Q',title=metric+(' (source units)' if metric=='AHT' else ' (%)'),scale=alt.Scale(zero=False)),
                    tooltip=['Period:T',alt.Tooltip(f'{metric}:Q',format='.2f')])
                target=alt.Chart(pd.DataFrame({'Target':[targets[metric]]})).mark_rule(color='#d97706',strokeDash=[5,4]).encode(y='Target:Q',tooltip=['Target:Q'])
                show_chart((base+target).interactive())
    st.caption('Orange dashed lines show configured targets. Productivity uses total production ÷ total valid target. Quality, SLA and AHT are record averages, not volume-weighted rates. Missing periods are omitted; line segments connect observed periods.')
    st.markdown('### Volume and quality drivers')
    volume_col, distribution_col = st.columns(2)
    with volume_col:
        st.markdown('**Workload by reporting period**')
        workload = alt.Chart(summary).mark_bar(color='#155eef', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X('Period:O', title='Reporting period', axis=alt.Axis(labelAngle=-30)),
            y=alt.Y('Records:Q', title='Uploaded records'),
            tooltip=['Period:T', 'Records:Q']).interactive()
        show_chart(workload)
        st.caption('Record count measures uploaded observations, not calls or production volume.')
    with distribution_col:
        st.markdown('**Quality distribution**')
        quality = frame[['Quality_%']].dropna() if 'Quality_%' in frame else pd.DataFrame()
        if quality.empty:
            st.info('Add Quality_% values to see the distribution.')
        else:
            show_chart(alt.Chart(quality).mark_bar(color='#0f8b8d').encode(
                x=alt.X('Quality_%:Q', bin=alt.Bin(maxbins=15), title='Quality (%)'),
                y=alt.Y('count():Q', title='Records'),
                tooltip=[alt.Tooltip('count():Q', title='Records')]).interactive())
    if teams:
        rows=[]
        for team,group in frame.groupby('Team'):
            # Aggregate all dates together, even across calendar years.
            combined=group.copy(); combined['Date']=pd.Timestamp('2000-01-01')
            row=aggregate(combined,'D').iloc[0].to_dict(); row['Team']=str(team); rows.append(row)
        st.markdown('**Team comparison — filtered date range**')
        team_frame=pd.DataFrame(rows)[['Team',*METRICS]]
        metric = st.selectbox('Compare teams by', list(METRICS), key='bpo_compare_metric')
        show_chart(alt.Chart(team_frame).mark_bar(color='#155eef', cornerRadiusEnd=4).encode(
            x=alt.X(f'{metric}:Q', title=metric + (' (source units)' if metric=='AHT' else ' (%)')),
            y=alt.Y('Team:N', sort='-x'), tooltip=['Team:N', alt.Tooltip(f'{metric}:Q',format='.2f')]), height=max(260, 32*len(team_frame)))
        st.dataframe(team_frame.round(2),hide_index=True,use_container_width=True)
        st.markdown('**Team performance matrix**')
        st.caption('Blue = meets target; amber = needs attention; grey = no value. Values are labelled; AHT uses source units and lower is better.')
        matrix = team_frame.melt(id_vars='Team', var_name='Metric', value_name='Value')
        def status(row):
            if pd.isna(row.Value): return 'No value'
            good = row.Value <= targets[row.Metric] if row.Metric == 'AHT' else row.Value >= targets[row.Metric]
            return 'Meets target' if good else 'Needs attention'
        matrix['Status'] = matrix.apply(status, axis=1)
        matrix['Label'] = matrix.apply(lambda r: '—' if pd.isna(r.Value) else f'{r.Value:.1f}'+('' if r.Metric == 'AHT' else '%'), axis=1)
        grid = alt.Chart(matrix).encode(
            x=alt.X('Metric:N', sort=list(METRICS), title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y('Team:N', title=None),
            tooltip=['Team:N','Metric:N',alt.Tooltip('Value:Q',format='.2f'),'Status:N'])
        cells = grid.mark_rect(stroke='#ffffff', strokeWidth=3).encode(color=alt.Color(
            'Status:N', scale=alt.Scale(domain=['Meets target','Needs attention','No value'],
            range=['#dbeafe','#fef3c7','#e5e7eb']), legend=alt.Legend(title=None)))
        labels = grid.mark_text(color='#18314f', fontSize=12).encode(text='Label:N')
        show_chart(cells+labels, height=max(160, 40*len(team_frame)))
    st.markdown('**Reporting-period details**')
    st.dataframe(summary.round(2),hide_index=True,use_container_width=True)
    st.download_button('Download filtered dashboard data', summary.to_csv(index=False).encode('utf-8'),
                       file_name='bpo-dashboard-summary.csv', mime='text/csv', key='bpo_dashboard_download')
