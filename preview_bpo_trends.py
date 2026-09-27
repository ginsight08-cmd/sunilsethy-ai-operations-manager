import pandas as pd
from bpo_trends import render_bpo_trends

render_bpo_trends(pd.DataFrame({
    'Date':['2026-01-01','2026-01-02','2026-02-01','bad'],
    'Team':['A','B','A','B'], 'Production':[100,80,110,90],
    'Target':[100,100,100,100], 'Quality_%':[95,96,97,95],
    'SLA_%':[96,97,98,96], 'AHT_Actual':[8,7,6,7],
}), {'Productivity':90,'Quality':95,'SLA':97,'AHT':8})
