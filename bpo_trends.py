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

def render_bpo_trends(source, targets):
    st.subheader('Performance trends')
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
    columns=st.columns(4)
    for col,metric in zip(columns,METRICS):
        latest=summary.iloc[-1][metric]
        previous=summary.iloc[-2][metric] if len(summary)>1 else float('nan')
        delta=None if pd.isna(latest) or pd.isna(previous) else f'{latest-previous:+.2f}'+('' if metric=='AHT' else ' pp')
        col.metric(metric,'—' if pd.isna(latest) else f'{latest:.2f}'+('' if metric=='AHT' else '%'),delta,delta_color='inverse' if metric=='AHT' else 'normal')
    st.caption('Cards compare the latest populated period with the previous populated period; partial periods may not be comparable.')
    for start in [0,2]:
        for col,metric in zip(st.columns(2),list(METRICS)[start:start+2]):
            with col:
                st.markdown(f'**{metric} over time**')
                plotted=summary[['Period',metric]].dropna()
                if plotted.empty:
                    st.info('No valid values for this metric.')
                    continue
                base=alt.Chart(plotted).mark_line(point=True).encode(
                    x=alt.X('Period:T',title='Reporting period'),
                    y=alt.Y(f'{metric}:Q',title=metric+(' (source units)' if metric=='AHT' else ' (%)'),scale=alt.Scale(zero=False)),
                    tooltip=['Period:T',alt.Tooltip(f'{metric}:Q',format='.2f')])
                target=alt.Chart(pd.DataFrame({'Target':[targets[metric]]})).mark_rule(color='#d97706',strokeDash=[5,4]).encode(y='Target:Q',tooltip=['Target:Q'])
                st.altair_chart((base+target).interactive(),use_container_width=True)
    st.caption('Orange dashed lines show configured targets. Productivity uses total production ÷ total valid target. Quality, SLA and AHT are record averages, not volume-weighted rates. Missing periods are omitted; line segments connect observed periods.')
    if teams:
        rows=[]
        for team,group in frame.groupby('Team'):
            # Aggregate all dates together, even across calendar years.
            combined=group.copy(); combined['Date']=pd.Timestamp('2000-01-01')
            row=aggregate(combined,'D').iloc[0].to_dict(); row['Team']=str(team); rows.append(row)
        st.markdown('**Team comparison — filtered date range**')
        team_frame=pd.DataFrame(rows)[['Team',*METRICS]]
        metric = st.selectbox('Compare teams by', list(METRICS), key='bpo_compare_metric')
        st.altair_chart(alt.Chart(team_frame).mark_bar().encode(
            x=alt.X(f'{metric}:Q', title=metric + (' (source units)' if metric=='AHT' else ' (%)')),
            y=alt.Y('Team:N', sort='-x'), tooltip=['Team:N', alt.Tooltip(f'{metric}:Q',format='.2f')]), use_container_width=True)
        st.dataframe(team_frame,hide_index=True,use_container_width=True)
    st.markdown('**Reporting-period details**')
    st.dataframe(summary,hide_index=True,use_container_width=True)
