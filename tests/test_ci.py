import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from ci import CIBot, Forum, participant
from course_service import ParticipantDataError


class CITest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.csv = root / 'peserta.csv'
        self.csv.write_text('NIM,Nama,ID,repo\n123,Ani,777,\n124,Budi,888,\n', encoding='utf-8')
        self.user = participant(self.csv, 777)
        self.forum = Forum(root / 'ci.sqlite3')
        self.bot = CIBot('dummy', self.csv, self.forum)
        self.bot.send_message = Mock()

    def update(self, text, user=777, uid=1, kind='private'):
        return {'update_id': uid, 'message': {'text': text,
                'chat': {'id': user, 'type': kind}, 'from': {'id': user}}}

    def test_existing_identity_and_unauthorized_access(self):
        original = self.csv.read_bytes()
        self.bot.handle_update(self.update('/status'))
        self.assertIn('Ani (123)', self.bot.send_message.call_args.args[1])
        self.bot.handle_update(self.update('/topik Rahasia', user=999))
        self.assertIn('belum terhubung', self.bot.send_message.call_args.args[1])
        self.assertNotIn('Rahasia', self.forum.execute(20, self.user, '/daftar'))
        self.assertEqual(original, self.csv.read_bytes())

    def test_shared_conversation_reply_and_synthesis_persist(self):
        self.forum.execute(1, self.user, '/topik Energi kampus')
        self.forum.execute(2, self.user, '/ide 1 Pasang panel surya')
        budi = participant(self.csv, 888)
        self.forum.execute(3, budi, '/balas 1 Periksa biaya dahulu')
        self.forum.execute(4, budi, '/bukti 1 https://example.org/studi')
        self.forum.execute(5, budi, '/sintesis 1 Lakukan studi kelayakan')
        reopened = Forum(self.forum.path)
        result = reopened.execute(6, self.user, '/baca 1')
        self.assertIn('Budi', result)
        self.assertIn('→ #1', result)
        self.assertIn('4 kontribusi, 2 kontributor', result)
        self.assertIn('Lakukan studi kelayakan', reopened.execute(7, self.user, '/ringkas 1'))

    def test_replayed_update_does_not_duplicate(self):
        first = self.forum.execute(1, self.user, '/topik A')
        self.assertEqual(first, self.forum.execute(1, self.user, '/topik A'))
        self.forum.execute(2, self.user, '/ide 1 X')
        self.forum.execute(2, self.user, '/ide 1 X')
        self.assertIn('1 kontribusi', self.forum.execute(3, self.user, '/ringkas 1'))

    def test_invalid_input_and_missing_targets(self):
        for uid, command in enumerate(['/ide 99 X', '/balas 99 X', '/baca 0', '/baca 1 -1', '/daftar ' + '9'*5000], 1):
            result = self.forum.execute(uid, self.user, command)
            self.assertTrue('tidak ditemukan' in result or 'bilangan bulat positif' in result)

    def test_group_does_not_expose_content(self):
        self.bot.handle_update(self.update('/daftar', kind='group'))
        self.bot.send_message.assert_not_called()

    def test_duplicate_identity_fails_closed(self):
        self.csv.write_text('NIM,Nama,ID\n1,A,777\n2,B,777\n')
        with self.assertRaises(ParticipantDataError):
            participant(self.csv, 777)

    def test_long_reply_split_with_emoji(self):
        self.bot._api_call = Mock()
        CIBot.send_message(self.bot, 777, '😀'*5000)
        chunks = [c.args[1]['text'] for c in self.bot._api_call.call_args_list]
        self.assertEqual('😀'*5000, ''.join(chunks))
        self.assertTrue(all(len(c.encode('utf-16-le'))//2 <= 3500 for c in chunks))


if __name__ == '__main__':
    unittest.main()
