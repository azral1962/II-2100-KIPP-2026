"""Reproducible local multi-agent experiments. No live accounts or LLM calls."""
import csv
import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

from ci_observer import Observer
from ci_lab import CHARTER_FIELDS, PHASES

ASSUMPTIONS = ('SIMULASI SINTETIK: agen berbasis aturan, bukan manusia/LLM. Kebijakan mengubah '
               'kesempatan bicara dan pilihan balasan. Penerimaan usulan dimodelkan dari '
               'keterwakilan kebutuhan kelompok; perbedaan hasil bukan bukti kausal kelas nyata.')
NEEDS = ['kejelasan tujuan','perlindungan data','aksesibilitas','bukti dan evaluasi']


@dataclass
class Agent:
    index: int
    group: str
    style: str
    contributions: int = 0
    observed_needs: set = field(default_factory=set)

    @property
    def uid(self):
        return 1000+self.index

    @property
    def nim(self):
        return f'SIM{self.index+1:02d}'

    def observe(self, event):
        if event.get('need') is not None:
            self.observed_needs.add(event['need'])

    def speak(self, phase, history, rng, bridge=False):
        need = NEEDS[int(self.group[-1])-1]
        options = [e for e in history if e['uid']!=self.uid]
        if bridge:
            options = [e for e in options if e.get('group')!=self.group] or options
        else:
            options = [e for e in options if e.get('group')==self.group] or options
        parent = rng.choice(options[-20:]) if options else None
        if phase=='Target':
            text = f'Saya usul sasaran proyek memuat {need} dan indikator uji kelas.'
        elif phase=='Attention':
            text = f'Berdasarkan pengamatan sintetik, {need} perlu diperiksa. Sumber contoh https://example.org/sintetik'
        elif phase=='Interest' and self.style=='penanya':
            text = f'Bagaimana usulan ini memenuhi {need} untuk pengguna yang berbeda?'
        elif phase=='Interest':
            text = f'Saya keberatan jika {need} belum punya kriteria penerimaan, karena kebutuhan kelompok berbeda.'
        elif phase=='Desire' and parent:
            text = f'Mari gabungkan gagasan sebelumnya dengan {need}; sintesis perlu mempertahankan kedua kebutuhan.'
        elif phase=='Desire':
            text = f'Bagaimana pendapat peserta yang belum berbicara tentang {need}?'
        else:
            text = f'Saya akan menguji {need} dengan contoh kasus dan mencatat hasilnya.'
        self.contributions+=1
        return {'uid':self.uid,'group':self.group,'need':need,'text':text,
                'reply':parent['mid'] if parent else None,'phase':phase}


