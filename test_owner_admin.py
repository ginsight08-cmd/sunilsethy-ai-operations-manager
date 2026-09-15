import unittest
from streamlit.testing.v1 import AppTest

SOURCE = '''
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
'''

class OwnerUITests(unittest.TestCase):
    def test_owner_cannot_submit_self_access_change(self):
        app=AppTest.from_file('preview_owner_admin.py')
        app.session_state['user_id']='example'
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(next(w for w in app.button if w.label=='Save access change').disabled)
        self.assertTrue(any('your owner account' in w.value for w in app.info))

    def test_defaults_submission(self):
        app=AppTest.from_file('preview_owner_admin.py').run()
        self.assertFalse(app.exception)
        next(w for w in app.number_input if w.label=='Trial days').set_value(7)
        next(w for w in app.button if w.label=='Save trial defaults').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['last_request']['p_payload']['trial_days'],7)

    def test_access_change_requires_reason(self):
        app=AppTest.from_file('preview_owner_admin.py').run()
        next(w for w in app.button if w.label=='Save access change').click().run()
        self.assertTrue(app.error)
        self.assertNotIn('last_request', app.session_state)

if __name__=='__main__': unittest.main()
