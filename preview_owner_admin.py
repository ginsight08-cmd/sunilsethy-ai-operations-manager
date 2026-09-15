
import streamlit as st
from types import SimpleNamespace
from owner_admin import render_owner_admin
class DB:
    def rpc(self,name,args):
        st.session_state['last_request']=args
        return self
    def execute(self): return SimpleNamespace(data={})
snapshot={'settings':{'trial_days':3,'analysis_limit':5},'total_users':1,'audit':[],
'users':[{'id':'example','email':'example@example.com','blocked':False}]}
render_owner_admin(DB(),snapshot)
