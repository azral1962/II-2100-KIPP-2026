"""TISE Collective Intelligence Laboratory: metrics, sessions, surveys, charters.

No psychological traits are inferred. All indices are exploratory process
indicators, with source evidence, denominators, and missing-data coverage.
"""
import hashlib
import json
import math
import re
import time
from collections import Counter
from contextlib import contextmanager

PHASES = ('Target', 'Attention', 'Interest', 'Desire', 'Action')
DEFAULT_WEIGHTS = {'participation': .20, 'balance': .15, 'knowledge': .20,
                   'deliberation': .15, 'action': .15, 'reciprocity': .15}
LIMITATION = ('Indeks eksploratif proses, belum tervalidasi ilmiah; bukan nilai akademik, '
              'ukuran kepribadian, atau bukti kausal perubahan CI. Data tidak tersedia berbeda dari nol.')
CHARTER_FIELDS = ('problem_statement','target_users','non_functional_requirements','ai_features',
                  'data_model','acceptance_criteria','work_packages','roadmap')


class Laboratory:
    def __init__(self, observer, weights=None):
        self.o = observer
        self.weights = self.validate_weights(weights or DEFAULT_WEIGHTS)
        with self.o.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS ci_v3_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL REFERENCES ci_forums(chat_id),
                    title TEXT NOT NULL, objective TEXT NOT NULL, started REAL NOT NULL, ended REAL,
                    phase TEXT NOT NULL DEFAULT 'Target', synthetic INTEGER NOT NULL DEFAULT 0, creator INTEGER NOT NULL);
                CREATE UNIQUE INDEX IF NOT EXISTS ci_v3_active_session ON ci_v3_sessions(chat_id) WHERE ended IS NULL;
                CREATE TABLE IF NOT EXISTS ci_v3_cohort (
                    session_id INTEGER NOT NULL REFERENCES ci_v3_sessions(id) ON DELETE CASCADE,
                    nim TEXT NOT NULL, telegram_id TEXT NOT NULL, PRIMARY KEY(session_id,nim));
                CREATE TABLE IF NOT EXISTS ci_v3_groups (
                    chat_id INTEGER NOT NULL REFERENCES ci_forums(chat_id), nim TEXT NOT NULL,
                    team TEXT NOT NULL, PRIMARY KEY(chat_id,nim));
                CREATE TABLE IF NOT EXISTS ci_v3_surveys (
                    session_id INTEGER NOT NULL REFERENCES ci_v3_sessions(id) ON DELETE CASCADE,
                    telegram_id INTEGER NOT NULL, stage TEXT NOT NULL CHECK(stage IN ('pra','pasca')),
                    trust INTEGER NOT NULL CHECK(trust BETWEEN 1 AND 5),
                    heard INTEGER NOT NULL CHECK(heard BETWEEN 1 AND 5),
                    safety INTEGER NOT NULL CHECK(safety BETWEEN 1 AND 5),
                    willingness INTEGER NOT NULL CHECK(willingness BETWEEN 1 AND 5), updated REAL NOT NULL,
                    PRIMARY KEY(session_id,telegram_id,stage));
                CREATE TABLE IF NOT EXISTS ci_v3_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL REFERENCES ci_v3_sessions(id) ON DELETE CASCADE,
                    captured REAL NOT NULL, fingerprint TEXT NOT NULL, data TEXT NOT NULL,
                    UNIQUE(session_id,fingerprint));
                CREATE TABLE IF NOT EXISTS ci_v3_charters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL REFERENCES ci_v3_sessions(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, sources TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('draft','approved','stale')),
                    author INTEGER NOT NULL, approved_by INTEGER, created REAL NOT NULL,
                    UNIQUE(session_id,version));
                CREATE TABLE IF NOT EXISTS ci_v3_settings (
                    chat_id INTEGER PRIMARY KEY REFERENCES ci_forums(chat_id), weights TEXT NOT NULL);
                INSERT OR IGNORE INTO ci_schema VALUES (4);
            ''')

    @staticmethod
    def validate_weights(weights):
        if set(weights) != set(DEFAULT_WEIGHTS):
            raise ValueError('Bobot harus memuat enam komponen indeks yang ditentukan.')
        clean = {key: float(value) for key,value in weights.items()}
        if any(not math.isfinite(v) or v < 0 for v in clean.values()) or sum(clean.values()) <= 0:
            raise ValueError('Bobot harus angka hingga, nonnegatif, dengan jumlah positif.')
        total = sum(clean.values())
        return {key:value/total for key,value in clean.items()}

    @contextmanager
    def transaction(self):
        # Shared with Telegram mutation receipts; dashboard mutations are atomic too.
        if self.o._active_db is not None:
            yield self.o._active_db
            return
        with self.o.db() as db:
            db.execute('BEGIN IMMEDIATE')
            self.o._active_db = db
            try:
                yield db
            finally:
                self.o._active_db = None

    def authorize(self, uid, chat_id, role='participant'):
        if chat_id not in self.o.chats or self.o.identity(uid) is None:
            raise PermissionError('Akses forum tidak diizinkan.')
        if role == 'instructor' and uid not in self.o.instructors:
            raise PermissionError('Tindakan ini khusus dosen.')
        if role == 'facilitator' and not self.o.is_facilitator(uid,chat_id):
            raise PermissionError('Tindakan ini khusus fasilitator aktif atau dosen/staf.')

    def session(self, sid):
        with self.o.db() as db:
            row = db.execute('SELECT * FROM ci_v3_sessions WHERE id=?',(sid,)).fetchone()
        if not row:
            raise ValueError('Sesi tidak ditemukan.')
        return dict(row)

    def sessions(self, uid, chat_id):
        self.authorize(uid,chat_id)
        with self.o.db() as db:
            return [dict(r) for r in db.execute('SELECT * FROM ci_v3_sessions WHERE chat_id=? ORDER BY id DESC',(chat_id,))]

    def latest(self, chat_id):
        with self.o.db() as db:
            row = db.execute('SELECT id FROM ci_v3_sessions WHERE chat_id=? ORDER BY id DESC LIMIT 1',(chat_id,)).fetchone()
        return row[0] if row else None

    def audit(self, db, uid, event):
        db.execute('INSERT INTO ci_audit(actor,event,created) VALUES (?,?,?)',(uid,event,time.time()))

    def start(self, uid, chat_id, title, *, objective=None, synthetic=False, started=None):
        self.authorize(uid,chat_id,'facilitator')
        if not title.strip() or len(title)>160:
            raise ValueError('Judul sesi harus 1–160 karakter.')
        with self.transaction() as db:
            self.o.facilitator.ensure_forum(db,chat_id)
            if db.execute('SELECT 1 FROM ci_v3_sessions WHERE chat_id=? AND ended IS NULL',(chat_id,)).fetchone():
                raise ValueError('Masih ada sesi aktif. Tutup sesi itu dahulu.')
            objective = objective or db.execute('SELECT objective FROM ci_forums WHERE chat_id=?',(chat_id,)).fetchone()[0]
            sid = db.execute('INSERT INTO ci_v3_sessions(chat_id,title,objective,started,synthetic,creator) VALUES (?,?,?,?,?,?)',
                             (chat_id,title,objective,int(time.time()) if started is None else started,int(synthetic),uid)).lastrowid
            roster = {r['NIM']: (r.get('ID') or '').strip() for r in self.o.roster()}
            db.executemany('INSERT INTO ci_v3_cohort VALUES (?,?,?)',[(sid,nim,tid) for nim,tid in roster.items()])
            self.audit(db,uid,f'sesi mulai {sid}')
        return sid

    def close(self, uid, sid, ended=None):
        s = self.session(sid)
        self.authorize(uid,s['chat_id'],'facilitator')
        with self.transaction() as db:
            end = time.time() if ended is None else ended
            if end < s['started']:
                raise ValueError('Waktu akhir harus sesudah awal sesi.')
            db.execute('UPDATE ci_v3_sessions SET ended=COALESCE(ended,?) WHERE id=?',(end,sid))
            self.capture(sid,end)
            self.audit(db,uid,f'sesi tutup {sid}')

    def phase(self, uid, sid, phase):
        s = self.session(sid)
        self.authorize(uid,s['chat_id'],'facilitator')
        if phase not in PHASES or s['ended'] is not None:
            raise ValueError('Pilih fase TAIDA yang valid pada sesi aktif.')
        with self.transaction() as db:
            db.execute('UPDATE ci_v3_sessions SET phase=? WHERE id=?',(phase,sid))
            self.audit(db,uid,f'fase sesi={sid} {phase}')

    def set_group(self, uid, chat_id, nim, team):
        self.authorize(uid,chat_id,'instructor')
        if nim not in {r['NIM'] for r in self.o.roster()} or not team.strip() or len(team)>60:
            raise ValueError('NIM harus terdaftar dan nama kelompok 1–60 karakter.')
        with self.transaction() as db:
            self.o.facilitator.ensure_forum(db,chat_id)
            db.execute('INSERT OR REPLACE INTO ci_v3_groups VALUES (?,?,?)',(chat_id,nim,team.strip()))
            self.audit(db,uid,f'kelompok forum={chat_id} nim={nim}')

    def survey(self, uid, sid, stage, values):
        s = self.session(sid)
        self.authorize(uid,s['chat_id'])
        if not self.o.consent(uid):
            raise PermissionError('Survei sukarela memerlukan /setuju di chat pribadi.')
        if stage not in {'pra','pasca'} or len(values)!=4 or any(type(v) is not int or not 1<=v<=5 for v in values):
            raise ValueError('Survei: pra/pasca dan empat angka 1–5 (trust, didengar, aman, kerja sama).')
        with self.transaction() as db:
            cohort = db.execute('SELECT 1 FROM ci_v3_cohort WHERE session_id=? AND telegram_id=?',(sid,str(uid))).fetchone()
            if not cohort:
                raise PermissionError('Anda tidak ada pada kohort sesi ini.')
            db.execute('INSERT OR REPLACE INTO ci_v3_surveys VALUES (?,?,?,?,?,?,?,?)',(sid,uid,stage,*values,time.time()))

    def survey_summary(self, sid):
        # Only aggregate >=5 respondents; paired delta avoids comparing different people.
        with self.o.db() as db:
            rows = db.execute('SELECT * FROM ci_v3_surveys WHERE session_id=?',(sid,)).fetchall()
        stages = {}
        for stage in ['pra','pasca']:
            selected = [r for r in rows if r['stage']==stage]
            stages[stage] = {'n':len(selected), 'means':{k:sum(r[k] for r in selected)/len(selected) for k in ['trust','heard','safety','willingness']} if len(selected)>=5 else None}
        before = {r['telegram_id']:r for r in rows if r['stage']=='pra'}
        pairs = [(before[r['telegram_id']],r) for r in rows if r['stage']=='pasca' and r['telegram_id'] in before]
        stages['paired'] = {'n':len(pairs),'delta':{k:sum(b[k]-a[k] for a,b in pairs)/len(pairs) for k in ['trust','heard','safety','willingness']} if len(pairs)>=5 else None}
        return stages

    def metrics(self, sid, until=None):
        s = self.session(sid)
        end = min(until if until is not None else time.time(),s['ended'] or float('inf'))
        with self.o.db() as db:
            config = db.execute('SELECT weights FROM ci_v3_settings WHERE chat_id=?',(s['chat_id'],)).fetchone()
            weights = json.loads(config[0]) if config else self.weights
            cohort = {r['nim'] for r in db.execute('SELECT nim FROM ci_v3_cohort WHERE session_id=?',(sid,))}
            rows = db.execute('SELECT * FROM ci_messages WHERE chat_id=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp,id',(s['chat_id'],s['started'],end)).fetchall()
            teams = dict(db.execute('SELECT nim,team FROM ci_v3_groups WHERE chat_id=?',(s['chat_id'],)).fetchall())
            integrations = [r for r in self.o.facilitator.valid_integrations(db,s['chat_id']) if s['started']<=r['created']<=end]
            available={r['id'] for r in rows}
            integrations=[r for r in integrations if all(source[0] in available for source in db.execute('SELECT message_id FROM ci_v2_sources WHERE integration=?',(r['id'],)))]
            rounds = db.execute('''SELECT r.* FROM ci_v2_rounds r JOIN ci_v2_proposals p ON p.id=r.proposal
                WHERE p.chat_id=? AND r.created>=? AND r.created<=? AND r.status!='superseded' ''',(s['chat_id'],s['started'],end)).fetchall()
        counts = Counter(r['nim'] for r in rows if r['nim'] in cohort)
        student_messages = sum(counts.values())
        participation = len(counts)/len(cohort) if cohort and rows else None
        balance = (-sum((n/student_messages)*math.log(n/student_messages) for n in counts.values())/math.log(len(cohort))) if student_messages and len(cohort)>1 else (1.0 if student_messages and len(cohort)==1 else None)
        by_mid = {r['telegram_message_id']:r for r in rows}
        edges, source_edges = Counter(), []
        within = across = unknown = linking = 0
        for r in rows:
            parent = by_mid.get(r['reply_to'])
            if not parent or parent['telegram_id']==r['telegram_id']:
                continue
            a,b = r['telegram_id'],parent['telegram_id']
            edges[(a,b)]+=1
            source_edges.append([r['id'],parent['id']])
            if (a in self.o.staff)!=(b in self.o.staff):
                linking+=1
            elif r['nim'] in cohort and parent['nim'] in cohort:
                ta,tb = teams.get(r['nim']),teams.get(parent['nim'])
                if not ta or not tb:
                    unknown+=1
                elif ta==tb:
                    within+=1
                else:
                    across+=1
        dyads = {tuple(sorted(pair)) for pair in edges}
        mutual = sum(1 for a,b in dyads if (a,b) in edges and (b,a) in edges)
        reciprocity = mutual/len(dyads) if dyads else None
        evidence = [r['id'] for r in rows if re.search(r'https?://|\b(karena|berdasarkan|sebab)\b',r['text'],re.I)]
        disagree = [r['id'] for r in rows if re.search(r'\b(tidak setuju|keberatan|namun|tetapi)\b',r['text'],re.I)]
        confirmed = [r for r in rounds if r['status']=='confirmed' and r['confirmed_at'] is not None and r['confirmed_at']<=end]
        components = {'participation':participation,'balance':balance,
                      'knowledge':min(1,(len(evidence)+2*len(integrations))/len(rows)) if rows else None,
                      'deliberation':min(1,len(source_edges)/len(rows)) if rows else None,
                      'action':len(confirmed)/len(rounds) if rounds else None,'reciprocity':reciprocity}
        coverage = sum(weights[k] for k,v in components.items() if v is not None)
        index = 100*sum(weights[k]*v for k,v in components.items() if v is not None)/coverage if coverage and student_messages>=6 else None
        group_edges = within+across
        data = {'session_id':sid,'until':end,'phase':s['phase'],'synthetic':bool(s['synthetic']),'messages':len(rows),'students':len(cohort),'active':len(counts),
                'components':components,'weights':weights,'coverage':coverage,'index':index,
                'knowledge':{'evidence_messages':evidence,'integrations':[r['id'] for r in integrations]},
                'deliberation':{'disagreement_messages':disagree,'reply_evidence':source_edges},
                'decisions':{'rounds':len(rounds),'confirmed':[r['id'] for r in confirmed]},
                'social':{'directed_reply_edges':sum(edges.values()),'dyads':len(dyads),'mutual_dyads':mutual,
                          'reciprocity':reciprocity,'bonding_edges':within,'bridging_edges':across,
                          'group_unknown_edges':unknown,'group_coverage':group_edges/(group_edges+unknown) if group_edges+unknown else None,
                          'bonding_share':within/group_edges if group_edges else None,
                          'bridging_share':across/group_edges if group_edges else None,
                          'linking_edges':linking},
                'sources':{str(r['id']):[r['revision'],r['telegram_id']] for r in rows},'limitation':LIMITATION}
        return data

    def capture(self, sid, until=None):
        data = self.metrics(sid,until)
        # Content hash excludes observation time so unchanged data is not repeatedly saved.
        hashed = {k:v for k,v in data.items() if k!='until'}
        fingerprint = hashlib.sha256(json.dumps(hashed,sort_keys=True).encode()).hexdigest()
        with self.o.db() as db:
            db.execute('INSERT OR IGNORE INTO ci_v3_snapshots(session_id,captured,fingerprint,data) VALUES (?,?,?,?)',
                       (sid,data['until'],fingerprint,json.dumps(data,ensure_ascii=False)))
        return data

    def set_weights(self, uid, chat_id, weights):
        self.authorize(uid,chat_id,'instructor')
        clean=self.validate_weights(weights)
        with self.transaction() as db:
            self.o.facilitator.ensure_forum(db,chat_id)
            db.execute('INSERT OR REPLACE INTO ci_v3_settings VALUES (?,?)',(chat_id,json.dumps(clean)))
            self.audit(db,uid,f'bobot indeks forum={chat_id}')

    def timeline(self, uid, sid):
        s = self.session(sid)
        self.authorize(uid,s['chat_id'])
        with self.o.db() as db:
            results=[]
            for r in db.execute('SELECT * FROM ci_v3_snapshots WHERE session_id=? ORDER BY captured,id',(sid,)).fetchall():
                data=json.loads(r['data'])
                valid=True
                for mid,expected in data['sources'].items():
                    source=db.execute('SELECT revision,telegram_id FROM ci_messages WHERE id=?',(int(mid),)).fetchone()
                    if not source or list(source)!=expected:
                        valid=False
                        break
                results.append(dict(captured=r['captured'],evidence_valid=valid,**data))
            return results

    def personal(self, uid, sid, target=None):
        s = self.session(sid)
        self.authorize(uid,s['chat_id'])
        target = uid if target is None else target
        if target!=uid and uid not in self.o.instructors:
            raise PermissionError('Asesmen pribadi mahasiswa lain hanya untuk dosen.')
        with self.o.db() as db:
            rows = db.execute('''SELECT m.id,m.timestamp,m.text,a.result FROM ci_messages m LEFT JOIN ci_assessments a ON a.message_id=m.id
                WHERE m.chat_id=? AND m.telegram_id=? AND m.timestamp>=? AND m.timestamp<=? ORDER BY m.timestamp,m.id''',
                (s['chat_id'],target,s['started'],s['ended'] or time.time())).fetchall()
        return [dict(r) for r in rows]

    def unheard(self, uid, sid):
        s=self.session(sid)
        self.authorize(uid,s['chat_id'],'facilitator')
        with self.o.db() as db:
            missing=db.execute('''SELECT c.nim FROM ci_v3_cohort c WHERE c.session_id=? AND NOT EXISTS
                (SELECT 1 FROM ci_messages m WHERE m.chat_id=? AND m.nim=c.nim AND m.timestamp>=? AND m.timestamp<=?)''',
                (sid,s['chat_id'],s['started'],s['ended'] or time.time())).fetchall()
        names={r['NIM']:r['Nama'] for r in self.o.roster()}
        return [{'NIM':r[0],'Nama':names.get(r[0],'Tidak lagi terdaftar')} for r in missing]

    def conversations(self, uid, sid):
        s = self.session(sid)
        self.authorize(uid,s['chat_id'])
        with self.o.db() as db:
            rows = db.execute('''SELECT m.*,a.result FROM ci_messages m LEFT JOIN ci_assessments a ON a.message_id=m.id
                WHERE m.chat_id=? AND m.timestamp>=? AND m.timestamp<=? ORDER BY m.timestamp,m.id''',
                (s['chat_id'],s['started'],s['ended'] or time.time())).fetchall()
        aliases = {tid:f'P{i+1:02d}' for i,tid in enumerate(sorted({r['telegram_id'] for r in rows}))}
        # Never send private assessment fields to the collective view.
        return [{'Bukti':f"M{r['id']}",'Waktu UTC':r['timestamp'],'Peserta':aliases[r['telegram_id']],
                 'Teks':r['text'],'Balasan Telegram':r['reply_to'],
                 'Kategori':', '.join(json.loads(r['result'])['speech_acts']) if r['result'] else 'belum dianalisis'} for r in rows]

    def confirmed_sources(self, sid):
        s = self.session(sid)
        with self.o.db() as db:
            return [dict(r) for r in db.execute('''SELECT r.id round_id,p.id proposal_id,p.body,r.confirmed_at FROM ci_v2_rounds r
                JOIN ci_v2_proposals p ON p.id=r.proposal WHERE p.chat_id=? AND r.status='confirmed'
                AND r.created>=? AND r.created<=? AND r.confirmed_at<=? ORDER BY r.id''',(s['chat_id'],s['started'],s['ended'] or time.time(),s['ended'] or time.time()))]

    def charter(self, uid, sid, title, fields=None, expected_version=None):
        s = self.session(sid)
        self.authorize(uid,s['chat_id'],'facilitator')
        if not title.strip() or len(title)>160:
            raise ValueError('Judul charter harus 1–160 karakter.')
        fields = fields or {}
        if set(fields)-set(CHARTER_FIELDS) or any(not isinstance(v,str) or len(v)>6000 for v in fields.values()):
            raise ValueError('Bagian charter tidak valid atau melebihi 6.000 karakter.')
        with self.transaction() as db:
            sources = self.confirmed_sources(sid)
            if not sources:
                raise ValueError('Charter membutuhkan sedikitnya satu putaran konsensus yang telah dikonfirmasi pada sesi ini.')
            previous = db.execute('SELECT COALESCE(MAX(version),0) FROM ci_v3_charters WHERE session_id=?',(sid,)).fetchone()[0]
            if expected_version is not None and expected_version!=previous:
                raise ValueError('Versi charter berubah; muat ulang sebelum menyimpan.')
            body = {'objective':s['objective'],'confirmed_requirements':sources,
                    'editorial':{k:fields.get(k,'Belum ditetapkan; perlu pembahasan manusia.') for k in CHARTER_FIELDS},
                    'editorial_status':'Bagian editorial adalah rancangan penyusun, bukan otomatis konsensus kelas.',
                    'tise':{'CI':'Keputusan dan integrasi pengetahuan peserta dengan bukti.',
                            'NI':'Observasi, empati, penilaian konteks, dan legitimasi keputusan oleh manusia.',
                            'AI':'Analisis indikator lokal dan rekomendasi pendukung; bukan pengambil keputusan.'}}
            cid = db.execute("INSERT INTO ci_v3_charters(session_id,version,title,body,sources,status,author,created) VALUES (?,?,?,?,?,'draft',?,?)",
                             (sid,previous+1,title,json.dumps(body,ensure_ascii=False),json.dumps([r['round_id'] for r in sources]),uid,time.time())).lastrowid
            self.audit(db,uid,f'charter draft={cid} sesi={sid}')
        return cid

    def validate_charters(self, db, sid):
        for c in db.execute("SELECT * FROM ci_v3_charters WHERE session_id=? AND status!='stale'",(sid,)).fetchall():
            for rid in json.loads(c['sources']):
                row = db.execute('SELECT status FROM ci_v2_rounds WHERE id=?',(rid,)).fetchone()
                if not row or row[0]!='confirmed':
                    db.execute("UPDATE ci_v3_charters SET status='stale' WHERE id=?",(c['id'],))
                    break

    def charters(self, uid, sid):
        s = self.session(sid)
        self.authorize(uid,s['chat_id'])
        with self.o.db() as db:
            self.validate_charters(db,sid)
            return [dict(r) for r in db.execute('SELECT * FROM ci_v3_charters WHERE session_id=? ORDER BY version DESC',(sid,))]

    def approve_charter(self, uid, cid):
        with self.transaction() as db:
            c = db.execute('SELECT * FROM ci_v3_charters WHERE id=?',(cid,)).fetchone()
            if not c:
                raise ValueError('Charter tidak ditemukan.')
            s = self.session(c['session_id'])
            self.authorize(uid,s['chat_id'],'instructor')
            self.validate_charters(db,s['id'])
            c = db.execute('SELECT * FROM ci_v3_charters WHERE id=?',(cid,)).fetchone()
            if c['status']=='stale':
                raise ValueError('Bukti konsensus berubah; susun versi baru setelah konfirmasi ulang.')
            db.execute("UPDATE ci_v3_charters SET status='approved',approved_by=? WHERE id=?",(uid,cid))
            self.audit(db,uid,f'charter approved={cid}')

    def export_charter(self, uid, cid):
        with self.o.db() as db:
            row = db.execute('SELECT session_id FROM ci_v3_charters WHERE id=?',(cid,)).fetchone()
        if not row:
            raise ValueError('Charter tidak ditemukan.')
        c = next(r for r in self.charters(uid,row[0]) if r['id']==cid)
        body = json.loads(c['body'])
        lines = [f"# {c['title']}",f"Versi {c['version']} · status {c['status']} · {'SINTETIK' if self.session(row[0])['synthetic'] else 'DATA KELAS'}",'',
                 '## Tujuan',body['objective'],'','## Kebutuhan fungsional yang dikonfirmasi']
        lines += [f"- [R{r['round_id']} / U{r['proposal_id']}] {r['body']}" for r in body['confirmed_requirements']]
        labels = ['Rumusan masalah','Pengguna sasaran','Kebutuhan nonfungsional','Fitur AI','Model data','Kriteria penerimaan','Paket pekerjaan','Roadmap implementasi']
        lines += ['',body['editorial_status']]
        for k,label in zip(CHARTER_FIELDS,labels):
            lines += ['',f'## {label}',body['editorial'][k]]
        lines += ['','## Peran TISE']+[f'- {k}: {v}' for k,v in body['tise'].items()]
        lines += ['','## Legitimasi',f"Persetujuan dokumen oleh dosen: {'tercatat' if c['approved_by'] else 'belum'}. Persetujuan dokumen tidak menggantikan konsensus untuk bagian editorial.",LIMITATION]
        if c['status']=='stale':
            lines += ['','PERHATIAN: sumber konsensus tidak lagi valid. Dokumen ini bukan keputusan aktif.']
        return '\n'.join(lines)

    def erase_user(self, db, uid):
        db.execute('DELETE FROM ci_v3_surveys WHERE telegram_id=?',(uid,))
        db.execute('DELETE FROM ci_v3_snapshots')  # derived history may contain this actor as evidence
        db.execute('DELETE FROM ci_v3_charters WHERE author=? OR approved_by=?',(uid,uid))
        # Delete copied proposal text when the underlying confirmed source disappeared.
        for c in db.execute('SELECT id,sources FROM ci_v3_charters').fetchall():
            if any(not db.execute("SELECT 1 FROM ci_v2_rounds WHERE id=? AND status='confirmed'",(rid,)).fetchone() for rid in json.loads(c['sources'])):
                db.execute('DELETE FROM ci_v3_charters WHERE id=?',(c['id'],))

    def purge(self, db, cutoff):
        db.execute('DELETE FROM ci_v3_sessions WHERE ended IS NOT NULL AND ended<?',(cutoff,))
        db.execute('DELETE FROM ci_v3_snapshots WHERE captured<?',(cutoff,))
        db.execute('DELETE FROM ci_v3_surveys WHERE updated<?',(cutoff,))
        db.execute('DELETE FROM ci_v3_charters WHERE created<?',(cutoff,))
        for c in db.execute('SELECT id,sources FROM ci_v3_charters').fetchall():
            if any(not db.execute('SELECT 1 FROM ci_v2_rounds WHERE id=?',(rid,)).fetchone() for rid in json.loads(c['sources'])):
                db.execute('DELETE FROM ci_v3_charters WHERE id=?',(c['id'],))

    def command(self, uid, user, chat, chat_id, command, arg):
        try:
            self.authorize(uid,chat_id)
            if command=='/sesi' and arg.lower().startswith('mulai '):
                sid = self.start(uid,chat_id,arg[6:].strip())
                return f'Sesi laboratorium S{sid} dimulai. Gunakan /fase dan survei sukarela /survei pra 4,4,4,4 di chat pribadi.'
            sid = self.latest(chat_id)
            if not sid:
                return 'Belum ada sesi laboratorium. Fasilitator dapat /sesi mulai JUDUL.'
            s = self.session(sid)
            if command=='/sesi':
                if arg.lower()=='selesai':
                    self.close(uid,sid)
                    return f'Sesi S{sid} ditutup dan snapshot akhir disimpan.'
                return f"Sesi S{sid}: {s['title']} · fase {s['phase']} · {'selesai' if s['ended'] else 'aktif'}"
            if command=='/fase':
                if arg:
                    value = next((p for p in PHASES if p.casefold()==arg.casefold()),arg)
                    self.phase(uid,sid,value)
                return f"Fase sesi S{sid}: {self.session(sid)['phase']}"
            if command=='/survei':
                if chat['type']!='private':
                    return 'Isi survei sukarela hanya di chat pribadi: /survei pra 4,4,4,4 atau /survei pasca 4,4,4,4.'
                stage,_,scores = arg.partition(' ')
                self.survey(uid,sid,stage,[int(x) for x in scores.split(',')])
                return 'Survei tersimpan secara pribadi. Agregat ditampilkan setelah sedikitnya 5 responden.'
            if command in {'/modal_sosial','/perkembangan'}:
                m = self.metrics(sid)
                if command=='/modal_sosial':
                    social = m['social']
                    return (f"Modal sosial observasional S{sid}\nTimbal balik: {social['mutual_dyads']}/{social['dyads']} pasangan balasan.\n"
                            f"Bonding: {social['bonding_edges']} balasan dalam kelompok; bridging: {social['bridging_edges']} lintas kelompok; "
                            f"kelompok belum dipetakan: {social['group_unknown_edges']}. Linking: {social['linking_edges']} balasan mahasiswa–staf.\n"
                            'Bukan inferensi trust psikologis. Survei persepsi terpisah di dashboard.\n'+LIMITATION)
                timeline = self.timeline(uid,sid)
                value = 'belum cukup data' if m['index'] is None else f"{m['index']:.1f}/100"
                return f"Perkembangan S{sid}: {len(timeline)} snapshot; indeks saat ini {value}; cakupan bobot {m['coverage']:.0%}.\n"+LIMITATION
            if command=='/charter':
                if arg.lower().startswith('buat '):
                    cid = self.charter(uid,sid,arg[5:].strip())
                    return f'Draf charter C{cid} dibuat dari konsensus yang dikonfirmasi. Lengkapi bagian editorial melalui dashboard.'
                if arg.lower().startswith('setujui '):
                    if chat['type']!='private':
                        return 'Persetujuan charter oleh dosen dilakukan di chat pribadi.'
                    cid = self.o.facilitator.number(arg[8:].strip())
                    rows = self.charters(uid,sid)
                    if not any(r['id']==cid for r in rows):
                        return 'Charter tidak ditemukan pada sesi yang dipilih.'
                    self.approve_charter(uid,cid)
                    return f'Charter C{cid} disetujui dosen.'
                rows = self.charters(uid,sid)
                return self.export_charter(uid,rows[0]['id']) if rows else 'Belum ada charter. Fasilitator dapat /charter buat JUDUL setelah ada keputusan dikonfirmasi.'
        except (ValueError,PermissionError) as exc:
            return str(exc)
        return 'Perintah laboratorium: /sesi, /fase, /survei, /modal_sosial, /perkembangan, /charter.'
