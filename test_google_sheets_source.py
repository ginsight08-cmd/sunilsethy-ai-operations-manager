import unittest
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


if __name__=='__main__':unittest.main()
