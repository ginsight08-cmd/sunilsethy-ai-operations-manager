import unittest
from datetime import date
from streamlit.testing.v1 import AppTest

class DateTests(unittest.TestCase):
 def test_range_validation_and_reset(self):
  app=AppTest.from_string("import pandas as pd\nfrom date_filters import date_range\ndate_range(pd.Timestamp('2020-01-01'),pd.Timestamp('2020-12-31'),'test')",default_timeout=15).run()
  self.assertFalse(app.exception)
  app.date_input[0].set_value(date(2020,10,1)).run()
  app.date_input[1].set_value(date(2020,2,1)).run()
  self.assertTrue(app.error)
  app.button[0].click().run()
  self.assertFalse(app.error)
  self.assertEqual(app.date_input[0].value,date(2020,1,1))
  self.assertEqual(app.date_input[1].value,date(2020,12,31))
 def test_user_can_edit_beyond_upload_dates(self):
  app=AppTest.from_string("import pandas as pd\nfrom date_filters import date_range\ndate_range(pd.Timestamp('2026-07-27'),pd.Timestamp('2026-07-27'),'test')",default_timeout=15).run()
  app.date_input[1].set_value(date(2027,6,2)).run()
  app.date_input[0].set_value(date(2026,9,27)).run()
  self.assertFalse(app.exception)
  self.assertFalse(app.error)
  self.assertEqual(app.date_input[0].value,date(2026,9,27))
  self.assertEqual(app.date_input[1].value,date(2027,6,2))
 def test_single_day(self):
  app=AppTest.from_string("import pandas as pd\nfrom date_filters import date_range\ndate_range(pd.Timestamp('2026-07-27'),pd.Timestamp('2026-07-27'),'test')",default_timeout=15).run()
  self.assertFalse(app.exception)
  self.assertTrue(any('one date' in c.value for c in app.caption))
