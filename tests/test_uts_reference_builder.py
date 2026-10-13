import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from prepare_uts_references import build
from uts import DIMENSIONS, SESSIONS, load_reference

class ReferenceBuilderTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packages = self.root / 'packages'
        self.packages.mkdir()
        self.output = self.root / 'references'
        self.rubric = {'rubric_version': 'fixture-v1-draft', 'basis': 'Synthetic fixture',
                       'descriptors': {key: {str(n): f'Test level {n}' for n in range(1, 5)} for key in DIMENSIONS}}
        for session in SESSIONS:
            self.write_package(session)
    def write_package(self, session, nim='001', target=None):
        with zipfile.ZipFile(self.packages / f'kasus_{session}_001.zip', 'w') as archive:
            archive.writestr('PENUGASAN.md', f'- NIM: {nim}\n- Sesi: {session}; urutan\n- Versi bank: 2.0; versi paket individual: 2.0\n- Komunikan: {target or session}\n')
            archive.writestr('prompt_umum.md', 'Fixture, not a production rubric.')
    def test_draft_has_provenance_and_blocks_scoring(self):
        build(self.packages, self.rubric, self.output)
        self.assertFalse(load_reference(self.output, '001')['available'])
        data = json.loads((self.output / '001.json').read_text(encoding='utf-8'))
        self.assertEqual('001', data['nim'])
        self.assertEqual(set(SESSIONS), set(data['assignments']))
        self.assertEqual(64, len(data['provenance']['1']['zip_sha256']))
    def test_explicit_approval_records_authority(self):
        build(self.packages, self.rubric, self.output, 'Dosen Fixture')
        data = load_reference(self.output, '001')
        self.assertTrue(data['available'])
        self.assertEqual('fixture-v1', data['rubric_version'])
        self.assertTrue(data['approved_at'])
    def test_no_overwrite(self):
        build(self.packages, self.rubric, self.output)
        original = (self.output / '001.json').read_bytes()
        with self.assertRaises(ValueError):
            build(self.packages, self.rubric, self.output, 'Dosen')
        self.assertEqual(original, (self.output / '001.json').read_bytes())
    def test_missing_package_or_wrong_nim_fail_before_export(self):
        (self.packages / 'kasus_3b_001.zip').unlink()
        with self.assertRaises(ValueError):
            build(self.packages, self.rubric, self.output)
        self.assertFalse(self.output.exists())
        self.write_package('3b', nim='002')
        with self.assertRaises(ValueError):
            build(self.packages, self.rubric, self.output)
    def test_same_targets_rejected(self):
        self.write_package('2a', target='Same')
        self.write_package('2b', target='Same')
        with self.assertRaises(ValueError):
            build(self.packages, self.rubric, self.output)
    def test_approved_without_lecturer_rejected(self):
        build(self.packages, self.rubric, self.output, 'Dosen')
        path = self.output / '001.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        data['approved_by'] = ''
        path.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(ValueError):
            load_reference(self.output, '001')
