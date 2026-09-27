"""Server-side Neon bridge for the existing Streamlit data interfaces.

Never cache this client globally: its HTTP cookie jar belongs to one app session.
Database identities come only from an online, verified Better Auth session.
"""
from types import SimpleNamespace as Obj
from contextlib import contextmanager
from datetime import date, datetime
import re
import requests
import certifi
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

TABLES = {'work_hub_records', 'work_hub_events', 'vakil_clients', 'vakil_cases', 'vakil_notification_log'}
RPCS = {'public_trial_offer': (), 'my_app_access': (),
        'owner_console': ('p_action', 'p_payload'),
        'admit_trial_analysis': ('p_user_id', 'p_analysis_key')}


class BackendError(RuntimeError):
    @property
    def message(self):
        return str(self)


def identifier(value):
    if not re.fullmatch(r'[a-z_][a-z0-9_]*', value):
        raise BackendError('Unsupported database field.')
    return sql.Identifier(value)


def adapt(value):
    return Jsonb(value) if isinstance(value, dict) else value


def api_rows(rows):
    # Preserve the existing PostgREST contract for forms and deadline comparisons.
    return [{key: value.isoformat() if isinstance(value, (date, datetime)) else value
             for key, value in row.items()} for row in rows]


class NeonClient:
    def __init__(self, auth_url, database_url, public_url, product):
        self.auth_url = auth_url.rstrip('/')
        self.database_url = database_url
        self.public_url = public_url
        self.product = product
        self.http = requests.Session()
        self.http.headers.update({'Origin': public_url.rstrip('/'), 'Accept': 'application/json'})
        self.auth = NeonAuth(self)

    def request(self, method, endpoint, payload=None):
        try:
            response = self.http.request(method, self.auth_url + endpoint,
                                         json=payload, timeout=25, allow_redirects=False)
            if response.status_code >= 300:
                if response.status_code == 429:
                    raise BackendError('Rate limit reached. Please try again later.')
                if response.status_code in (400, 401, 403):
                    raise BackendError('Sign-in failed. Check your details and verify your email.')
                raise BackendError('Authentication service is unavailable. Please retry.')
            return response.json()
        except (requests.RequestException, ValueError):
            raise BackendError('Authentication service is unavailable. Please retry.') from None

    def identity(self):
        result = self.request('GET', '/get-session?disableCookieCache=true')
        user = (result or {}).get('user')
        if not user or not user.get('id') or user.get('emailVerified') is not True:
            raise BackendError('Please verify your email and sign in again.')
        return user

    @contextmanager
    def connection(self, user=None, privileged=False):
        # The per-project marker catches accidentally swapped database secrets.
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row,
                                  connect_timeout=15, sslmode='verify-full', sslrootcert=certifi.where()) as conn:
                marker = conn.execute('select product from gi_auth.deployment where singleton').fetchone()
                if not marker or marker['product'] != self.product:
                    raise BackendError('Database configuration does not match this product.')
                if not privileged:
                    if user:
                        access=conn.execute('select blocked from public.app_account_access where user_id=%s', (user['id'],)).fetchone()
                        if not access or access['blocked']:
                            raise BackendError('Your account access is unavailable.')
                    conn.execute("select set_config('gi.user_id', %s, true)", (user['id'] if user else '',))
                    conn.execute('set local role authenticated' if user else 'set local role anon')
                yield conn
        except psycopg.Error:
            # Never display SQL, DSNs, authentication cookies, or provider errors.
            raise BackendError('The database request could not be confirmed. Reload before retrying.') from None

    def profile(self, user, initial=None):
        metadata={'full_name':user.get('name',''),'plan':'Free'}
        if initial:
            metadata['company_name']=str(initial.get('company_name',''))[:300]
        with self.connection(privileged=True) as conn:
            row = conn.execute('''insert into gi_auth.users(id,email,created_at,raw_user_meta_data)
                values(%s,%s,%s,%s) on conflict(id) do update set email=excluded.email
                returning *''', (user['id'], user['email'], user['createdAt'],
                                  Jsonb(metadata))).fetchone()
        return Obj(id=row['id'],email=row['email'],created_at=row['created_at'],
                   user_metadata=row['raw_user_meta_data'])

    def table(self, name):
        if name not in TABLES:
            raise BackendError('Unsupported table.')
        return Query(self, name)

    def rpc(self, name, params):
        if name not in RPCS or set(params) != set(RPCS[name]):
            raise BackendError('Unsupported operation.')
        return Rpc(self, name, params)


