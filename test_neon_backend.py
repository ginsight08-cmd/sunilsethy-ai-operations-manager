import unittest
from unittest.mock import Mock, patch
from contextlib import contextmanager
from neon_backend import NeonClient, BackendError, identifier, api_rows
from datetime import date


class NeonTests(unittest.TestCase):
    def setUp(self):
        self.client=NeonClient('https://auth.example/auth','unused','https://app.example/','bpo')

    def test_unverified_or_revoked_session_denied(self):
        for data in [None, {}, {'user':{'id':'u','emailVerified':False}}]:
            self.client.request=Mock(return_value=data)
            with self.assertRaises(BackendError): self.client.identity()

    def test_forces_online_session_validation(self):
        self.client.request=Mock(return_value={'user':{'id':'u','emailVerified':True}})
        self.assertEqual(self.client.identity()['id'],'u')
        self.client.request.assert_called_with('GET','/get-session?disableCookieCache=true')

    def test_cookie_jars_are_not_shared(self):
        other=NeonClient('https://other.example/auth','unused','https://other.example/','vakil')
        self.client.http.cookies.set('session','one')
        self.assertEqual(len(other.http.cookies),0)

    def test_date_values_keep_existing_ui_contract(self):
        self.assertEqual(api_rows([{'due_date':date(2026,9,21)}])[0]['due_date'],'2026-09-21')

    def test_signup_never_grants_access_from_response(self):
        self.client.request=Mock(return_value={'user':{'id':'u','emailVerified':True},'token':'not-trusted'})
        result=self.client.auth.sign_up({'email':'test@example.com','password':'fixture',
            'options':{'data':{'full_name':'Test'}}})
        self.assertIsNone(result.session)

    def test_cross_user_privileged_actions_rejected(self):
        self.client.identity=Mock(return_value={'id':'user-a'})
        with self.assertRaises(BackendError):
            self.client.rpc('admit_trial_analysis',{'p_user_id':'user-b','p_analysis_key':'a'*64}).execute()
        with self.assertRaises(BackendError):
            self.client.auth.admin.update_user_by_id('user-b',{'user_metadata':{'plan':'Professional'}})

    def test_query_uses_verified_identity_and_bound_values(self):
        self.client.identity=Mock(return_value={'id':'user-a'})
        conn=Mock(); conn.execute.return_value.fetchall.return_value=[]
        @contextmanager
        def connection(user):
            self.assertEqual(user['id'],'user-a')
            yield conn
        self.client.connection=connection
        self.client.table('work_hub_records').select('*').eq('title',"x'; delete from users;--").execute()
        query,params=conn.execute.call_args.args
        self.assertIn('"user_id"=%s',query.as_string())
        self.assertNotIn('delete from',query.as_string())
        self.assertEqual(params[-2],'user-a')

    def test_table_rpc_and_field_allowlists(self):
        with self.assertRaises(BackendError): self.client.table('app_owners')
        with self.assertRaises(BackendError): self.client.rpc('unsafe',{})
        with self.assertRaises(BackendError): identifier('id; drop table users')

    def test_provider_error_is_redacted(self):
        response=Mock(status_code=500,text='secret database details')
        self.client.http.request=Mock(return_value=response)
        with self.assertRaisesRegex(BackendError,'Authentication service is unavailable'):
            self.client.request('GET','/get-session')

    def test_logout_clears_cookies_even_on_provider_failure(self):
        self.client.http.cookies.set('session','fixture')
        self.client.request=Mock(side_effect=BackendError('failed'))
        with self.assertRaises(BackendError): self.client.auth.sign_out()
        self.assertEqual(len(self.client.http.cookies),0)


if __name__=='__main__': unittest.main()
