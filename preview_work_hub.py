"""Local UI harness only. In-memory records do not test Supabase/RLS."""
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
from datetime import datetime, timezone
import streamlit as st
from work_hub import render_work_hub


class FakeDB:
    def __init__(self):
        self.rows=st.session_state.setdefault('preview_rows',[])
    def table(self,name):
        self.name=name; self.filters=[]; self.action=None; return self
    def select(self,*args): return self
    def eq(self,key,value): self.filters.append((key,value)); return self
    def order(self,*args,**kwargs): return self
    def limit(self,*args): return self
    def insert(self,row): self.action='insert'; self.payload=deepcopy(row); return self
    def update(self,row): self.action='update'; self.payload=deepcopy(row); return self
    def execute(self):
        if self.name=='work_hub_events': return SimpleNamespace(data=[])
        matched=[r for r in self.rows if all(r.get(k)==v for k,v in self.filters)]
        if self.action=='insert':
            row=dict(self.payload,id=str(uuid4()),version=1,updated_at=datetime.now(timezone.utc).isoformat())
            self.rows.append(row); return SimpleNamespace(data=[deepcopy(row)])
        if self.action=='update':
            for row in matched:
                row.update(self.payload); row['version']+=1
            return SimpleNamespace(data=deepcopy(matched))
        return SimpleNamespace(data=deepcopy(matched))


st.set_page_config(layout='wide')
render_work_hub(FakeDB(),'preview-user','BPO')