class NeonAuth:
    def __init__(self, client):
        self.client = client
        self.admin = ProfileAdmin(client)

    def sign_up(self, payload):
        fields=payload.get('options',{}).get('data',{})
        result=self.client.request('POST','/sign-up/email',
            {'name':fields.get('full_name',''), 'email':payload['email'],
             'password':payload['password'], 'callbackURL':self.client.public_url})
        created=result.get('user') or {}
        if all(created.get(key) for key in ('id','email','createdAt')):
            # Preserve signup business details from the provider-confirmed record.
            # This grants no session; verified sign-in is still required below.
            self.client.profile(created,fields)
        # Always require the normal verified sign-in flow; never grant app access
        # based solely on a signup response or submitted email address.
        return Obj(user=Obj(id=(result.get('user') or {}).get('id','')),session=None)

    def sign_in_with_password(self, payload):
        self.client.request('POST','/sign-in/email',
            {'email':payload['email'],'password':payload['password']})
        return self.set_session('', '')

    def verify_email(self, email, code):
        if not email.strip() or not code.strip():
            raise BackendError('Enter your email and verification code.')
        self.client.request('POST','/email-otp/verify-email',{'email':email.strip().lower(),'otp':code.strip()})

    def resend_verification(self, email):
        if not email.strip(): raise BackendError('Enter your email address.')
        self.client.request('POST','/email-otp/send-verification-otp',
                            {'email':email.strip().lower(),'type':'email-verification'})

    def set_session(self, access_token, refresh_token):
        user=self.client.profile(self.client.identity())
        # Compatibility markers only; authentication uses the private cookie jar.
        return Obj(user=user,session=Obj(access_token='neon-session',refresh_token='neon-session'))

    def sign_out(self):
        try:
            self.client.request('POST','/sign-out',{})
        finally:
            self.client.http.cookies.clear()


class ProfileAdmin:
    """Internal server API for existing verified billing paths, never a public RPC."""
    def __init__(self, client): self.client=client

    def current(self, user_id):
        user=self.client.identity()
        if user['id'] != user_id:
            raise BackendError('Account mismatch.')
        return user

    def get_user_by_id(self, user_id):
        return Obj(user=self.client.profile(self.current(user_id)))

    def update_user_by_id(self, user_id, payload):
        self.current(user_id)
        metadata=payload.get('user_metadata')
        if not isinstance(metadata,dict): raise BackendError('Invalid profile update.')
        with self.client.connection(privileged=True) as conn:
            conn.execute('update gi_auth.users set raw_user_meta_data=%s where id=%s',
                         (Jsonb(metadata),user_id))


class Rpc:
    def __init__(self,client,name,params): self.client,self.name,self.params=client,name,params

    def execute(self):
        user=None if self.name=='public_trial_offer' else self.client.identity()
        privileged=self.name=='admit_trial_analysis'
        if privileged and self.params['p_user_id'] != user['id']:
            raise BackendError('Account mismatch.')
        fields=RPCS[self.name]
        query=sql.SQL('select public.{}({}) as data').format(identifier(self.name),
            sql.SQL(',').join(sql.Placeholder() for _ in fields))
        with self.client.connection(user,privileged=privileged) as conn:
            data=conn.execute(query,[adapt(self.params[k]) for k in fields]).fetchone()['data']
        return Obj(data=data)


class Query:
    def __init__(self,client,table):
        self.client,self.name=client,table
        self.action,self.fields,self.payload='select','*',None
        self.filters=[]; self.sort=None; self.maximum=1000

    def select(self,fields='*'): self.fields=fields; return self
    def insert(self,payload): self.action,self.payload='insert',payload; return self
    def update(self,payload): self.action,self.payload='update',payload; return self
    def delete(self): self.action='delete'; return self
    def eq(self,key,value): self.filters.append((key,value)); return self
    def order(self,key,desc=False): self.sort=(key,desc); return self
    def limit(self,value): self.maximum=max(1,min(int(value),1000)); return self

    def execute(self):
        user=self.client.identity()
        table=sql.Identifier('public',self.name)
        params=[]
        if self.action=='select':
            columns=sql.SQL('*') if self.fields=='*' else sql.SQL(',').join(identifier(x.strip()) for x in self.fields.split(','))
            query=sql.SQL('select {} from {}').format(columns,table)
        elif self.action=='delete':
            query=sql.SQL('delete from {}').format(table)
        else:
            if not isinstance(self.payload,dict) or not self.payload: raise BackendError('Invalid record.')
            payload=dict(self.payload)
            if payload.get('user_id',user['id']) != user['id']: raise BackendError('Account mismatch.')
            if self.action=='insert': payload['user_id']=user['id']
            keys=list(payload)
            params=[adapt(payload[k]) for k in keys]
            if self.action=='insert':
                query=sql.SQL('insert into {} ({}) values ({})').format(table,
                    sql.SQL(',').join(identifier(k) for k in keys),sql.SQL(',').join(sql.Placeholder() for k in keys))
            else:
                query=sql.SQL('update {} set {}').format(table,sql.SQL(',').join(
                    sql.SQL('{}=%s').format(identifier(k)) for k in keys))
        if self.action!='insert':
            filters=[*self.filters,('user_id',user['id'])]
            query+=sql.SQL(' where ')+sql.SQL(' and ').join(sql.SQL('{}=%s').format(identifier(k)) for k,v in filters)
            params.extend(v for k,v in filters)
        if self.action=='select':
            if self.sort:
                query+=sql.SQL(' order by {} {}').format(identifier(self.sort[0]),sql.SQL('desc' if self.sort[1] else 'asc'))
            query+=sql.SQL(' limit %s'); params.append(self.maximum)
        else:
            query+=sql.SQL(' returning *')
        with self.client.connection(user) as conn:
            rows=conn.execute(query,params).fetchall()
        return Obj(data=api_rows(rows))
