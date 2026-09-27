import unittest
import pandas as pd
from it_operations import prepare_work, summarize_work, work_template


class ITTests(unittest.TestCase):
    def test_all_workflows_missing_measures(self):
        result=summarize_work(prepare_work(work_template()), '2026-09-06')
        self.assertEqual(result['Open'],5)
        self.assertEqual(result['Overdue open'],5)
        self.assertTrue(pd.isna(result['On-time delivery %']))
        self.assertTrue(pd.isna(result['Mean cycle hours']))

    def test_on_time_and_cycle(self):
        frame=work_template().iloc[:2].copy()
        frame['Status']='Completed'
        frame['Completed_At']=['2026-09-01T11:00:00Z','2026-09-06T09:00:00Z']
        result=summarize_work(prepare_work(frame),'2026-09-07')
        self.assertEqual(result['On-time delivery %'],50)
        self.assertEqual(result['Mean cycle hours'],61)

    def test_invalid_exports(self):
        for col,value in [('Work_Item_ID','same'),('Workflow','other'),('Created_At','bad'),('Status','other'),('Completed_At','2025-01-01')]:
            frame=work_template();frame[col]=value
            with self.assertRaises(ValueError):prepare_work(frame)


if __name__=='__main__':unittest.main()
