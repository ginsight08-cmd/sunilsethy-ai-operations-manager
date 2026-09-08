import unittest
from datetime import date
import pandas as pd
from excellence_engine import capacity_plan, quality_rates, pareto, validate_project


class ExcellenceTests(unittest.TestCase):
    def test_capacity_and_round_up(self):
        p = capacity_plan(1000, 300, 8, 85, 30, 15)
        self.assertEqual(p['required_staff'], 18)
        self.assertEqual(p['staff_gap'], 3)
        self.assertEqual(capacity_plan(0, 300, 8, 85, 30, 15)['required_staff'], 0)

    def test_invalid_capacity(self):
        for values in [(1, 0, 8, 85, 30, 1), (1, 300, 8, 0, 30, 1), (1, 300, 8, 85, 100, 1), (float('nan'), 1, 1, 1, 1, 1)]:
            with self.assertRaises(ValueError):
                capacity_plan(*values)

    def test_quality_denominators(self):
        self.assertEqual(quality_rates(1000, 30, 40, 5), {'yield': 97.0, 'dpmo': 8000.0})
        for values in [(0, 0, 0, 1), (10, 11, 11, 2), (10, 2, 1, 2), (10, 2, 30, 2)]:
            with self.assertRaises(ValueError):
                quality_rates(*values)

    def test_pareto_missing_invalid_and_zero(self):
        table, rejected = pareto(pd.DataFrame({'Error_Category': ['A', 'B', 'A', None, 'C'], 'Error_Count': [3, 2, 1, 1, -1]}))
        self.assertEqual(table.iloc[0].Errors, 4)
        self.assertEqual(table.iloc[-1]['Cumulative_%'], 100)
        self.assertEqual(rejected, 1)
        self.assertTrue(pareto(pd.DataFrame())[0].empty)

    def test_closure_gate(self):
        p = dict(title='Reduce repeat calls', owner='Quality lead', problem='Repeat calls 12%', customer_need='Resolve first time', due_date=date.today().isoformat(), status='Open', stage='Define', severity=5, occurrence=4, detection=3)
        self.assertEqual(validate_project(p), [])
        p['status'] = 'Closed'
        self.assertTrue(validate_project(p))
        for k in ['root_cause', 'cause_evidence', 'corrective_action', 'preventive_action', 'effectiveness_evidence', 'reviewer', 'control_plan', 'metric', 'baseline', 'target', 'actual']:
            p[k] = 'Recorded evidence'
        p['effectiveness_confirmed'] = True
        p['stage'] = 'Control'
        self.assertEqual(validate_project(p), [])


if __name__ == '__main__':
    unittest.main()
