import unittest
import pandas as pd
from annotation_operations import prepare_tasks, summarize, template, report_pdf


class AnnotationTests(unittest.TestCase):
    def test_all_modalities_and_metrics(self):
        frame=prepare_tasks(template())
        result=summarize(frame)
        self.assertEqual(result['Completed'],4)
        self.assertEqual(result['Acceptance %'],100)
        self.assertEqual(result['Turnaround hours'],2)
        self.assertTrue(report_pdf(result).startswith(b'%PDF'))

    def test_missing_measurements_are_not_zero(self):
        frame=template().drop(columns=['Completed_At','Rework_Count','Annotation_Minutes','Review_Status'])
        result=summarize(prepare_tasks(frame))
        self.assertTrue(pd.isna(result['Acceptance %']))
        self.assertTrue(pd.isna(result['Rework %']))
        self.assertTrue(pd.isna(result['Turnaround hours']))
        self.assertEqual(result['Review backlog'],4)

    def test_reject_duplicate_and_invalid_tasks(self):
        for column,value in [('Task_ID','same'),('Modality','unknown'),('Created_At','invalid'),('Completed_At','2025-01-01'),('Rework_Count',-1),('Annotation_Minutes',float('inf'))]:
            with self.subTest(column=column):
                frame=template();frame[column]=value
                with self.assertRaises(ValueError):prepare_tasks(frame)

    def test_acceptance_denominator_is_reviewed_tasks(self):
        frame=template();frame['Review_Status']=['Accepted','Rejected','Not reviewed','Not reviewed']
        result=summarize(prepare_tasks(frame))
        self.assertEqual(result['Acceptance %'],50)
        self.assertEqual(result['Review backlog'],2)


if __name__=='__main__':unittest.main()
