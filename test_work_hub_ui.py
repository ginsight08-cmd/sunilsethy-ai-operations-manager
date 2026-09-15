import unittest
from streamlit.testing.v1 import AppTest


class HubUITests(unittest.TestCase):
    def test_client_work_draft_review_pipeline(self):
        app=AppTest.from_file('preview_work_hub.py').run(timeout=30)
        section=lambda name: app.selectbox(key='hub_section_BPO').set_value(name).run()
        section('Clients & intake')
        next(w for w in app.text_input if w.label=='Name').set_value('Example client')
        next(b for b in app.button if b.label=='Save record').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state['preview_rows']),1)
        # Saving again edits the created record rather than creating a duplicate.
        next(b for b in app.button if b.label=='Save record').click().run()
        self.assertEqual(len(app.session_state['preview_rows']),1)
        section('Work records')
        next(w for w in app.text_input if w.label=='Title').set_value('Service review')
        next(b for b in app.button if b.label=='Save record').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state['preview_rows']),2)
        section('Drafts & approvals')
        next(w for w in app.text_input if w.label=='Title').set_value('Client update')
        app.text_area[0].set_value('Draft update for review.')
        next(b for b in app.button if b.label=='Save record').click().run()
        self.assertFalse(app.exception)
        app.checkbox[0].check()
        next(b for b in app.button if b.label=='Record decision').click().run()
        self.assertEqual(app.session_state['preview_rows'][-1]['status'],'Pending review')
        app.checkbox[0].check()
        next(b for b in app.button if b.label=='Record decision').click().run()
        self.assertEqual(app.session_state['preview_rows'][-1]['status'],'Approved')
        self.assertFalse(app.exception)


if __name__=='__main__': unittest.main()
