import unittest
import ast
from pathlib import Path
from streamlit.testing.v1 import AppTest

class OnboardingTests(unittest.TestCase):
    def test_choose_industry_before_workspace(self):
        app=AppTest.from_file('preview_industry_onboarding.py').run()
        self.assertEqual(app.title[0].value,'Choose your industry')
        app.button(key='choose_industry_BPO').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['industry'],'BPO')
        self.assertEqual(app.session_state['workspace_view'],'Industry tools')
        self.assertTrue(app.session_state['industry_selected_this_login'])

    def test_coming_soon_industry_opens_available_hub(self):
        app=AppTest.from_file('preview_industry_onboarding.py').run()
        app.button(key='choose_industry_Retail').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['workspace_view'],'Shared work hub')

    def test_admin_navigation_stays_inside_owner_check(self):
        tree=ast.parse(Path('app.py').read_text(encoding='utf-8'))
        owners=[n for n in tree.body if isinstance(n,ast.If) and ast.unparse(n.test)=='_access[\'is_owner\']']
        self.assertEqual(len(owners),1)
        self.assertIn('Owner dashboard',ast.unparse(owners[0]))
        login=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='set_authenticated_user')
        self.assertIn('industry_selected_this_login = False',ast.unparse(login))

if __name__=='__main__': unittest.main()