def run_experiment(path, seed=42, policy='inclusive', steps=120):
    if policy not in {'none','inclusive','bridge'} or not 40<=steps<=400:
        raise ValueError('Kebijakan none/inclusive/bridge dan langkah 40–400 diperlukan.')
    path = Path(path)
    roster = path.with_suffix('.participants.csv')
    if path.exists() or roster.exists():
        raise ValueError('Simulasi harus memakai database dan CSV baru; data lama tidak ditimpa.')
    path.parent.mkdir(parents=True,exist_ok=True)
    agents = [Agent(i,f'Kelompok {i//10+1}',['penanya','pemberi bukti','pengkritik','penyintesis'][i%4]) for i in range(40)]
    with roster.open('x',newline='',encoding='utf-8') as output:
        writer=csv.writer(output)
        writer.writerow(['NIM','Nama','ID','repo'])
        for a in agents:
            writer.writerow([a.nim,f'Agen Sintetik {a.index+1}',a.uid,''])
    o=Observer(path,roster,chats={-999},instructors={9999})
    start=int(time.time())-7200
    # Replay uses an explicit logical clock. All identities and consent are synthetic.
    with o.db() as db:
        for uid in [a.uid for a in agents]+[9999]:
            db.execute('INSERT INTO ci_consent VALUES (?,1,?,?)',(uid,'synthetic-lab',start-1))
    sid=o.lab.start(9999,-999,'Eksperimen TISE sintetik',synthetic=True,started=start)
    for a in agents:
        o.lab.set_group(9999,-999,a.nim,a.group)
    rng=random.Random(seed)
    history=[]
    update_id=1
    for step in range(steps):
        phase=PHASES[min(4,step*5//steps)]
        if step==0 or phase!=history[-1]['phase']:
            o.lab.phase(9999,sid,phase)
        if policy=='none':
            actor=agents[rng.randrange(8)]
        elif policy=='inclusive':
            actor=agents[step%40]
        else:
            actor=agents[((step%4)*10+(step//4)%10)]
        event=actor.speak(phase,history,rng,policy=='bridge')
        event.update(mid=step+1,offset=(step+1)*6000//steps)
        msg={'message_id':event['mid'],'date':start+event['offset'],'text':event['text'],
             'chat':{'id':-999,'type':'supergroup','title':'LAB SINTETIK'},'from':{'id':actor.uid}}
        if event['reply']:
            msg['reply_to_message']={'message_id':event['reply']}
        o.handle({'update_id':update_id,'message':msg})
        update_id+=1
        history.append(event)
        for agent in agents:
            agent.observe(event)
        if (step+1)%max(1,steps//10)==0:
            o.lab.capture(sid,start+event['offset'])
    # A facilitator-agent asks humans' analogue a question; no real user receives it.
    for i,text in enumerate(['Perspektif siapa yang belum terdengar?','Apa bukti yang dapat kita uji bersama?']):
        o.handle({'update_id':update_id,'message':{'message_id':steps+1+i,'date':start+6050+i*20,
                 'text':text,'chat':{'id':-999,'type':'supergroup'},'from':{'id':9999},
                 'reply_to_message':{'message_id':history[-1]['mid']}}})
        update_id+=1
    with o.db() as db:
        first=db.execute('SELECT * FROM ci_messages WHERE chat_id=-999 AND telegram_id!=9999 ORDER BY id LIMIT 1').fetchone()
        second=db.execute('SELECT * FROM ci_messages WHERE chat_id=-999 AND telegram_id NOT IN (?,9999) ORDER BY id LIMIT 1',(first['telegram_id'],)).fetchone()
    chat={'id':-999,'type':'supergroup'}
    first_user={'NIM':agents[0].nim,'Nama':'Agen Sintetik 1'}
    if second:
        o.command(1000,first_user,chat,'/integrasi',f"{first['id']},{second['id']} Integrasikan tujuan dan kriteria uji yang dibutuhkan kelompok.")
    o.command(1000,first_user,chat,'/usulan','Aplikasi fasilitator harus menampilkan bukti, melindungi data, menyediakan akses setara, dan meminta konfirmasi manusia.')
    o.command(9999,{'NIM':'staff:9999'},chat,'/sepakat','1')
    for a in agents:
        # Explicit model assumption: only represented needs result in acceptance.
        acceptable=NEEDS[int(a.group[-1])-1] in a.observed_needs
        stance='setuju' if acceptable else 'keberatan Kebutuhan kelompok belum terwakili.'
        o.command(a.uid,{'NIM':a.nim},chat,'/sikap','1 '+stance)
    o.command(9999,{'NIM':'staff:9999'},chat,'/konfirmasi','1')
    # Put all synthetic decision events onto the replay clock.
    with o.db() as db:
        db.execute('UPDATE ci_v2_proposals SET created=?',(start+6100,))
        db.execute('UPDATE ci_v2_rounds SET created=?,confirmed_at=CASE WHEN confirmed_at IS NULL THEN NULL ELSE ? END',(start+6150,start+6500))
        db.execute('UPDATE ci_v2_integrations SET created=?',(start+6100,))
        db.execute('UPDATE ci_v2_ballot_history SET updated=?',(start+6400,))
        db.execute('UPDATE ci_v2_ballots SET updated=?',(start+6400,))
    o.lab.phase(9999,sid,'Action')
    o.analyze(-999)
    # Discard the wall-clock capture from analyze; replay snapshots use logical time.
    with o.db() as db:
        db.execute('DELETE FROM ci_v3_snapshots WHERE captured>?',(start+6600,))
    o.lab.close(9999,sid,start+6600)
    for a in agents:
        o.lab.survey(a.uid,sid,'pra',[3,3,3,3])
        o.lab.survey(a.uid,sid,'pasca',[4,4,4,4] if policy!='none' else [3,2,3,3])
    if o.lab.confirmed_sources(sid):
        fields=dict(zip(CHARTER_FIELDS,[
            'Fasilitator memerlukan dukungan yang memberi ruang beragam perspektif.',
            'Fasilitator komunitas, peserta, dan dosen.',
            'Penyimpanan lokal, akses sesuai peran, persetujuan, retensi, dan waktu respons yang diuji.',
            'Analisis bukti dan rekomendasi lokal; keputusan tetap pada manusia.',
            'Peserta, forum, pesan, bukti, usulan, putaran, sikap, intervensi, dan charter.',
            'Uji deduplikasi, akses pribadi, sumber bukti, keberatan, serta konfirmasi manusia.',
            'Akuisisi pesan; analitik; antarmuka; pengujian kelas; evaluasi.',
            'Prototipe lokal → uji sintetik → review dosen → pilot kelas → evaluasi.'
        ]))
        o.lab.charter(9999,sid,'Project Charter UAS — SIMULASI',fields)
    with o.db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS ci_v3_simulations (
            session_id INTEGER PRIMARY KEY REFERENCES ci_v3_sessions(id) ON DELETE CASCADE,
            seed INTEGER NOT NULL, policy TEXT NOT NULL, assumptions TEXT NOT NULL, events TEXT NOT NULL, agents TEXT NOT NULL)''')
        db.execute('INSERT INTO ci_v3_simulations VALUES (?,?,?,?,?,?)',(sid,seed,policy,ASSUMPTIONS,
                   json.dumps(history,ensure_ascii=False),json.dumps([{'nim':a.nim,'group':a.group,'style':a.style,
                        'contributions':a.contributions,'observed_needs':sorted(a.observed_needs)} for a in agents])))
    return o,sid


def summary(observer,sid):
    m=observer.lab.metrics(sid)
    return ('DATA SINTETIK — TISE Collective Intelligence Laboratory\n'+ASSUMPTIONS+'\n'
            +json.dumps({k:m[k] for k in ['messages','active','students','index','coverage','components','social','decisions']},ensure_ascii=False,indent=2))
