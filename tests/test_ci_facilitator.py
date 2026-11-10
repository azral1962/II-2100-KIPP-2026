import tempfile
import time
import unittest
from pathlib import Path

from ci_observer import Observer


class IntelligentFacilitatorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.roster = root / 'peserta.csv'
        self.roster.write_text('NIM,Nama,ID,repo\n1,Ani,11,\n2,Budi,22,\n3,Cici,33,\n')
        self.observer = Observer(root/'ci.sqlite3', self.roster, chats={-10}, instructors={99})
        self.engine = self.observer.facilitator
        self.seq = 0
        for uid in [11,22,33]:
            self.send('/setuju', uid=uid, private=True)

    def update(self, text, uid=11, private=False, mid=None, reply=None, edited=False, chat_id=None):
        self.seq += 1
        message = dict(text=text, from_={'id':uid}, date=int(time.time())+1,
                       message_id=mid or self.seq,
                       chat={'id':chat_id if chat_id is not None else uid if private else -10,
                             'type':'private' if private else 'supergroup'})
        message['from'] = message.pop('from_')
        if reply:
            message['reply_to_message'] = {'message_id':reply}
        if edited:
            message['edit_date'] = int(time.time())+10
        return {'update_id':self.seq, 'edited_message' if edited else 'message':message}

    def send(self, text, **kwargs):
        response = self.observer.handle(self.update(text, **kwargs))
        return response[0][1] if response else ''

    def seed_messages(self):
        for i in range(6):
            self.send('Saya usul A karena perlu data.' if i != 1 else 'Saya tidak setuju karena belum ada bukti.', mid=100+i)
        self.send('Bagaimana kebutuhan peserta lain?', uid=22, reply=100, mid=106)

    def make_round(self):
        self.send('/usulan Bangun prototipe dengan uji kelas.')
        result = self.send('/sepakat 1', uid=99)
        self.assertIn('Belum ada konsensus', result)
        return 1

    def test_detection_participation_disagreement_and_integration_gap(self):
        self.seed_messages()
        state = self.engine.snapshot(-10)
        self.assertIn('concentration', state['triggers'])
        self.assertIn('disagreement', state['triggers'])
        self.assertIn('integration_gap', state['triggers'])
        self.assertEqual(2, state['active'])
        # Two of three active is above default 60% threshold.
        self.assertNotIn('participation_gap', state['triggers'])
        self.assertEqual(1, len(state['disagreements']))
        self.assertIn('bukan diagnosis konflik personal', self.send('/konflik'))
        self.assertIn('M', self.send('/konflik'))
        self.send('/hapusdata', uid=22, private=True)
        self.assertIn('participation_gap', self.engine.snapshot(-10)['triggers'])

    def test_integration_requires_real_cross_person_sources_and_invalidates_edits(self):
        self.send('Usul A', mid=100)
        self.send('Usul B', uid=22, mid=101)
        self.send('Usul C', mid=102)
        self.assertIn('tersimpan', self.send('/integrasi M1,M2 Gabungkan kebutuhan A dan B.'))
        self.assertEqual(1, len(self.engine.snapshot(-10)['integrations']))
        self.assertIn('dua peserta', self.send('/integrasi 1,3 Gabungkan'))
        self.assertIn('tersedia pada forum', self.send('/integrasi 1,999 Gabungkan'))
        self.send('Usul B diperbaiki', uid=22, mid=101, edited=True)
        self.assertEqual(0, len(self.engine.snapshot(-10)['integrations']))

    def test_partial_source_deletion_invalidates_three_source_integration(self):
        self.send('Usul A', mid=100)
        self.send('Usul B', uid=22, mid=101)
        self.send('Usul C', uid=33, mid=102)
        self.send('/integrasi 1,2,3 Gabungkan tiga gagasan')
        self.assertEqual(1, len(self.engine.snapshot(-10)['integrations']))
        self.send('/hapusdata', uid=22, private=True)
        self.assertEqual(0, len(self.engine.snapshot(-10)['integrations']))

    def test_private_recommendations_require_human_approval_and_support_edits(self):
        self.seed_messages()
        self.observer.analyze(-10)
        self.assertIn('chat pribadi', self.send('/intervensi', uid=99))
        self.assertIn('khusus fasilitator', self.send('/intervensi', private=True))
        self.assertIn('Saran intervensi', self.send('/intervensi', uid=99, private=True))
        before = self.engine.pending_deliveries()
        self.assertTrue(before)
        self.assertTrue(all(kind == 'notify' and recipient == 99 for recipient,_,_,kind in before))
        target = before[0][2]
        original = before[0][1]
        alternative = self.send(f'/alternatif {target}', uid=99, private=True)
        self.assertNotEqual(original, alternative)
        self.assertIn('antrean kirim', self.send(f'/terapkan {target} Mari periksa asumsi bersama.', uid=99, private=True))
        posts = [x for x in self.engine.pending_deliveries() if x[3]=='post']
        self.assertEqual(1,len(posts))
        self.assertEqual(-10,posts[0][0])
        self.assertIn('Mari periksa asumsi bersama.',posts[0][1])
        self.engine.mark_delivered(posts[0][0],posts[0][2],posts[0][3])
        self.assertFalse(any(x[3]=='post' for x in self.engine.pending_deliveries()))

    def test_notification_dedup_ignore_and_pause(self):
        self.seed_messages()
        self.observer.analyze(-10)
        items = self.engine.pending_deliveries()
        for recipient,_,iid,kind in items:
            self.engine.mark_delivered(recipient,iid,kind)
        self.assertEqual([],self.engine.pending_deliveries())
        first = items[0][2]
        self.send(f'/abaikan {first}',uid=99,private=True)
        self.assertIn('tidak tersedia', self.send(f'/terapkan {first}',uid=99,private=True))
        self.send('/pause',uid=99)
        self.assertEqual([],self.engine.pending_deliveries())
        self.assertIn('dijeda',self.send('/intervensi',uid=99,private=True))

    def test_stale_recommendation_not_posted_after_evidence_edit(self):
        self.seed_messages()
        self.observer.analyze(-10)
        target = self.engine.pending_deliveries()[0][2]
        self.send(f'/terapkan {target}',uid=99,private=True)
        self.send('Baru',mid=100,edited=True)
        self.assertFalse(any(x[3]=='post' for x in self.engine.pending_deliveries()))
        self.assertIn('tidak tersedia',self.send(f'/terapkan {target}',uid=99,private=True))

    def test_consensus_unanimity_not_silence_and_manual_confirmation(self):
        self.make_round()
        self.send('/sikap 1 setuju')
        self.assertIn('Belum dapat dikonfirmasi', self.send('/konfirmasi 1',uid=99))
        self.send('/sikap 1 abstain Belum punya data',uid=22)
        self.send('/sikap 1 keberatan Perlu kriteria privasi',uid=33)
        self.assertIn('Perlu kriteria privasi',self.send('/keberatan'))
        self.assertIn('open_objection',self.engine.snapshot(-10)['triggers'])
        self.assertIn('Belum dapat dikonfirmasi',self.send('/konfirmasi 1',uid=99))
        self.send('/sikap 1 setuju',uid=22)
        self.send('/sikap 1 setuju',uid=33)
        self.assertIn('[open]',self.send('/konsensus 1'))
        self.assertIn('khusus fasilitator',self.send('/konfirmasi 1'))
        self.assertIn('dikonfirmasi',self.send('/konfirmasi 1',uid=99))
        self.assertIn('[confirmed]',self.send('/konsensus 1'))
        self.assertIn('tidak terbuka',self.send('/sikap 1 keberatan Baru',uid=22))
        self.assertNotIn('open_objection',self.engine.snapshot(-10)['triggers'])
        self.assertEqual(1,self.engine.snapshot(-10)['resolved'])

    def test_reopen_requires_new_votes_and_roster_snapshot(self):
        self.make_round()
        for uid in [11,22,33]:
            self.send('/sikap 1 setuju',uid=uid)
        self.roster.write_text('NIM,Nama,ID,repo\n1,Ani,11,\n2,Budi,22,\n3,Cici,33,\n4,Dodi,44,\n')
        self.assertIn('Daftar peserta berubah',self.send('/konfirmasi 1',uid=99))
        self.assertIn('R2 dibuka',self.send('/bukaulang 1',uid=99))
        self.assertIn('Setuju 0/4',self.send('/konsensus 2'))
        self.assertIn('tidak terbuka',self.send('/sikap 1 setuju'))

    def test_forum_scoping_and_facilitator_revocation(self):
        self.observer.chats.add(-20)
        self.send('/request_fasilitator')
        self.send('/usulan A')
        self.assertIn('R1 dibuka',self.send('/sepakat 1'))
        self.assertIn('tidak ditemukan',self.send('/sepakat 1',uid=99,chat_id=-20))
        self.send('/selesai_fasilitator')
        self.assertIn('khusus fasilitator',self.send('/konfirmasi 1'))
        self.send('/forum -10',private=True)
        self.assertIn('khusus fasilitator',self.send('/intervensi',private=True))

    def test_retries_do_not_duplicate_proposals_rounds_or_integration(self):
        update = self.update('/usulan A')
        a = self.observer.handle(update)
        self.assertEqual(a,self.observer.handle(update))
        update = self.update('/sepakat 1',uid=99)
        self.observer.handle(update)
        self.observer.handle(update)
        with self.observer.db() as db:
            self.assertEqual(1,db.execute('SELECT COUNT(*) FROM ci_v2_proposals').fetchone()[0])
            self.assertEqual(1,db.execute('SELECT COUNT(*) FROM ci_v2_rounds').fetchone()[0])

    def test_delete_user_supersedes_decision_and_erases_objection(self):
        self.make_round()
        self.send('/sikap 1 keberatan Pesan pribadi saya',uid=22)
        self.send('/hapusdata',uid=22,private=True)
        self.assertNotIn('Pesan pribadi saya',self.send('/keberatan'))
        self.assertIn('[superseded]',self.send('/konsensus 1'))
        self.assertIn('tidak terbuka',self.send('/konfirmasi 1',uid=99))

    def test_bad_inputs_do_not_change_ballots(self):
        self.make_round()
        for text in ['/sikap 1 keberatan','/sikap 1 diam','/sepakat -1','/konsensus '+'9'*1000]:
            self.send(text,uid=99)
        with self.observer.db() as db:
            self.assertEqual(0,db.execute('SELECT COUNT(*) FROM ci_v2_ballots').fetchone()[0])
        self.send('/tarik',private=True)
        self.assertIn('/setuju',self.send('/sikap 1 setuju'))
