"""BPO excellence calculations. No inferred causes or automatic CAPA closure."""
import math
from datetime import date

import pandas as pd


def capacity_plan(volume, aht_seconds, hours, occupancy, shrinkage, available):
    values = [volume, aht_seconds, hours, occupancy, shrinkage, available]
    if not all(math.isfinite(float(v)) for v in values):
        raise ValueError('Enter finite numbers for all planning inputs.')
    if volume < 0 or aht_seconds <= 0 or hours <= 0 or available < 0:
        raise ValueError('Volume and staff cannot be negative; AHT and hours must be positive.')
    if not 0 < occupancy <= 100 or not 0 <= shrinkage < 100:
        raise ValueError('Occupancy must be above 0 and at most 100%; shrinkage must be below 100%.')
    workload = volume * aht_seconds / 3600
    effective = hours * (occupancy / 100) * (1 - shrinkage / 100)
    required = math.ceil(workload / effective)
    return {'workload_hours': workload, 'required_staff': required,
            'staff_gap': required - available, 'capacity': available * effective * 3600 / aht_seconds}


def pareto(df):
    if df is None or not {'Error_Category', 'Error_Count'} <= set(df.columns):
        return pd.DataFrame(), 0
    counts = pd.to_numeric(df['Error_Count'], errors='coerce')
    valid = counts.notna() & counts.ge(0) & counts.lt(float('inf'))
    clean = pd.DataFrame({'Category': df['Error_Category'].fillna('').astype(str).str.strip(),
                          'Errors': counts})[valid]
    clean.loc[clean.Category.eq(''), 'Category'] = 'Unspecified'
    result = clean.groupby('Category', as_index=False).Errors.sum().sort_values('Errors', ascending=False)
    total = result.Errors.sum()
    result['Cumulative_%'] = result.Errors.cumsum() / total * 100 if total > 0 else 0.0
    return result, int((~valid).sum())


def quality_rates(inspected, defective, defects, opportunities):
    if inspected <= 0 or not 0 <= defective <= inspected or opportunities < 1:
        raise ValueError('Enter inspected units > 0, defective units within that total, and opportunities >= 1.')
    if not defective <= defects <= defective * opportunities:
        raise ValueError('Defects must cover defective units and cannot exceed total opportunities.')
    return {'yield': (1 - defective / inspected) * 100,
            'dpmo': defects / (inspected * opportunities) * 1_000_000}


def validate_project(p):
    errors = []
    for field in ['title', 'owner', 'problem', 'customer_need']:
        if not str(p.get(field, '')).strip():
            errors.append(f'{field.replace("_", " ").capitalize()} is required.')
    try:
        date.fromisoformat(p.get('due_date', ''))
    except (TypeError, ValueError):
        errors.append('A valid due date is required.')
    for field in ['severity', 'occurrence', 'detection']:
        score = p.get(field)
        if type(score) is not int or not 1 <= score <= 10:
            errors.append(f'{field.capitalize()} must be an integer from 1 to 10.')
    if p.get('status') not in ['Open', 'Investigating', 'Implementing', 'Effectiveness review', 'Closed']:
        errors.append('Choose a valid action status.')
    if p.get('stage') not in ['Define', 'Measure', 'Analyze', 'Improve', 'Control']:
        errors.append('Choose a valid DMAIC stage.')
    if p.get('status') in ['Implementing', 'Effectiveness review', 'Closed']:
        for field in ['root_cause', 'cause_evidence', 'corrective_action', 'preventive_action']:
            if not str(p.get(field, '')).strip():
                errors.append(f'{field.replace("_", " ").capitalize()} is required before implementation.')
    if p.get('status') == 'Closed':
        if p.get('stage') != 'Control':
            errors.append('Move the project to Control before closure.')
        for field in ['effectiveness_evidence', 'reviewer', 'control_plan', 'metric', 'baseline', 'target', 'actual']:
            if not str(p.get(field, '')).strip():
                errors.append(f'{field.replace("_", " ").capitalize()} is required before closure.')
        if not p.get('effectiveness_confirmed'):
            errors.append('Confirm effectiveness before closing the action.')
    return errors
