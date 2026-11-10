import csv
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ci import CIBot, Forum
from ci_observer import Observer, LocalAnalyzer
from ci_simulator import simulate


class ObserverTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.roster = self.root / 'peserta.csv'
        self.roster.write_text('NIM,Nama,ID,repo\n1,Ani,11,\n2,Budi,22,\n3,Cici,33,\n')
        self.path = self.root / 'ci.sqlite3'
        self.legacy = Forum(self.path)
        self.legacy.execute(300, {'NIM': '1', 'Nama': 'Ani'}, '/topik Lama')
        self.obs = Observer(self.path, self.roster, chats={-100}, staff={90}, instructors={99})
        self.bot = CIBot('dummy', self.roster, self.legacy, observer=self.obs)
        self.bot.send_message = Mock()
        self.bot._api_call = Mock(side_effect=lambda method,parameters,**kwargs:
            {'status':'left'} if method=='getChatMember' else {'invite_link':'https://t.me/+synthetic-ci'})
        self.seq = 0

    def update(self, text, uid=11, private=False, edited=False, mid=None, reply=None, chat_id=None):
        self.seq += 1
        msg = {'message_id': mid or self.seq, 'date': int(time.time())+1,
               'text': text, 'chat': {'id': chat_id if chat_id is not None else uid if private else -100,
                                     'type': 'private' if private else 'supergroup'},
               'from': {'id': uid}}
        if reply:
            msg['reply_to_message'] = {'message_id': reply}
        if edited:
            msg['edit_date'] = int(time.time())+10
        return {'update_id': self.seq, 'edited_message' if edited else 'message': msg}

    def say(self, text, **kwargs):
        u = self.update(text, **kwargs)
        self.bot.handle_update(u)
        return u

    def agree(self, uid=11):
        self.say('/setuju', uid=uid, private=True)

    def test_consent_registered_allowlisted_only_and_legacy_preserved(self):
        before = self.roster.read_bytes()
        self.say('not consented')
        self.agree()
        self.say('registered')
        self.say('unknown', uid=777)
        self.say('other group', chat_id=-500)
        self.assertEqual(1, len(self.obs.state(-100)['rows']))
        self.assertEqual(before, self.roster.read_bytes())
        self.assertIn('Lama', self.legacy.execute(301, {'NIM':'1','Nama':'Ani'}, '/daftar'))

    def test_dedup_edit_context_and_incremental_analysis(self):
        self.agree()
        first = self.say('Saya usul A', mid=10)
        self.bot.handle_update(first)
        self.assertEqual(1, self.obs.analyze(-100))
        self.assertEqual(0, self.obs.analyze(-100))
        self.agree(22)
        self.say('Mari gabungkan menjadi sintesis', uid=22, reply=10)
        self.assertEqual(1, self.obs.analyze(-100))
        with self.obs.db() as db:
            a = json.loads(db.execute('SELECT result FROM ci_assessments ORDER BY message_id DESC').fetchone()[0])
        self.assertEqual(2, len(a['dimensions']['integration']['evidence_message_ids']))
        self.say('Saya usul B', edited=True, mid=10)
        self.assertEqual(2, self.obs.analyze(-100))
        self.assertEqual(2, len(self.obs.state(-100)['rows']))
        self.assertIn('Saya usul B', self.obs.report(-100, summary=True))
        self.assertNotIn('Saya usul A', self.obs.report(-100, summary=True))

    def test_roles_pause_resume_and_private_feedback(self):
        self.agree()
        self.say('/pause')
        self.assertFalse(self.obs.state(-100)['paused'])
        self.say('/pause', uid=90)
        self.say('ignored')
        self.assertEqual([], self.obs.state(-100)['rows'])
        self.assertEqual([], self.obs.tick())
        self.say('/resume', uid=90)
        self.say('because', mid=10)
        self.say('/refleksi')
        self.assertIn('chat pribadi', self.bot.send_message.call_args.args[1])
        self.say('/refleksi', uid=22, private=True)
        self.assertNotIn('because', self.bot.send_message.call_args.args[1])
        self.say('/refleksi', private=True)
        self.assertIn('because', self.bot.send_message.call_args.args[1])

    def test_review_ownership_and_instructor_correction(self):
        self.agree()
        self.say('Saya akan menguji aplikasi')
        msg_id = self.obs.state(-100)['rows'][0]['id']
        self.say(f'/tinjau {msg_id} Tolong baca konteks', uid=22, private=True)
        self.assertIn('bukan milik Anda', self.bot.send_message.call_args.args[1])
        self.say(f'/tinjau {msg_id} Tolong baca konteks', private=True)
        self.say(f'/koreksi {msg_id} Perlu pemeriksaan sumber', uid=90, private=True)
        self.assertIn('khusus dosen', self.bot.send_message.call_args.args[1])
        self.say(f'/koreksi {msg_id} Perlu pemeriksaan sumber', uid=99, private=True)
        self.assertIn('Perlu pemeriksaan sumber', self.obs.reflection(-100, 11))
        self.say(f'/tinjauan', uid=99, private=True)
        self.assertIn('Tolong baca konteks', self.bot.send_message.call_args.args[1])
        self.say(f'/bukti {msg_id}', uid=22, private=True)
        self.assertIn('akses tidak diizinkan', self.bot.send_message.call_args.args[1])
        self.say(f'/bukti {msg_id}', uid=99, private=True)
        self.assertIn('Saya akan menguji', self.bot.send_message.call_args.args[1])

    def test_mutating_command_retry_is_atomic_and_idempotent(self):
        consent = self.update('/setuju', private=True)
        self.bot.handle_update(consent)
        with self.obs.db() as db:
            original = db.execute('SELECT updated FROM ci_consent WHERE telegram_id=11').fetchone()[0]
        self.bot.handle_update(consent)
        with self.obs.db() as db:
            self.assertEqual(original, db.execute('SELECT updated FROM ci_consent WHERE telegram_id=11').fetchone()[0])
        self.say('Bukti')
        msg_id = self.obs.state(-100)['rows'][0]['id']
        request = self.update(f'/tinjau {msg_id} Tolong periksa', private=True)
        self.bot.handle_update(request)
        self.bot.handle_update(request)
        with self.obs.db() as db:
            self.assertEqual(1, db.execute('SELECT COUNT(*) FROM ci_reviews').fetchone()[0])

    def test_scheduler_summary_changes_only_and_retry(self):
        self.agree()
        self.say('Saya usul A')
        items = self.obs.tick()
        self.assertEqual(1, len(items))
        self.assertEqual(1, len(self.obs.tick()))  # not acknowledged on send failure
        cid, text, fingerprint, now = items[0]
        self.obs.mark_summary(cid, fingerprint, now)
        self.assertEqual([], self.obs.tick(now+1300))
        self.assertIn('bukan nilai akademik', text)
        self.assertIn('2 mahasiswa belum teramati', text)

    def test_withdraw_delete_retention_and_old_backlog(self):
        self.agree()
        old = self.update('backlog')
        old['message']['date'] = int(time.time())-100
        self.bot.handle_update(old)
        self.assertEqual([], self.obs.state(-100)['rows'])
        self.say('first')
        self.say('/tarik', private=True)
        self.say('not recorded')
        self.assertEqual(1, len(self.obs.state(-100)['rows']))
        self.say('/hapusdata', private=True)
        self.assertEqual([], self.obs.state(-100)['rows'])
        self.agree()
        self.say('expires')
        self.obs.purge(time.time()+100*86400)
        self.assertEqual([], self.obs.state(-100)['rows'])

    def test_edited_to_command_removes_stale_evidence(self):
        self.agree()
        self.say('old text', mid=10)
        self.obs.analyze(-100)
        self.say('/pause', edited=True, mid=10)
        self.assertFalse(self.obs.state(-100)['paused'])
        self.assertEqual([], self.obs.state(-100)['rows'])

    def test_no_unsupported_quality_or_consensus_inference(self):
        self.agree()
        self.say('Oke setuju')
        self.obs.analyze(-100)
        with self.obs.db() as db:
            result = json.loads(db.execute('SELECT result FROM ci_assessments').fetchone()[0])
        self.assertTrue(all(d['score'] is None for d in result['dimensions'].values()))
        self.assertIn('belum memvalidasi', self.obs.report(-100, True).lower())

    def test_simulator_without_token_is_reproducible(self):
        a, b = self.root/'sim-a.sqlite3', self.root/'sim-b.sqlite3'
        output = simulate(a, 7)
        self.assertIn('DATA SINTETIK', output)
        self.assertIn('64 pesan', output)
        simulate(b, 7)
        with Observer(a, a.with_suffix('.participants.csv')).db() as db:
            first = [tuple(r) for r in db.execute('SELECT nim,text FROM ci_messages ORDER BY id')]
        with Observer(b, b.with_suffix('.participants.csv')).db() as db:
            second = [tuple(r) for r in db.execute('SELECT nim,text FROM ci_messages ORDER BY id')]
        self.assertEqual(first, second)
        with self.assertRaises(SystemExit):
            simulate(a)

    def test_polling_requests_edits_and_saves_offset(self):
        self.agree()
        message = self.update('recorded')
        self.bot._api_call = Mock(side_effect=[{'username':'ci_bot'}, [message], KeyboardInterrupt])
        self.bot._save_offset = Mock()
        with self.assertRaises(KeyboardInterrupt):
            self.bot.run()
        params = self.bot._api_call.call_args_list[1].args[1]
        self.assertIn('edited_message', json.loads(params['allowed_updates']))
        self.bot._save_offset.assert_called_once_with(message['update_id']+1)

    def test_facilitator_fifo_handoff_and_permissions(self):
        self.say('/request_fasilitator')
        self.assertTrue(self.obs.is_facilitator(11, -100))
        self.say('/request_fasilitator', uid=22)
        self.say('/request_fasilitator', uid=33)
        self.say('/analisis', uid=22)
        self.assertIn('khusus fasilitator', self.bot.send_message.call_args.args[1])
        self.say('/pause')
        self.assertTrue(self.obs.state(-100)['paused'])
        self.say('/selesai_fasilitator')
        self.assertFalse(self.obs.is_facilitator(11, -100))
        self.assertTrue(self.obs.is_facilitator(22, -100))
        self.assertIn('Aktif: Budi', self.bot.send_message.call_args.args[1])
        self.say('/resume', uid=22)
        self.assertFalse(self.obs.state(-100)['paused'])
        self.say('/pause')
        self.assertFalse(self.obs.state(-100)['paused'])
        self.assertTrue(self.obs.is_facilitator(99, -100))

    def test_facilitator_cancel_rejoin_and_idempotent_request(self):
        first = self.say('/request', uid=11)
        self.bot.handle_update(first)
        self.say('/request_fasilitator', uid=22)
        self.say('/request_fasilitator', uid=22)
        self.say('/request_fasilitator', uid=33)
        with self.obs.db() as db:
            self.assertEqual(3, db.execute('SELECT COUNT(*) FROM ci_facilitators').fetchone()[0])
        self.say('/unrequest', uid=22)
        self.say('/request', uid=22)
        self.say('/antrian_fasilitator')
        result = self.bot.send_message.call_args.args[1]
        self.assertLess(result.index('1. Cici'), result.index('2. Budi'))
        finish = self.say('/selesai_fasilitator')
        self.bot.handle_update(finish)
        self.assertTrue(self.obs.is_facilitator(33, -100))
        with self.obs.db() as db:
            self.assertEqual(1, db.execute("SELECT COUNT(*) FROM ci_facilitators WHERE status='done'").fetchone()[0])

    def test_facilitator_self_only_and_no_academic_privilege(self):
        self.agree(22)
        self.say('Bukti milik Budi', uid=22)
        evidence = self.obs.state(-100)['rows'][0]['id']
        self.say('/request_fasilitator')
        self.say('/unrequest_fasilitator 11', uid=22)
        self.assertIn('tanpa argumen', self.bot.send_message.call_args.args[1])
        self.say('/selesai_fasilitator', uid=22)
        self.assertTrue(self.obs.is_facilitator(11, -100))
        self.say('/unrequest_fasilitator')
        self.assertIn('/selesai_fasilitator', self.bot.send_message.call_args.args[1])
        self.assertTrue(self.obs.is_facilitator(11, -100))
        self.say(f'/bukti {evidence}', private=True)
        self.assertIn('akses tidak diizinkan', self.bot.send_message.call_args.args[1])
        self.say(f'/koreksi {evidence} Catatan', private=True)
        self.assertIn('khusus dosen', self.bot.send_message.call_args.args[1])

    def test_facilitator_persistence_forum_scope_and_student_only(self):
        self.obs.chats.add(-200)
        self.say('/request_fasilitator', chat_id=-100)
        self.say('/request_fasilitator', uid=22, chat_id=-200)
        reopened = Observer(self.path, self.roster, chats={-100, -200})
        self.assertTrue(reopened.is_facilitator(11, -100))
        self.assertFalse(reopened.is_facilitator(11, -200))
        self.assertTrue(reopened.is_facilitator(22, -200))
        self.say('/request_fasilitator', uid=99, chat_id=-100)
        self.assertIn('khusus mahasiswa', self.bot.send_message.call_args.args[1])
        self.say('/request_fasilitator', uid=777, private=True)
        self.assertIn('belum terhubung', self.bot.send_message.call_args.args[1])

    def test_facilitator_private_selected_forum_and_removed_student(self):
        self.obs.chats.add(-200)
        self.say('/forum -100', private=True)
        self.say('/request_fasilitator', private=True)
        self.say('/request_fasilitator', uid=22)
        self.roster.write_text('NIM,Nama,ID,repo\n2,Budi,22,\n3,Cici,33,\n')
        self.assertFalse(self.obs.is_facilitator(11, -100))
        self.assertTrue(self.obs.is_facilitator(22, -100))

    def test_facilitator_delete_data_releases_role(self):
        self.say('/request_fasilitator')
        self.say('/request_fasilitator', uid=22)
        self.say('/hapusdata', private=True)
        self.assertFalse(self.obs.is_facilitator(11, -100))
        self.assertTrue(self.obs.is_facilitator(22, -100))
        with self.obs.db() as db:
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM ci_facilitators WHERE telegram_id=11').fetchone()[0])
