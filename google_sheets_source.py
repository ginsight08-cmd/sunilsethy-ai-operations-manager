"""Session-scoped, read-only Google Sheets source for authenticated users."""
import hashlib
import io
import json
import re
import secrets
import time
from pathlib import Path
from urllib.parse import quote, urlparse
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

SCOPE = 'https://www.googleapis.com/auth/spreadsheets.readonly'
_connect = components.declare_component('gi_google_sheets', path=str(Path(__file__).with_name('google_sheets_component')))


class SheetsError(ValueError):
    pass


class SheetUpload(io.BytesIO):
    def __init__(self, content):
        super().__init__(content)
        self.name = 'google-sheet-' + hashlib.sha256(content).hexdigest()[:12] + '.csv'
        self.size = len(content)


def spreadsheet_id(value):
    value = value.strip()
    if re.fullmatch(r'[A-Za-z0-9_-]{20,200}', value): return value
    parsed = urlparse(value)
    if parsed.scheme != 'https' or parsed.netloc != 'docs.google.com':
        raise SheetsError('Use a Google Sheets link starting with https://docs.google.com/spreadsheets/d/.')
    match = re.match(r'^/spreadsheets/d/([A-Za-z0-9_-]{20,200})(?:/|$)',parsed.path)
    if not match: raise SheetsError('This is not a supported spreadsheet link.')
    return match.group(1)


def read_json(url, token, params=None, limit=6*1024*1024):
    # URLs are constructed only from fixed Google API endpoints and validated IDs.
    try:
        with requests.get(url,headers={'Authorization':'Bearer '+token},params=params,
                          timeout=(10,30),allow_redirects=False,stream=True) as response:
            if response.status_code in (401,403): raise SheetsError('Access expired or permission was denied. Reconnect Google and check spreadsheet access.')
            if response.status_code == 404: raise SheetsError('Spreadsheet not found or not shared with the connected Google account.')
            if response.status_code == 429: raise SheetsError('Google is temporarily rate-limiting requests. Try again shortly.')
            if response.status_code != 200: raise SheetsError('Google Sheets could not be reached. Try again shortly.')
            content=bytearray()
            for chunk in response.iter_content(65536):
                content.extend(chunk)
                if len(content)>limit: raise SheetsError('This sheet exceeds the import size limit. Use a smaller reporting sheet.')
            return json.loads(content)
    except SheetsError: raise
    except (requests.RequestException,ValueError): raise SheetsError('Could not read a valid response from Google Sheets.') from None


def rows_to_upload(rows, max_bytes):
    if len(rows)<2: raise SheetsError('The sheet needs a header row and at least one data row.')
    headers=[str(value).strip() for value in rows[0]]
    if not headers or any(not value for value in headers) or len(set(headers))!=len(headers):
        raise SheetsError('Use a non-empty, unique column name in every header cell.')
    if any(len(row)>len(headers) for row in rows[1:]): raise SheetsError('Some data columns do not have a header.')
    data=pd.DataFrame([row+[None]*(len(headers)-len(row)) for row in rows[1:]],columns=headers)
    content=data.to_csv(index=False).encode('utf-8')
    if len(content)>max_bytes: raise SheetsError('Imported data exceeds your plan upload limit.')
    return SheetUpload(content)


def connection(config, owner):
    state=st.session_state.get('_google_sheets')
    if state and state.get('owner')!=owner:
        st.session_state.pop('_google_sheets',None)
        state=None
    if state and state.get('access_token'):
        if state.get('expires_at',0)<=time.time():
            st.session_state.pop('_google_sheets',None)
            st.warning('Google access expired. Connect again to refresh your sheet.')
            return None
        st.success('Google Sheets connected for this signed-in session.')
        if st.button('Disconnect Google Sheets',key='google_sheets_disconnect'):
            token=state['access_token']
            for key in list(st.session_state):
                if key.startswith('_google_'):st.session_state.pop(key,None)
            try:
                response=requests.post('https://oauth2.googleapis.com/revoke',data={'token':token},timeout=15)
                if response.status_code!=200:st.warning('Local connection removed. You can also remove access in your Google account permissions.')
            except requests.RequestException:st.warning('Local connection removed. Google could not confirm revocation; review your Google account permissions.')
            st.rerun()
        return state['access_token']
    if not state or state.get('deadline',0)<time.time():
        state={'owner':owner,'nonce':secrets.token_urlsafe(32),'deadline':time.time()+600}
        st.session_state['_google_sheets']=state
    result=_connect(client_id=config['client_id'],nonce=state['nonce'],origin=config['origin'],key='google_auth_'+state['nonce'],default=None)
    if not result:return None
    if not isinstance(result,dict) or not secrets.compare_digest(str(result.get('nonce','')),state['nonce']) or result.get('origin')!=config['origin']:
        st.error('Google connection validation failed. Please reconnect.');return None
    code=result.get('code')
    if not isinstance(code,str) or not code or len(code)>4096:
        st.error('Google authorization was not completed. Please try again.');return None
    # Consume the nonce before exchanging a single-use authorization code.
    st.session_state.pop('_google_sheets',None)
    try:
        response=requests.post('https://oauth2.googleapis.com/token',data={
            'client_id':config['client_id'],'client_secret':config['client_secret'],
            'code':code,'grant_type':'authorization_code','redirect_uri':config['origin']},timeout=20)
        payload=response.json() if response.status_code==200 else {}
        if not payload.get('access_token') or SCOPE not in payload.get('scope','').split():
            raise SheetsError('Google did not grant read-only spreadsheet access. Please try again.')
        st.session_state['_google_sheets']={'owner':owner,'access_token':payload['access_token'],
            'expires_at':time.time()+min(int(payload.get('expires_in',3600)),3600)-60}
        # Refresh tokens are deliberately not persisted; reconnect after logout/restart.
        st.rerun()
    except (requests.RequestException,ValueError):
        st.error('Google connection could not be completed. Please try again.')
    return None


