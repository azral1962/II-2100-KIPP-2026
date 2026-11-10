import json
import tempfile
import time
import unittest
from pathlib import Path

from ci_observer import Observer
from ci_lab import DEFAULT_WEIGHTS
from ci_lab_simulator import run_experiment


class LaboratoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.roster=self.root/'peserta.csv'
        self.roster.write_text('NIM,Nama,ID,repo\n'+''.join(f'{i},Peserta {i},{i*11},\n' for i in range(1,7)))
        self.o=Observer(self.root/'ci.sqlite3',self.roster,chats={-10},instructors={99})
        self.lab=self.o.lab; self.clock=time.time(); self.seq=0
        for i in range(1,7):
            self.command('/setuju',uid=i*11,private=True)
        self.sid=self.lab.start(99,-10,'Uji kelas',started=self.clock-10)

    def command(self,text,uid=11,private=False):
        self.seq+=1
        response=self.o.handle({'update_id':self.seq,'message':{'message_id':self.seq,'date':int(self.clock),
            'from':{'id':uid},'chat':{'id':uid if private else -10,'type':'private' if private else 'supergroup'},'text':text}})
        return response[0][1] if response else ''

    def message(self,uid,text,mid,reply=None,edit=False):
        self.seq+=1
        msg={'message_id':mid,'date':int(self.clock),'from':{'id':uid},'chat':{'id':-10,'type':'supergroup'},'text':text}
        if reply: msg['reply_to_message']={'message_id':reply}
        if edit: msg['edit_date']=int(self.clock)+5
        self.o.handle({'update_id':self.seq,'edited_message' if edit else 'message':msg})

    def agreement(self):
        self.command('/usulan Catat bukti dan wajibkan konfirmasi manusia.')
        self.command('/sepakat 1',uid=99)
        for uid in [11,22,33,44,55,66]: self.command('/sikap 1 setuju',uid=uid)
        self.command('/konfirmasi 1',uid=99)

    def test_session_roles_phase_cohort_and_scope(self):
        with self.assertRaises(PermissionError): self.lab.start(11,-10,'Tidak boleh')
        with self.assertRaises(ValueError): self.lab.start(99,-10,'Duplikat aktif')
        self.lab.phase(99,self.sid,'Interest')
        self.lab.phase(99,self.sid,'Attention')  # TAIDA may move backward.
        self.assertEqual('Attention',self.lab.session(self.sid)['phase'])
        with self.assertRaises(ValueError): self.lab.phase(99,self.sid,'Tidak valid')
        self.assertEqual(6,self.lab.metrics(self.sid)['students'])
        with self.assertRaises(PermissionError): self.lab.sessions(777,-10)

    def test_social_graph_observed_not_inferred_and_missing_groups(self):
        for nim,group in [('1','A'),('2','A'),('3','B')]: self.lab.set_group(99,-10,nim,group)
        self.message(11,'Ide A',100)
        self.message(22,'Karena bukti',101,100)
        self.message(11,'Terima kasih',102,101)
        self.message(33,'Perspektif lain',103,100)
        self.o.command(99,{'NIM':'staff:99'},{'id':99,'type':'private'},'/setuju','')
        self.message(99,'Bagaimana menguji?',104,103)
        m=self.lab.metrics(self.sid,self.clock+10)
        self.assertEqual(2,m['social']['bonding_edges'])
        self.assertEqual(1,m['social']['bridging_edges'])
        self.assertEqual(1,m['social']['linking_edges'])
        self.assertEqual(1,m['social']['mutual_dyads'])
        self.assertAlmostEqual(1/3,m['social']['reciprocity'])
        self.assertEqual(3,m['active'])
        self.assertNotIn('trust',m['social'])
        self.message(44,'Kelompok belum ada',105,100)
        self.assertEqual(1,self.lab.metrics(self.sid,self.clock+10)['social']['group_unknown_edges'])

    def test_empty_and_low_sample_not_zero_quality_and_weight_validation(self):
        m=self.lab.metrics(self.sid)
        self.assertIsNone(m['index']); self.assertIsNone(m['social']['reciprocity'])
        self.assertIsNone(m['social']['bridging_share'])
        self.message(11,'Pesan tunggal',100)
        self.assertIsNone(self.lab.metrics(self.sid,self.clock+10)['index'])
        with self.assertRaises(ValueError): self.lab.set_weights(99,-10,{k:float('nan') for k in DEFAULT_WEIGHTS})
        with self.assertRaises(ValueError): self.lab.set_weights(99,-10,{k:0 for k in DEFAULT_WEIGHTS})
        with self.assertRaises(PermissionError): self.lab.set_weights(11,-10,DEFAULT_WEIGHTS)
        custom={k:(3 if k=='participation' else 1) for k in DEFAULT_WEIGHTS}
        self.lab.set_weights(99,-10,custom)
        self.assertAlmostEqual(1,sum(self.lab.metrics(self.sid)['weights'].values()))

    def test_surveys_minimum_and_paired_changes(self):
        for uid in [11,22,33,44]: self.lab.survey(uid,self.sid,'pra',[2,3,4,5])
        self.assertIsNone(self.lab.survey_summary(self.sid)['pra']['means'])
        self.lab.survey(55,self.sid,'pra',[2,3,4,5])
        for uid in [11,22,33,44,55]: self.lab.survey(uid,self.sid,'pasca',[4,4,4,4])
        summary=self.lab.survey_summary(self.sid)
        self.assertEqual(5,summary['paired']['n'])
        self.assertEqual(2,summary['paired']['delta']['trust'])
        with self.assertRaises(ValueError): self.lab.survey(11,self.sid,'pra',[0,6,3,3])
        self.command('/tarik',private=True)
        with self.assertRaises(PermissionError): self.lab.survey(11,self.sid,'pra',[3]*4)

    def test_private_assessment_service_enforces_identity(self):
        self.message(22,'Pesan pribadi dalam asesmen Budi',100)
        with self.assertRaises(PermissionError): self.lab.personal(11,self.sid,22)
        self.assertEqual(1,len(self.lab.personal(99,self.sid,22)))
        self.assertEqual([],self.lab.personal(11,self.sid))
        public=self.lab.conversations(11,self.sid)
        self.assertNotIn('result',public[0]); self.assertNotIn('telegram_id',public[0])

    def test_snapshots_dedup_and_changed_evidence_marked(self):
        self.message(11,'Ide awal',100)
        self.lab.capture(self.sid,self.clock+10)
        self.lab.capture(self.sid,self.clock+11)
        self.assertEqual(1,len(self.lab.timeline(11,self.sid)))
        self.message(11,'Ide diedit',100,edit=True)
        self.assertFalse(self.lab.timeline(11,self.sid)[0]['evidence_valid'])
        self.lab.capture(self.sid,self.clock+12)
        self.assertEqual(2,len(self.lab.timeline(11,self.sid)))

    def test_charter_uses_only_confirmed_decisions_versioning_and_staleness(self):
        with self.assertRaises(ValueError): self.lab.charter(99,self.sid,'Belum disepakati')
        self.agreement()
        cid=self.lab.charter(99,self.sid,'Charter UAS',{'acceptance_criteria':'Uji akses pribadi.'},expected_version=0)
        text=self.lab.export_charter(11,cid)
        self.assertIn('[R1 / U1]',text)
        self.assertIn('bukan otomatis konsensus',text)
        with self.assertRaises(PermissionError): self.lab.approve_charter(11,cid)
        with self.assertRaises(ValueError): self.lab.charter(99,self.sid,'Bentrok',expected_version=0)
        self.lab.approve_charter(99,cid)
        self.assertEqual('approved',self.lab.charters(11,self.sid)[0]['status'])
        self.command('/bukaulang 1',uid=99)
        self.assertEqual('stale',self.lab.charters(11,self.sid)[0]['status'])
        with self.assertRaises(ValueError): self.lab.approve_charter(99,cid)

    def test_erase_participant_removes_derived_survey_snapshots_charter(self):
        self.agreement(); cid=self.lab.charter(99,self.sid,'Charter')
        self.message(11,'Bukti',100)
        self.lab.capture(self.sid,self.clock+10)
        self.lab.survey(11,self.sid,'pra',[3]*4)
        self.command('/hapusdata',private=True)
        self.assertEqual([],self.lab.timeline(99,self.sid))
        self.assertEqual([],self.lab.charters(99,self.sid))
        self.assertEqual(0,self.lab.survey_summary(self.sid)['pra']['n'])

    def test_closed_session_isolates_later_messages_and_new_session(self):
        self.message(11,'Sesi pertama',100)
        self.lab.close(99,self.sid,self.clock+2)
        self.seq+=1
        self.o.handle({'update_id':self.seq,'message':{'message_id':101,'date':int(self.clock)+10,'text':'Sesi lain',
                      'from':{'id':22},'chat':{'id':-10,'type':'supergroup'}}})
        self.assertEqual(1,self.lab.metrics(self.sid,self.clock+20)['messages'])
        new=self.lab.start(99,-10,'Berikutnya',started=self.clock+3)
        self.assertEqual(1,self.lab.metrics(new,self.clock+20)['messages'])

    def test_multi_agent_policies_reproducible_and_keep_production_untouched(self):
        original=self.roster.read_bytes()
        a,sid=run_experiment(self.root/'a.sqlite3',7,'inclusive',40)
        b,sid2=run_experiment(self.root/'b.sqlite3',7,'inclusive',40)
        baseline,base_sid=run_experiment(self.root/'baseline.sqlite3',7,'none',40)
        with a.db() as db: events_a=db.execute('SELECT events FROM ci_v3_simulations').fetchone()[0]
        with b.db() as db: events_b=db.execute('SELECT events FROM ci_v3_simulations').fetchone()[0]
        self.assertEqual(events_a,events_b)
        self.assertEqual(40,a.lab.metrics(sid)['active'])
        self.assertLess(baseline.lab.metrics(base_sid)['active'],40)
        self.assertTrue(a.lab.metrics(sid)['synthetic'])
        self.assertTrue(a.lab.confirmed_sources(sid))
        self.assertFalse(baseline.lab.confirmed_sources(base_sid))
        self.assertTrue(a.lab.charters(9999,sid))
        self.assertEqual(original,self.roster.read_bytes())
        with self.assertRaises(ValueError): run_experiment(self.root/'a.sqlite3',7,'none',40)
