import unittest
import time
from unittest.mock import MagicMock, patch
import google_sheets_source as sheets
from google_sheets_source import spreadsheet_id, rows_to_upload, SheetsError


class SheetsTests(unittest.TestCase):
    def test_only_google_sheet_ids(self):
        ident='abcdefghijABCDEFGHIJ0123456789'
        self.assertEqual(spreadsheet_id('https://docs.google.com/spreadsheets/d/'+ident+'/edit#gid=0'),ident)
        for value in ['http://localhost/a','https://docs.google.com.evil.test/spreadsheets/d/'+ident,'https://user@docs.google.com/spreadsheets/d/'+ident,'https://docs.google.com/spreadsheets/d/../secrets']:
            with self.assertRaises(SheetsError):spreadsheet_id(value)

    def test_rows_and_upload_contract(self):
        result=rows_to_upload([['Date','Tasks'],['2026-01-01',2],['2026-01-02']],1000)
        self.assertEqual(result.size,len(result.getvalue()))
        self.assertTrue(result.name.endswith('.csv'))
        self.assertIn(b'2026-01-01,2',result.getvalue())

    def test_reject_malformed_or_large_data(self):
        for rows in [[['A','A'],[1,2]],[['A',''],[1,2]],[['A'],[1,2]],[['A']]]:
            with self.assertRaises(SheetsError):rows_to_upload(rows,1000)
        with self.assertRaises(SheetsError):rows_to_upload([['A'],['x'*100]],10)

    def test_expired_token_is_removed(self):
        ui=MagicMock()
        ui.session_state={'_google_sheets':{'owner':('a','bpo'),'access_token':'test-token','expires_at':0}}
        with patch.object(sheets,'st',ui):
            self.assertIsNone(sheets.connection({},('a','bpo')))
        self.assertNotIn('_google_sheets',ui.session_state)

    def test_user_change_does_not_reuse_token(self):
        ui=MagicMock()
        ui.session_state={'_google_sheets':{'owner':('a','bpo'),'access_token':'test-token','expires_at':time.time()+300}}
        with patch.object(sheets,'st',ui), patch.object(sheets,'_connect',return_value=None):
            self.assertIsNone(sheets.connection({'client_id':'test','origin':'https://example.com'},('b','bpo')))
        self.assertNotIn('access_token',ui.session_state['_google_sheets'])
        self.assertEqual(ui.session_state['_google_sheets']['owner'],('b','bpo'))

    def test_invalid_callback_never_exchanges_code(self):
        ui=MagicMock()
        ui.session_state={'_google_sheets':{'owner':('a','bpo'),'nonce':'expected','deadline':time.time()+300}}
        with patch.object(sheets,'st',ui), patch.object(sheets,'_connect',return_value={'nonce':'wrong','code':'test'}), patch.object(sheets.requests,'post') as post:
            self.assertIsNone(sheets.connection({'client_id':'test','origin':'https://example.com'},('a','bpo')))
            post.assert_not_called()

    def test_api_errors_do_not_expose_provider_response(self):
        for status in [401,403,404,429,500]:
            response=MagicMock(status_code=status)
            response.__enter__.return_value=response
            response.text='private-provider-details'
            with patch.object(sheets.requests,'get',return_value=response):
                with self.assertRaises(SheetsError) as error:
                    sheets.read_json('https://sheets.googleapis.com/v4/spreadsheets/test','test-token')
                self.assertNotIn('private-provider-details',str(error.exception))


if __name__=='__main__':unittest.main()