def source_upload(label, type=None, key='operations_upload', max_mb=None, **kwargs):
    types=type or ['csv','xlsx']
    max_mb=max_mb if max_mb is not None else {'Free':5,'Professional':25,'Business':100}.get(st.session_state.get('user_plan','Free'),5)
    choice=st.radio('Data source',['Upload file','Google Sheets'],horizontal=True,key=key+'_source')
    if choice=='Upload file':return st.file_uploader(label,type=types,key=key,**kwargs)
    if not st.session_state.get('authenticated') or not st.session_state.get('user_id'):
        st.error('Sign in before connecting a spreadsheet.');return None
    config={k:st.secrets.get('GOOGLE_SHEETS_'+k.upper(),'') for k in ['client_id','client_secret','origin']}
    if not all(config.values()):
        st.info('Google Sheets connection is being configured by the app owner. File uploads remain available.');return None
    origin=urlparse(config['origin'])
    if origin.scheme!='https' or origin.path not in ('','/') or origin.username or origin.query or origin.fragment:
        st.error('Google Sheets setup needs attention from the app owner.');return None
    config['origin']=f'{origin.scheme}://{origin.netloc}'
    st.caption('Google asks for read-only access to your spreadsheets. This app imports only the spreadsheet and worksheet you choose. Connection lasts for this signed-in session; reconnect after expiry or sign-out.')
    owner=(st.session_state.user_id,st.secrets.get('PRODUCT_ID','legacy'))
    token=connection(config,owner)
    if not token:return None
    url=st.text_input('Google Sheets link',key=key+'_sheet_url',placeholder='https://docs.google.com/spreadsheets/d/…')
    if not url:return None
    try: identity=spreadsheet_id(url)
    except SheetsError as error:st.error(str(error));return None
    meta_key='_google_metadata_'+key
    metadata=st.session_state.get(meta_key)
    if st.button('Load worksheets',key=key+'_load'):
        st.session_state.pop('_google_data_'+key,None)
        try:
            document=read_json('https://sheets.googleapis.com/v4/spreadsheets/'+identity,token,
                params={'fields':'sheets.properties(sheetId,title,gridProperties)'},limit=1024*1024)
            metadata={'id':identity,'owner':owner,'sheets':[s['properties'] for s in document.get('sheets',[])]}
            st.session_state[meta_key]=metadata
        except SheetsError as error:st.error(str(error));return None
    if not metadata or metadata['id']!=identity or metadata['owner']!=owner:return None
    sheets=metadata['sheets']
    if not sheets:st.info('No worksheets are available.');return None
    title=st.selectbox('Worksheet',[s['title'] for s in sheets],key=key+'_sheet_title')
    st.caption('First row must contain column names. Format date columns as YYYY-MM-DD. Import supports up to 10,000 rows and 100 columns; your plan size and analysis limits still apply.')
    data_key='_google_data_'+key
    if st.button('Import / refresh data',key=key+'_refresh',type='primary'):
        st.session_state.pop(data_key,None)
        sheet=next(s for s in sheets if s['title']==title)
        grid=sheet.get('gridProperties',{})
        if grid.get('rowCount',0)>10000 or grid.get('columnCount',0)>100:
            st.error('Use a reporting worksheet with at most 10,000 grid rows and 100 columns.');return None
        sheet_range="'"+title.replace("'","''")+"'"
        try:
            values=read_json('https://sheets.googleapis.com/v4/spreadsheets/'+identity+'/values/'+quote(sheet_range,safe=''),token,
                params={'valueRenderOption':'UNFORMATTED_VALUE','dateTimeRenderOption':'FORMATTED_STRING'},limit=int(max_mb*1024*1024))
            upload=rows_to_upload(values.get('values',[]),int(max_mb*1024*1024))
            st.session_state[data_key]={'owner':owner,'id':identity,'title':title,'bytes':upload.getvalue(),'time':time.strftime('%H:%M UTC',time.gmtime())}
        except SheetsError as error:st.error(str(error));return None
    imported=st.session_state.get(data_key)
    if imported and imported['owner']==owner and imported['id']==identity and imported['title']==title:
        st.caption('Last refreshed '+imported['time']+'. Changes in Google Sheets appear after you refresh.')
        return SheetUpload(imported['bytes'])
    return None
