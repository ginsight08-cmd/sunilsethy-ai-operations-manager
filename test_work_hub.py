import unittest
from decimal import Decimal
from work_hub_domain import validate, estimate, draft_transition, HubStore


class WorkHubTests(unittest.TestCase):
    def test_each_industry_uses_same_core(self):
        for industry in ['BPO','Manufacturing','CaseManagement','Retail','Logistics','Healthcare']:
            validate(dict(kind='client',industry=industry,title='Example',status='Lead',details={}))

    def test_parent_and_kind_validation(self):
        with self.assertRaises(ValueError):
            validate(dict(kind='task',industry='BPO',title='Check',status='Open',details={}))
        with self.assertRaises(ValueError):
            validate(dict(kind='unknown',industry='BPO',title='Check',status='Open'))

    def test_document_link_validation(self):
        for url in ['javascript:alert(1)','http://example.com','https://user:password@example.com','file:///tmp/file']:
            with self.assertRaises(ValueError):
                validate(dict(kind='document',industry='BPO',title='Reference',status='Reference',parent_id='work',details={'url':url}))
        validate(dict(kind='document',industry='BPO',title='Reference',status='Reference',parent_id='work',details={'url':'https://example.com/file'}))

    def test_billing_estimate(self):
        self.assertEqual(estimate(90,1000),Decimal('1500.00'))
        self.assertEqual(estimate(1,100),Decimal('1.67'))
        for values in [(0,10),(-1,10),(1500,10),(5,-1),(5,'nan'),('inf',5)]:
            with self.assertRaises(ValueError):
                estimate(*values)

    def test_approval_bound_to_content(self):
        self.assertFalse(draft_transition('Draft','Approved'))
        self.assertTrue(draft_transition('Draft','Pending review'))
        self.assertTrue(draft_transition('Pending review','Approved'))
        self.assertFalse(draft_transition('Approved','Approved',True))
        self.assertTrue(draft_transition('Approved','Draft',True))
        self.assertFalse(draft_transition('Approved','Sent'))

    def test_stale_update_rejected(self):
        class Query:
            data=[]
            def table(self,*a): return self
            def update(self,*a): return self
            def eq(self,*a): return self
            def execute(self): return self
        with self.assertRaisesRegex(ValueError,'another session'):
            HubStore(Query(),'user','BPO').save(dict(kind='client',title='Name',status='Lead'),dict(id='x',version=1))


if __name__ == '__main__':
    unittest.main()
