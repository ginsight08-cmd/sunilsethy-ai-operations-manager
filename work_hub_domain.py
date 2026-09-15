"""Validation and presentation for persistent, account-scoped work records."""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlsplit

STATUSES = {
    'client': ['Lead', 'Qualified', 'Active', 'Archived'],
    'work': ['Intake', 'In progress', 'On hold', 'Completed'],
    'task': ['Open', 'In progress', 'Done'],
    'document': ['Reference'],
    'draft': ['Draft', 'Pending review', 'Approved', 'Rejected'],
    'time': ['Recorded'],
}
INDUSTRIES = ['BPO', 'Manufacturing', 'CaseManagement', 'Retail', 'Logistics', 'Healthcare']
PARENTS = {'work': 'client', 'task': 'work', 'document': 'work', 'draft': 'work', 'time': 'work'}


def validate(record):
    kind = record.get('kind')
    if kind not in STATUSES or record.get('industry') not in INDUSTRIES:
        raise ValueError('Choose a supported record type and industry.')
    if not isinstance(record.get('title'), str) or not record['title'].strip() or len(record['title']) > 300:
        raise ValueError('Enter a title of 1–300 characters.')
    if record.get('status') not in STATUSES[kind]:
        raise ValueError('Invalid status for this record.')
    if kind in PARENTS and not record.get('parent_id'):
        raise ValueError('Select the related client or work record.')
    if record.get('due_date'):
        try:
            date.fromisoformat(record['due_date'])
        except (ValueError, TypeError):
            raise ValueError('Enter a valid due date.')
    data = record.get('details', {})
    if not isinstance(data, dict):
        raise ValueError('Record details must be an object.')
    if kind == 'document':
        url = data.get('url', '')
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Use a HTTPS document link without embedded credentials.')
    if kind == 'draft' and not str(data.get('body', '')).strip():
        raise ValueError('Enter draft content for review.')
    if kind == 'time':
        estimate(data.get('minutes'), data.get('hourly_rate'))
        if data.get('currency') not in ['INR', 'USD', 'EUR', 'GBP']:
            raise ValueError('Choose a supported currency.')
    return record


def estimate(minutes, hourly_rate):
    try:
        m, r = Decimal(str(minutes)), Decimal(str(hourly_rate))
        if not m.is_finite() or not r.is_finite() or m < 1 or m > 1440 or r < 0 or r > 1000000:
            raise ValueError('Time must be 1–1440 minutes; hourly rate must be 0–1,000,000.')
        return (m / 60 * r).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError):
        raise ValueError('Enter valid time and hourly rate.')


def draft_transition(old_status, new_status, content_changed=False):
    if content_changed:
        return new_status == 'Draft'
    allowed = {'Draft': {'Draft', 'Pending review'}, 'Pending review': {'Draft', 'Approved', 'Rejected'},
               'Approved': {'Draft'}, 'Rejected': {'Draft'}}
    return new_status in allowed.get(old_status, set())


class HubStore:
    def __init__(self, db, user_id, industry):
        self.db, self.user_id, self.industry = db, user_id, industry

    def load(self):
        response = self.db.table('work_hub_records').select('*').eq('user_id', self.user_id).eq('industry', self.industry).order('updated_at', desc=True).limit(501).execute()
        rows = list(response.data or [])
        return rows[:500], len(rows) > 500

    def save(self, row, existing=None):
        row = dict(row, user_id=self.user_id, industry=self.industry)
        validate(row)
        if existing:
            result = self.db.table('work_hub_records').update(row).eq('id', existing['id']).eq('user_id', self.user_id).eq('version', existing['version']).execute()
        else:
            result = self.db.table('work_hub_records').insert(row).execute()
        if not result.data:
            raise ValueError('The record changed in another session. Reload before saving.')
        return result.data[0]
