import os
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest=None

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipIf(AppTest is None,'Streamlit dashboard dependencies not installed')
class DashboardTest(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'CI_DASHBOARD_MODE':'demo'})
        self.env.start(); self.addCleanup(self.env.stop)

    def test_all_instructor_pages_render_from_real_synthetic_database(self):
        at=AppTest.from_file(str(ROOT/'ci_dashboard.py'),default_timeout=60).run()
        self.assertEqual([],list(at.exception))
        self.assertTrue(any('40/40'==m.value for m in at.metric))
        for name in ['intelligence','conversation','assessment','charter','cockpit','settings','simulation','overview']:
            at.switch_page(f'ci_app_pages/{name}.py').run(timeout=30)
            self.assertEqual([],list(at.exception)),name
        at.switch_page('ci_app_pages/charter.py').run()
        self.assertTrue(at.get('download_button'))

    def test_student_cannot_select_another_person_or_staff_pages(self):
        at=AppTest.from_file(str(ROOT/'ci_dashboard.py'),default_timeout=60).run()
        at.selectbox(key='ci_demo_role').set_value('Mahasiswa').run()
        at.switch_page('ci_app_pages/assessment.py').run()
        self.assertEqual([],list(at.exception))
        self.assertFalse(any(s.label=='Bukti peserta (akses dosen)' for s in at.selectbox))
        with self.assertRaises(ValueError): at.switch_page('ci_app_pages/cockpit.py')
        with self.assertRaises(ValueError): at.switch_page('ci_app_pages/settings.py')

    def test_live_without_oidc_does_not_render_class_data(self):
        with patch.dict(os.environ,{'CI_DASHBOARD_MODE':'live'}):
            at=AppTest.from_file(str(ROOT/'ci_dashboard.py'),default_timeout=30).run()
        self.assertEqual([],list(at.exception))
        self.assertFalse(at.metric)
        self.assertTrue(any('OIDC' in item.value or 'Masuk' in item.value for item in at.info))

    def test_verified_subject_mapping_ignores_untrusted_email(self):
        from ci_dashboard_support import resolve_identity
        with self.assertRaises(PermissionError): resolve_identity({'email':'dosen@example.org'}, {'dosen@example.org':99})
        self.assertEqual(99,resolve_identity({'iss':'issuer','sub':'subject'},{'issuer|subject':99}))
        with self.assertRaises(PermissionError): resolve_identity({'iss':'evil','sub':'subject'},{'issuer|subject':99})
