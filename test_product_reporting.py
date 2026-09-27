import unittest
import pandas as pd
from bpo_trends import prepare, aggregate
from product_deployment import validate_deployment, PRODUCTS


class ProductTests(unittest.TestCase):
    def config(self, product='bpo'):
        return dict(PRODUCT_ID=product, PRODUCT_PROJECTS=dict(bpo='aaa',procurement='bbb',vakil='ccc'),
                    NEON_AUTH_URL='https://ep-test.neonauth.c-4.ap-southeast-1.aws.neon.tech/neondb/auth',
                    NEON_DATABASE_URL='postgresql://test:test@ep-test-pooler.ap-southeast-1.aws.neon.tech/neondb',
                    APP_PUBLIC_URL='https://example.streamlit.app/')

    def test_each_product(self):
        for product in PRODUCTS:
            self.assertEqual(validate_deployment(product,self.config(product)),PRODUCTS[product])

    def test_wrong_product_and_database_fail_closed(self):
        for changes in [dict(PRODUCT_ID='vakil'),dict(NEON_DATABASE_URL='postgresql://test:test@ep-other.neon.tech/neondb'),
                        dict(PRODUCT_PROJECTS=dict(bpo='aaa',procurement='aaa',vakil='ccc')),
                        dict(PRODUCT_PROJECTS=''),
                        dict(APP_PUBLIC_URL='http://localhost:3000')]:
            config=self.config(); config.update(changes)
            with self.assertRaises(ValueError): validate_deployment('bpo',config)


class ReportingTests(unittest.TestCase):
    def test_weighted_production_and_missing_dates(self):
        frame,invalid=prepare(pd.DataFrame(dict(Date=['2026-01-01','2026-01-01','bad','2026-01-03'],
                                               Production=[10,180,500,20],Target=[10,90,100,0])))
        self.assertEqual(invalid,1)
        result=aggregate(frame,'D')
        self.assertEqual(len(result),2)
        self.assertEqual(result.iloc[0].Productivity,190)
        self.assertTrue(pd.isna(result.iloc[1].Productivity))

    def test_no_history_invented(self):
        frame,invalid=prepare(pd.DataFrame({'Production':[1,2]}))
        self.assertTrue(frame.empty)

    def test_monthly_across_years(self):
        frame,_=prepare(pd.DataFrame(dict(Date=['2025-12-01','2026-01-01'],Quality_=[94,97])))
        self.assertEqual(len(aggregate(frame,'MS')),2)

    def test_trend_ui_and_empty_filters(self):
        from streamlit.testing.v1 import AppTest
        from pathlib import Path
        app=AppTest.from_file(str(Path(__file__).with_name('preview_bpo_trends.py'))).run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.metric),4)
        for period in ['Weekly','Monthly']:
            app.selectbox[0].set_value(period).run()
            self.assertEqual(len(app.exception),0)
        app.multiselect[0].set_value([]).run()
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any('No records match' in item.value for item in app.info))


if __name__=='__main__': unittest.main()
