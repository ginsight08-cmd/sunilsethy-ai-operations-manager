import unittest
from streamlit.testing.v1 import AppTest


class ExcellenceUITests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file('preview_excellence.py').run(timeout=30)

    def test_navigation_and_calculation(self):
        self.assertFalse(self.app.exception)
        self.app.radio[0].set_value('Workforce planning').run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.metric[1].value, '18')
        self.app.radio[0].set_value('Quality & Lean tools').run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.metric[1].value, '8,000')

    def test_gap_opens_prefilled_project(self):
        import pandas as pd
        self.app.session_state['analysis_result'] = {'findings': pd.DataFrame([
            {'Team': 'A', 'Finding': 'Quality 90% below 95%', 'Severity': 'High'}])}
        self.app.run()
        next(b for b in self.app.button if b.label == 'Use this gap in the project form').click().run()
        self.assertFalse(self.app.exception)
        self.app.radio[0].set_value('RCA & CAPA').run()
        problem = next(w for w in self.app.text_area if w.label == 'Measured problem / gap')
        self.assertEqual(problem.value, 'Quality 90% below 95%')

    def test_project_save_and_incomplete_closure_blocked(self):
        self.app.radio[0].set_value('RCA & CAPA').run()
        values = {'Project title': 'Improve FCR', 'Accountable owner': 'QA lead',
                  'Measured problem / gap': 'FCR below target',
                  'Voice of customer → critical-to-quality requirement': 'Resolve first contact'}
        for widget in list(self.app.text_input) + list(self.app.text_area):
            if widget.label in values:
                widget.set_value(values[widget.label])
        self.app.button[0].click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.session_state['ox_projects']), 1)
        self.app.selectbox[0].select(self.app.session_state['ox_projects'][0]['id']).run()
        next(w for w in self.app.selectbox if w.label == 'Action status').set_value('Closed')
        self.app.button[0].click().run()
        self.assertTrue(self.app.error)
        self.assertEqual(self.app.session_state['ox_projects'][0]['status'], 'Open')


if __name__ == '__main__':
    unittest.main()
