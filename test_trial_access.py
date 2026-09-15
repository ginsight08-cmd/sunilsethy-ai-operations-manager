import unittest
from types import SimpleNamespace
from trial_access import analysis_key, admit_analysis

class TrialTests(unittest.TestCase):
    def test_reruns_have_same_identity(self):
        self.assertEqual(analysis_key(b'data', 'BPO', {'a': 1, 'b': 2}), analysis_key(b'data', 'BPO', {'b': 2, 'a': 1}))
    def test_new_inputs_consume_distinct_slot(self):
        base = analysis_key(b'data', 'BPO', {'a': 1})
        for key in [analysis_key(b'new', 'BPO', {'a': 1}), analysis_key(b'data', 'Manufacturing', {'a': 1}), analysis_key(b'data', 'BPO', {'a': 2})]:
            self.assertNotEqual(base, key)
    def test_rpc_contract_and_failure(self):
        class DB:
            def rpc(self, name, args):
                self.name, self.args = name, args
                return self
            def execute(self):
                return SimpleNamespace(data=self.result)
        db = DB()
        db.result = {'allowed': False, 'reason': 'limit'}
        self.assertFalse(admit_analysis(db, 'account', b'data', 'BPO')['allowed'])
        self.assertEqual(db.args['p_user_id'], 'account')
        db.result = None
        with self.assertRaises(RuntimeError):
            admit_analysis(db, 'account', b'data', 'BPO')

if __name__ == '__main__':
    unittest.main()
