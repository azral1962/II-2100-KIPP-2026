import tempfile
import unittest
from pathlib import Path
from uts_manual import COMPONENTS, final_score, save_review, history, latest, portfolio_links

class ManualUTSTest(unittest.TestCase):
    def test_total_and_blank_are_distinct_from_zero(self):
        scores = {k: 75 for k in COMPONENTS}
        scores['paper'] = 80
        self.assertEqual('75.50', final_score(scores))
        scores['paper'] = None
        self.assertIsNone(final_score(scores))
        scores = {k: 0 for k in COMPONENTS}
        self.assertEqual('0.00', final_score(scores))
        for value in ('NaN', 'Infinity', -1, 101):
            scores['paper'] = value
            with self.assertRaises(ValueError): final_score(scores)

    def test_draft_finalize_history_and_stale_write(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'grades.json'
            args = dict(nim='001', name='Dummy', ticket='7',
                        scores={k: None for k in COMPONENTS}, notes={}, assessor='Dosen',
                        expected_revision=0)
            with self.assertRaises(ValueError):save_review(path, **args, final=True)
            save_review(path, **args, final=False)
            with self.assertRaises(ValueError):save_review(path, **args, final=False)
            args.update(scores={k: 80 for k in COMPONENTS}, expected_revision=1)
            save_review(path, **args, final=True)
            self.assertEqual(2, len(history(path)))
            self.assertEqual('80.00', latest(path)['001']['total'])
            args.update(nim='002', expected_revision=0)
            save_review(path, **args, final=True)
            self.assertEqual(2, len(latest(path)))

    def test_links_without_snapshot(self):
        with tempfile.TemporaryDirectory() as root:
            index, links = portfolio_links({'NIM':'001','repo':'https://github.com/student/course'}, None, root)
            self.assertTrue(index.endswith('/portfolio/week-08.html'))
            self.assertEqual(set(COMPONENTS), set(links))
            self.assertIn('hasil_2a_001.html', links['2a'][0][1])
