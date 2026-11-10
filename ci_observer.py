"""Tahap 1 KIPP-CI: penyimpanan, analisis lokal, dan kontrol Forum Observer."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from contextlib import closing, contextmanager
from pathlib import Path

RUBRIC_VERSION = 'observer-1.0'
WEIGHTS = {'relevance': .15, 'knowledge': .20, 'empathy': .15,
           'integration': .20, 'facilitation': .15, 'action': .15}
OBJECTIVE = ('Merumuskan spesifikasi proyek UAS: aplikasi AI yang membantu '
             'fasilitator membangun Collective Intelligence dalam komunitas.')
NOTICE = '''KIPP-CI v3 — TISE Collective Intelligence Laboratory
Identitas memakai peserta.csv; tidak perlu mendaftar ulang.
Pesan/caption di grup yang dikonfigurasi dicatat hanya setelah /setuju di chat pribadi.
Teks, ID pesan, waktu, relasi balasan dan edit disimpan lokal untuk analisis kontribusi.
Ringkasan kelas memakai kutipan berpseudonim; asesmen pribadi hanya di chat pribadi.
Analisis memakai aturan lokal eksploratif, bukan nilai akademik atau ukuran karakter.
Tidak ada data yang dikirim ke LLM. Dosen menetapkan penilaian akhir.
/hapusdata menghapus pesan dan asesmen Anda serta menarik persetujuan.
/tarik menarik persetujuan; data lama tetap tersimpan sampai dihapus atau kedaluwarsa.

/setuju — setujui pencatatan versi observer-1
/gabung — tautan permintaan bergabung; juga dikirim setelah /setuju (pribadi)
/tujuan — tujuan kegiatan
/status — status forum
/request_fasilitator — minta giliran fasilitator
/unrequest_fasilitator — batalkan antrean sendiri
/selesai_fasilitator — lepas peran dan lanjutkan ke peserta berikutnya
/antrian_fasilitator — lihat fasilitator aktif dan antrean
/ringkasan — ringkasan ekstraktif pesan terbaru
/refleksi atau /profil — bukti dan umpan balik Anda (pribadi)
/rubrik — rubrik 6 dimensi
/tinjau ID_PESAN ALASAN — minta tinjauan dosen (pribadi)
/bukti ID_PESAN — lihat bukti/asesmen sendiri (pribadi; staf boleh semua)
Fasilitator/dosen: /analisis, /laporan, /pause, /resume
Dosen: /tinjauan, /koreksi ID_PESAN CATATAN (pribadi)
Untuk perintah pribadi, pilih grup: /forum ID_GRUP.

Versi 2:
/partisipasi, /konflik — indikator kolektif berbukti
/integrasi M1,M2 TEKS — hubungkan gagasan dari dua peserta
/usulan [TEKS] — buat atau lihat usulan formal
/konsensus [ID_PUTARAN], /keberatan — lacak konfirmasi dan keberatan
/sikap ID_PUTARAN setuju|abstain|keberatan [ALASAN]
Fasilitator: /sepakat ID_USULAN, /konfirmasi ID_PUTARAN, /bukaulang ID_PUTARAN
Di chat pribadi fasilitator: /intervensi, /terapkan ID [TEKS], /alternatif ID, /abaikan ID
Usulan, integrasi, dan alasan keberatan formal dapat dibaca peserta forum.
Saran lokal belum diposting sampai disetujui fasilitator.

Laboratorium TISE:
/sesi — status sesi; fasilitator: /sesi mulai JUDUL atau /sesi selesai
/fase [Target|Attention|Interest|Desire|Action]
/survei pra|pasca 4,4,4,4 — persepsi trust, didengar, aman, kerja sama (pribadi)
/modal_sosial, /perkembangan — indikator observasional dan riwayat CI
/charter — Project Charter UAS; fasilitator: /charter buat JUDUL
/dashboard — petunjuk dashboard
'''


class LocalAnalyzer:
    """Deterministic baseline. Evidence is observed syntax, not semantic judgement."""
    name = 'local-rules-v1'

    def analyze(self, row, context):
        text = row['text']
        low = text.casefold()
        acts = []
        if '?' in text:
            acts.append('question')
        if re.search(r'\b(usul|usulan|sebaiknya|bagaimana jika)\b', low):
            acts.append('proposal')
        if re.search(r'https?://', low):
            acts.append('evidence')
        if re.search(r'\b(karena|sebab|berdasarkan)\b', low):
            acts.append('argument')
        if re.search(r'\b(namun|keberatan|tidak setuju|tetapi)\b', low):
            acts.append('disagreement')
        if re.search(r'\b(gabungkan|menggabungkan|sintesis|merangkum)\b', low):
            acts.append('synthesis')
        if re.search(r'\b(pendapat lain|belum berbicara|bagaimana pendapat)\b', low):
            acts.append('facilitation')
        if re.search(r'\b(saya akan|kami akan|langkah berikut|tindak lanjut)\b', low):
            acts.append('commitment')
        if re.search(r'\b(saya belajar|saya menyadari|pandangan saya berubah)\b', low):
            acts.append('reflection')
        acts = acts or ['information']
        evidence = [row['id']]
        parent = next((r for r in context if r['telegram_message_id'] == row['reply_to']), None)
        if parent:
            evidence.append(parent['id'])
        signals = {
            'knowledge': ('evidence' in acts or 'argument' in acts,
                          'Ada tautan atau penanda alasan; kebenaran sumber belum diverifikasi.'),
            'empathy': (bool(re.search(r'\b(terima kasih|mohon|menghargai)\b', low)),
                        'Ada ungkapan penghargaan; bukan pengukuran empati psikologis.'),
            'integration': (bool(parent and 'synthesis' in acts),
                            'Penanda sintesis disertai balasan ke pesan yang tersedia.'),
            'facilitation': ('facilitation' in acts, 'Ada undangan eksplisit untuk perspektif lain.'),
            'action': ('commitment' in acts, 'Ada penanda rencana tindakan; pelaksanaan belum diverifikasi.')}
        dimensions = {}
        for dim in WEIGHTS:
            found, reason = signals.get(dim, (False, 'Relevansi terhadap tujuan memerlukan tinjauan manusia.'))
            dimensions[dim] = {
                'score': 2 if found else None,
                'status': 'observed' if found else 'not_observed',
                'explanation': reason if found or dim == 'relevance' else 'Tidak ada penanda aturan yang teramati; ini bukan kinerja buruk.',
                'evidence_message_ids': evidence if found else [],
                'improvement': 'Perjelas alasan, kaitan tujuan, atau bukti sesuai fungsi pesan.',
                'confidence': .35 if found else 0.0}
        return {'message_id': row['id'], 'speech_acts': acts, 'dimensions': dimensions,
                'evidence_message_ids': evidence, 'confidence': .35,
                'feedback': 'Indikator aturan lokal; perlu pembacaan konteks oleh dosen.',
                'rubric_version': RUBRIC_VERSION, 'model_name': self.name}


class Observer:
    def __init__(self, path, participants, *, chats=(), staff=(), instructors=(),
                 retention_days=90, analysis_seconds=600, summary_seconds=1200,
                 facilitator_options=None, laboratory_options=None):
        self.path, self.participants = Path(path), Path(participants)
        self.chats, self.staff, self.instructors = set(chats), set(staff) | set(instructors), set(instructors)
        self.retention_days = retention_days
        self.analysis_seconds, self.summary_seconds = analysis_seconds, summary_seconds
        self.analyzer = LocalAnalyzer()
        self._active_db = None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            # Additive migration: existing topics/posts/receipts remain intact.
            db.executescript('''
                CREATE TABLE IF NOT EXISTS ci_schema(version INTEGER PRIMARY KEY);
                INSERT OR IGNORE INTO ci_schema VALUES (1);
                CREATE TABLE IF NOT EXISTS ci_consent (
                    telegram_id INTEGER PRIMARY KEY, accepted INTEGER NOT NULL,
                    version TEXT NOT NULL, updated REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS ci_forums (
                    chat_id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                    objective TEXT NOT NULL, paused INTEGER NOT NULL DEFAULT 0,
                    last_analysis REAL NOT NULL DEFAULT 0,
                    last_summary REAL NOT NULL DEFAULT 0, summary_fingerprint TEXT);
                CREATE TABLE IF NOT EXISTS ci_messages (
                    id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL REFERENCES ci_forums(chat_id),
                    telegram_message_id INTEGER NOT NULL, telegram_id INTEGER NOT NULL,
                    nim TEXT NOT NULL, timestamp REAL NOT NULL, text TEXT NOT NULL,
                    reply_to INTEGER, thread_id INTEGER, edited_at REAL, revision TEXT NOT NULL,
                    UNIQUE(chat_id, telegram_message_id));
                CREATE INDEX IF NOT EXISTS ci_message_forum ON ci_messages(chat_id, timestamp);
                CREATE INDEX IF NOT EXISTS ci_message_user ON ci_messages(telegram_id);
                CREATE TABLE IF NOT EXISTS ci_assessments (
                    message_id INTEGER PRIMARY KEY REFERENCES ci_messages(id) ON DELETE CASCADE,
                    revision TEXT NOT NULL, result TEXT NOT NULL, assessed REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS ci_updates(update_id INTEGER PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS ci_command_results (
                    update_id INTEGER PRIMARY KEY, telegram_id INTEGER NOT NULL,
                    response TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS ci_selection(telegram_id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS ci_reviews (
                    id INTEGER PRIMARY KEY, message_id INTEGER NOT NULL REFERENCES ci_messages(id) ON DELETE CASCADE,
                    telegram_id INTEGER NOT NULL, kind TEXT NOT NULL, note TEXT NOT NULL,
                    created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS ci_audit (
                    id INTEGER PRIMARY KEY, actor INTEGER, event TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS ci_facilitators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL REFERENCES ci_forums(chat_id),
                    telegram_id INTEGER NOT NULL, status TEXT NOT NULL
                    CHECK(status IN ('waiting','active','done','cancelled')),
                    requested REAL NOT NULL, finished REAL);
                CREATE UNIQUE INDEX IF NOT EXISTS ci_facilitator_pending
                    ON ci_facilitators(chat_id,telegram_id) WHERE status IN ('waiting','active');
                CREATE UNIQUE INDEX IF NOT EXISTS ci_facilitator_active
                    ON ci_facilitators(chat_id) WHERE status='active';
                INSERT OR IGNORE INTO ci_schema VALUES (2);
            ''')
        from ci_facilitator import IntelligentFacilitator
        self.facilitator = IntelligentFacilitator(self, **(facilitator_options or {}))
        from ci_lab import Laboratory
        self.lab = Laboratory(self, **(laboratory_options or {}))

    @contextmanager
    def db(self):
        if self._active_db is not None:
            yield self._active_db
            return
        with closing(sqlite3.connect(self.path, timeout=30)) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('PRAGMA secure_delete=ON')
            with db:
                yield db

    def identity(self, telegram_id):
        # Lazy import avoids a dependency cycle with the ci.py entry point.
        from ci import participant
        user = participant(self.participants, telegram_id)
        if user:
            return user
        if telegram_id in self.staff:
            return {'NIM': 'staff:' + str(telegram_id), 'Nama': 'Fasilitator'}
        return None

    def roster(self):
        import csv
        with self.participants.open(encoding='utf-8-sig', newline='') as source:
            return list(csv.DictReader(source))

    def consent(self, telegram_id):
        with self.db() as db:
            row = db.execute('SELECT accepted FROM ci_consent WHERE telegram_id=?', (telegram_id,)).fetchone()
        return bool(row and row[0])

    def select_forum(self, telegram_id, chat):
        if chat['type'] != 'private':
            return chat['id'] if chat['id'] in self.chats else None
        with self.db() as db:
            row = db.execute('SELECT chat_id FROM ci_selection WHERE telegram_id=?', (telegram_id,)).fetchone()
        if row and row[0] in self.chats:
            return row[0]
        return next(iter(self.chats)) if len(self.chats) == 1 else None

    def handle(self, update):
        """Return responses; ordinary group messages are silently observed."""
        message = update.get('message') or update.get('edited_message') or {}
        chat, sender = message.get('chat', {}), message.get('from', {})
        uid, chat_id = sender.get('id'), chat.get('id')
        if not isinstance(uid, int) or not isinstance(chat_id, int) or sender.get('is_bot') or message.get('sender_chat'):
            return []
        private = chat.get('type') == 'private'
        if not private and (chat_id not in self.chats or chat.get('type') not in {'group', 'supergroup'}):
            return []
        user = self.identity(uid)
        if not user:
            return [(chat_id, 'Akun Telegram ini belum terhubung di peserta.csv. Hubungi dosen untuk koreksi data.')] if private else []
        text = message.get('text') or message.get('caption') or ''
        if not isinstance(text, str):
            return []
        if not private:
            with self.db() as db:
                db.execute('INSERT OR IGNORE INTO ci_forums(chat_id,title,objective) VALUES (?,?,?)',
                           (chat_id, chat.get('title', 'Forum CI'), OBJECTIVE))
        # Edits never re-execute commands. An edit into a command removes an
        # earlier recorded text, so stale content cannot remain as evidence.
        if 'edited_message' in update:
            self.ingest(update, message, user, command=text.startswith('/'))
            return []
        if text.startswith('/'):
            command, _, arg = text.strip().partition(' ')
            command = command.split('@')[0].lower()
            mutations = {'/setuju', '/tarik', '/hapusdata', '/forum', '/pause', '/resume', '/tinjau', '/koreksi',
                         '/request_fasilitator', '/unrequest_fasilitator', '/selesai_fasilitator',
                         '/request', '/unrequest', '/integrasi', '/usulan', '/sepakat', '/sikap',
                         '/konfirmasi', '/bukaulang', '/intervensi', '/terapkan', '/abaikan', '/alternatif',
                         '/sesi', '/fase', '/survei', '/charter'}
            if command in mutations and isinstance(update.get('update_id'), int):
                # Commit command side effects and retry receipt atomically.
                with self.db() as db:
                    db.execute('BEGIN IMMEDIATE')
                    cached = db.execute('SELECT response FROM ci_command_results WHERE update_id=?', (update['update_id'],)).fetchone()
                    if cached:
                        return [(chat_id, cached[0])]
                    self._active_db = db
                    try:
                        response = self.command(uid, user, chat, command, arg.strip())
                        db.execute('INSERT INTO ci_command_results VALUES (?,?,?,?)', (update['update_id'], uid, response, time.time()))
                    finally:
                        self._active_db = None
                return [(chat_id, response)]
            return [(chat_id, self.command(uid, user, chat, command, arg.strip()))]
        if not private:
            self.ingest(update, message, user)
        return []

    def ingest(self, update, message, user, command=False):
        chat_id, uid = message['chat']['id'], message['from']['id']
        if chat_id not in self.chats or not isinstance(message.get('message_id'), int):
            return
        with self.db() as db:
            if not self.consent(uid):
                return
            consent_time = db.execute('SELECT updated FROM ci_consent WHERE telegram_id=?', (uid,)).fetchone()[0]
            if message.get('date', 0) < int(consent_time):
                return  # Do not retroactively collect a backlog from before consent.
            forum = db.execute('SELECT paused FROM ci_forums WHERE chat_id=?', (chat_id,)).fetchone()
            if not forum or forum[0]:
                return
            update_id = update.get('update_id')
            if not isinstance(update_id, int):
                return
            if db.execute('SELECT 1 FROM ci_updates WHERE update_id=?', (update_id,)).fetchone():
                return
            text = message.get('text') or message.get('caption') or ''
            stamp = message.get('edit_date', message.get('date', 0))
            old = db.execute('SELECT * FROM ci_messages WHERE chat_id=? AND telegram_message_id=?',
                             (chat_id, message['message_id'])).fetchone()
            if old and stamp < (old['edited_at'] or old['timestamp']):
                return
            if old and command:
                db.execute('DELETE FROM ci_messages WHERE id=?', (old['id'],))
                db.execute('DELETE FROM ci_assessments WHERE message_id IN (SELECT id FROM ci_messages WHERE chat_id=?)', (chat_id,))
            elif text:
                revision = hashlib.sha256(text.encode()).hexdigest()
                if old and revision != old['revision']:
                    # Invalidate the forum context, including assessments of replies.
                    db.execute('DELETE FROM ci_assessments WHERE message_id IN (SELECT id FROM ci_messages WHERE chat_id=?)', (chat_id,))
                elif not old:
                    # An out-of-order parent can change a previously seen reply.
                    db.execute('DELETE FROM ci_assessments WHERE message_id IN (SELECT id FROM ci_messages WHERE chat_id=? AND reply_to=?)',
                               (chat_id, message['message_id']))
                db.execute('''INSERT INTO ci_messages(chat_id,telegram_message_id,telegram_id,nim,timestamp,
                    text,reply_to,thread_id,edited_at,revision) VALUES (?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(chat_id,telegram_message_id) DO UPDATE SET
                    text=excluded.text,reply_to=excluded.reply_to,thread_id=excluded.thread_id,
                    edited_at=excluded.edited_at,revision=excluded.revision''',
                    (chat_id, message['message_id'], uid, user['NIM'], message.get('date', time.time()), text,
                     message.get('reply_to_message', {}).get('message_id'), message.get('message_thread_id'),
                     message.get('edit_date'), revision))
            elif old:
                db.execute('DELETE FROM ci_messages WHERE id=?', (old['id'],))
                db.execute('DELETE FROM ci_assessments WHERE message_id IN (SELECT id FROM ci_messages WHERE chat_id=?)', (chat_id,))
            db.execute('INSERT INTO ci_updates VALUES (?)', (update_id,))

    def analyze(self, chat_id):
        if self.state(chat_id)['paused']:
            return 0
        processed = 0
        with self.db() as db:
            rows = db.execute('SELECT * FROM ci_messages WHERE chat_id=? ORDER BY timestamp,id', (chat_id,)).fetchall()
            for row in rows:
                cached = db.execute('SELECT revision FROM ci_assessments WHERE message_id=?', (row['id'],)).fetchone()
                if cached and cached[0] == row['revision']:
                    continue
                result = self.analyzer.analyze(row, rows)
                db.execute('INSERT OR REPLACE INTO ci_assessments VALUES (?,?,?,?)',
                           (row['id'], row['revision'], json.dumps(result, ensure_ascii=False), time.time()))
                processed += 1
            db.execute('UPDATE ci_forums SET last_analysis=? WHERE chat_id=?', (time.time(), chat_id))
        self.facilitator.propose_interventions(chat_id)
        sid = self.lab.latest(chat_id)
        if sid is not None and self.lab.session(sid)['ended'] is None:
            self.lab.capture(sid)
        return processed

    def state(self, chat_id):
        with self.db() as db:
            rows = db.execute('SELECT * FROM ci_messages WHERE chat_id=? ORDER BY timestamp,id', (chat_id,)).fetchall()
            forum = db.execute('SELECT * FROM ci_forums WHERE chat_id=?', (chat_id,)).fetchone()
        counts = {}
        for row in rows:
            counts[row['nim']] = counts.get(row['nim'], 0) + 1
        roster = {r['NIM'] for r in self.roster()}
        active = roster & set(counts)
        return {'rows': rows, 'counts': counts, 'active': len(active), 'total': len(roster),
                'silent': sorted(roster - active), 'paused': bool(forum and forum['paused'])}

    def report(self, chat_id, summary=False):
        state = self.state(chat_id)
        rows = state['rows']
        result = (f"Forum Observer — {'DIJEDA' if state['paused'] else 'AKTIF'}\n"
                  f"Tujuan: {OBJECTIVE}\n{len(rows)} pesan tercatat; "
                  f"{state['active']}/{state['total']} mahasiswa berkontribusi dalam data tercatat.\n"
                  f"{len(state['silent'])} mahasiswa belum teramati; bukan bukti tidak berpartisipasi.\n")
        if summary:
            # Extractive, attributed snippets; never infer consensus from frequency.
            result += '\nRingkasan ekstraktif lokal — hingga 12 pesan terakhir:\n'
            if not rows:
                result += 'Belum ada pesan yang dapat diringkas.\n'
            aliases = {nim: f'P{i+1}' for i, nim in enumerate(sorted(state['counts']))}
            for r in rows[-12:]:
                result += f"[M{r['id']}] {aliases[r['nim']]}: {r['text'][:240]}\n"
            result += '\nKutipan dapat terpotong. Belum memvalidasi bukti, menyelesaikan keberatan, atau mengonfirmasi konsensus.'
        with self.db() as db:
            assessments = db.execute('SELECT a.result FROM ci_assessments a JOIN ci_messages m ON m.id=a.message_id WHERE m.chat_id=?', (chat_id,)).fetchall()
        acts = {}
        for assessment in assessments:
            for act in json.loads(assessment[0])['speech_acts']:
                acts[act] = acts.get(act, 0) + 1
        if assessments:
            result += f'\nAnalisis lokal tersedia: {len(assessments)}/{len(rows)} pesan. Penanda kontribusi: ' + ', '.join(f'{a}={n}' for a,n in sorted(acts.items())) + '.'
        if rows:
            largest_share = max(state['counts'].values()) / len(rows)
            result += f'\nPorsi pesan terbesar dari satu kontributor: {largest_share:.0%} (indikator volume, bukan kualitas).'
        result += '\nIndikator eksploratif berbasis data yang tersedia, bukan nilai akademik.'
        return result + '\n\n' + self.facilitator.report(chat_id)

    def reflection(self, chat_id, uid):
        self.analyze(chat_id)
        with self.db() as db:
            rows = db.execute('''SELECT m.id,m.text,a.result FROM ci_messages m JOIN ci_assessments a
                ON m.id=a.message_id WHERE m.chat_id=? AND m.telegram_id=? ORDER BY m.timestamp,m.id''', (chat_id, uid)).fetchall()
            reviews = db.execute('''SELECT r.*,m.id evidence FROM ci_reviews r JOIN ci_messages m ON m.id=r.message_id
                WHERE m.chat_id=? AND m.telegram_id=? ORDER BY r.id DESC LIMIT 5''', (chat_id, uid)).fetchall()
        output = f'Refleksi pribadi — {len(rows)} kontribusi tercatat\nMetode: {self.analyzer.name}, rubrik {RUBRIC_VERSION}.\n'
        output += 'Tidak ada rata-rata nilai atau kesimpulan karakter. Skor 2 menandai indikator awal teramati; dimensi lain belum teramati.\n'
        for row in rows[-10:]:
            a = json.loads(row['result'])
            signals = ', '.join(f'{dim}=2/4' for dim, v in a['dimensions'].items() if v['score'] is not None) or 'semua dimensi not_observed'
            output += f"\n[M{row['id']}] {row['text'][:180]}\n{', '.join(a['speech_acts'])}; {signals}; keyakinan rendah 0,35.\n"
            for dim, value in a['dimensions'].items():
                if value['score'] is not None:
                    output += f"{dim}: {value['explanation']} Bukti {value['evidence_message_ids']}.\n"
        for review in reviews:
            output += f"\nTinjauan M{review['evidence']} ({review['kind']}): {review['note']}\n"
        return output + '\nSaran: hubungkan gagasan dengan tujuan, alasan, sumber, dan perspektif peserta lain sesuai konteks. Minta tinjauan: /tinjau ID_PESAN ALASAN.'

    def refresh_facilitators(self, db, chat_id):
        """Drop unavailable identities and promote the earliest waiting student."""
        students = {r['ID'].strip(): r['Nama'] for r in self.roster() if r.get('ID', '').strip()}
        rows = db.execute("SELECT * FROM ci_facilitators WHERE chat_id=? AND status IN ('active','waiting') ORDER BY id", (chat_id,)).fetchall()
        for row in rows:
            if str(row['telegram_id']) not in students:
                db.execute("UPDATE ci_facilitators SET status='cancelled',finished=? WHERE id=?", (time.time(), row['id']))
        if not db.execute("SELECT 1 FROM ci_facilitators WHERE chat_id=? AND status='active'", (chat_id,)).fetchone():
            first = db.execute("SELECT id FROM ci_facilitators WHERE chat_id=? AND status='waiting' ORDER BY id LIMIT 1", (chat_id,)).fetchone()
            if first:
                db.execute("UPDATE ci_facilitators SET status='active' WHERE id=?", (first[0],))
        return students

    def is_facilitator(self, uid, chat_id):
        if uid in self.staff:
            return True
        with self.db() as db:
            self.refresh_facilitators(db, chat_id)
            return bool(db.execute("SELECT 1 FROM ci_facilitators WHERE chat_id=? AND telegram_id=? AND status='active'", (chat_id, uid)).fetchone())

    def facilitator_command(self, uid, chat_id, command, arg):
        if arg:
            return f'Gunakan {command} tanpa argumen; perintah hanya berlaku untuk diri sendiri.'
        with self.db() as db:
            # Also serialize queue reads that may clean up removed participants.
            if self._active_db is None:
                db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR IGNORE INTO ci_forums(chat_id,title,objective) VALUES (?,?,?)', (chat_id, 'Forum CI', OBJECTIVE))
            students = self.refresh_facilitators(db, chat_id)
            current = db.execute("SELECT * FROM ci_facilitators WHERE chat_id=? AND telegram_id=? AND status IN ('active','waiting')", (chat_id, uid)).fetchone()
            note = ''
            if command != '/antrian_fasilitator' and str(uid) not in students:
                return 'Antrean ini khusus mahasiswa yang terdaftar di peserta.csv.'
            if command == '/request_fasilitator':
                if current:
                    note = 'Anda sudah menjadi fasilitator aktif.' if current['status'] == 'active' else 'Anda sudah berada dalam antrean; posisi tetap.'
                else:
                    db.execute("INSERT INTO ci_facilitators(chat_id,telegram_id,status,requested) VALUES (?,?,'waiting',?)", (chat_id, uid, time.time()))
                    note = 'Permintaan giliran Anda dicatat.'
            elif command == '/unrequest_fasilitator':
                if current and current['status'] == 'active':
                    note = 'Anda sedang bertugas. Gunakan /selesai_fasilitator untuk melepas peran.'
                elif current:
                    db.execute("UPDATE ci_facilitators SET status='cancelled',finished=? WHERE id=?", (time.time(), current['id']))
                    note = 'Permintaan Anda dibatalkan.'
                else:
                    note = 'Anda tidak sedang mengantre.'
            elif command == '/selesai_fasilitator':
                if current and current['status'] == 'active':
                    db.execute("UPDATE ci_facilitators SET status='done',finished=? WHERE id=?", (time.time(), current['id']))
                    note = 'Tugas fasilitator Anda selesai; peran giliran dilepas.'
                else:
                    note = 'Anda bukan fasilitator aktif. Untuk membatalkan antrean gunakan /unrequest_fasilitator.'
            students = self.refresh_facilitators(db, chat_id)
            active = db.execute("SELECT telegram_id FROM ci_facilitators WHERE chat_id=? AND status='active'", (chat_id,)).fetchone()
            waiting = db.execute("SELECT telegram_id FROM ci_facilitators WHERE chat_id=? AND status='waiting' ORDER BY id", (chat_id,)).fetchall()
            if command != '/antrian_fasilitator':
                db.execute('INSERT INTO ci_audit(actor,event,created) VALUES (?,?,?)', (uid, f'{command} forum={chat_id}', time.time()))
            output = f'Antrean fasilitator — forum {chat_id}\nAktif: ' + (students[str(active[0])] if active else 'belum ada')
            output += '\nMenunggu:\n' + ('\n'.join(f'{i}. {students[str(row[0])]}'+(' (Anda)' if row[0] == uid else '') for i,row in enumerate(waiting, 1)) or 'Tidak ada antrean.')
            output += '\nGiliran otomatis sesuai urutan permintaan. Fasilitator aktif: /selesai_fasilitator.'
            return (note + '\n\n' if note else '') + output

    def command(self, uid, user, chat, command, arg):
        private = chat['type'] == 'private'
        if command in {'/start', '/help', '/bantuan'}:
            return f"Selamat datang, {user['Nama']}!\n{NOTICE}"
        if command in {'/setuju', '/tarik', '/hapusdata'}:
            if not private:
                return 'Gunakan perintah persetujuan di chat pribadi dengan bot.'
            with self.db() as db:
                db.execute('INSERT OR REPLACE INTO ci_consent VALUES (?,?,?,?)',
                           (uid, int(command == '/setuju'), 'observer-1', time.time()))
                if command == '/hapusdata':
                    db.execute('DELETE FROM ci_messages WHERE telegram_id=?', (uid,))
                    db.execute('DELETE FROM ci_assessments')  # remove cross-message evidence too
                    db.execute('DELETE FROM ci_command_results WHERE telegram_id=?', (uid,))
                    forums = db.execute('SELECT DISTINCT chat_id FROM ci_facilitators WHERE telegram_id=?', (uid,)).fetchall()
                    db.execute('DELETE FROM ci_facilitators WHERE telegram_id=?', (uid,))
                    for forum in forums:
                        self.refresh_facilitators(db, forum[0])
                    self.facilitator.erase_user(db, uid)
                    self.lab.erase_user(db, uid)
                db.execute('INSERT INTO ci_audit(actor,event,created) VALUES (?,?,?)', (uid, command, time.time()))
            return 'Persetujuan dicatat. Pesan berikutnya dapat diamati.' if command == '/setuju' else 'Persetujuan ditarik.' + (' Pesan dan asesmen Anda dihapus.' if command == '/hapusdata' else '')
        if command == '/tujuan':
            return OBJECTIVE
        if command == '/dashboard':
            return 'Jalankan dashboard laboratorium: .venv/bin/python -m streamlit run ci_dashboard.py --server.address 127.0.0.1\nMode demo menggunakan data sintetik. Mode kelas memerlukan autentikasi OIDC; lihat manuals/ci-v3-manual.md.'
        if command == '/rubrik':
            return ('Rubrik ' + RUBRIC_VERSION + '\n' + '\n'.join(f'{k}: {v:.0%}' for k,v in WEIGHTS.items()) +
                    '\nSkala 0–4. Tahap 1 hanya memberi 2 pada penanda awal teramati atau null/not_observed. '
                    'not_applicable dan poor_performance memerlukan tinjauan manusia; tidak otomatis disimpulkan. '
                    'Tidak dijumlahkan menjadi nilai akademik. Setiap indikator menyimpan alasan, bukti, saran dan confidence.')
        if command == '/forum' and private:
            try:
                target = int(arg)
            except ValueError:
                return 'Gunakan /forum ID_GRUP.'
            if target not in self.chats:
                return 'Forum tidak diizinkan oleh konfigurasi.'
            with self.db() as db:
                db.execute('INSERT OR REPLACE INTO ci_selection VALUES (?,?)', (uid, target))
            return f'Forum aktif Anda: {target}.'
        chat_id = self.select_forum(uid, chat)
        if command == '/status' and not chat_id:
            return f"Terdaftar: {user['Nama']} ({user['NIM']}). Tidak perlu registrasi ulang.\nBelum ada forum terpilih; konfigurasikan CI_CHAT_IDS atau /forum ID_GRUP."
        if not chat_id:
            return 'Pilih forum: /forum ID_GRUP. Operator perlu mengisi CI_CHAT_IDS.'
        command = {'/request': '/request_fasilitator', '/unrequest': '/unrequest_fasilitator'}.get(command, command)
        if command in {'/request_fasilitator', '/unrequest_fasilitator', '/selesai_fasilitator', '/antrian_fasilitator'}:
            return self.facilitator_command(uid, chat_id, command, arg)
        if command in {'/sesi','/fase','/survei','/modal_sosial','/perkembangan','/charter'}:
            return self.lab.command(uid,user,chat,chat_id,command,arg)
        if command in {'/partisipasi','/konflik','/integrasi','/usulan','/sepakat','/sikap','/konfirmasi',
                       '/bukaulang','/konsensus','/keberatan','/intervensi','/terapkan','/abaikan','/alternatif'}:
            if command == '/sikap' or (command in {'/usulan','/integrasi'} and arg):
                if not self.consent(uid):
                    return 'Baca /start lalu /setuju di chat pribadi sebelum menyimpan kontribusi formal.'
            result = self.facilitator.command(uid, user, chat, chat_id, command, arg)
            with self.db() as db:
                db.execute('INSERT INTO ci_audit(actor,event,created) VALUES (?,?,?)', (uid, f'{command} forum={chat_id}', time.time()))
            return result
        if command in {'/refleksi', '/profil', '/tinjau', '/koreksi', '/bukti', '/tinjauan'} and not private:
            return 'Asesmen dan tinjauan hanya tersedia di chat pribadi dengan bot.'
        if command in {'/pause', '/resume', '/analisis', '/laporan'} and not self.is_facilitator(uid, chat_id):
            return 'Perintah ini khusus fasilitator aktif atau staf/dosen yang dikonfigurasi.'
        if command in {'/pause', '/resume'}:
            with self.db() as db:
                db.execute('INSERT OR IGNORE INTO ci_forums(chat_id,title,objective) VALUES (?,?,?)', (chat_id, 'Forum CI', OBJECTIVE))
                db.execute('UPDATE ci_forums SET paused=? WHERE chat_id=?', (int(command == '/pause'), chat_id))
                db.execute('INSERT INTO ci_audit(actor,event,created) VALUES (?,?,?)', (uid, command, time.time()))
            return 'Pencatatan dan analisis dijeda.' if command == '/pause' else 'Pencatatan dan analisis dilanjutkan; pesan selama jeda tidak diambil ulang.'
        if command == '/status':
            return self.report(chat_id)
        if command == '/ringkasan':
            return self.report(chat_id, summary=True)
        if self.state(chat_id)['paused']:
            return 'Forum dijeda. Analisis dan asesmen baru dihentikan sampai /resume.'
        if command in {'/analisis', '/laporan'}:
            processed = self.analyze(chat_id)
            result = f'{processed} pesan dianalisis ulang.\n' + self.report(chat_id, summary=True)
            if private:
                result += '\nNIM belum teramati: ' + ', '.join(self.state(chat_id)['silent'])
            return result
        if command in {'/refleksi', '/profil'}:
            return self.reflection(chat_id, uid)
        if command == '/tinjauan':
            if uid not in self.instructors:
                return 'Daftar tinjauan khusus dosen.'
            with self.db() as db:
                reviews = db.execute('''SELECT r.*,m.nim FROM ci_reviews r JOIN ci_messages m ON m.id=r.message_id
                    WHERE m.chat_id=? ORDER BY r.id DESC LIMIT 20''', (chat_id,)).fetchall()
            return 'Tinjauan terbaru (maksimal 20):\n' + ('\n'.join(f"M{r['message_id']} NIM {r['nim']} [{r['kind']}]: {r['note']}" for r in reviews) or 'Belum ada catatan.')
        if command == '/bukti':
            if not arg.isdigit() or len(arg) > 9:
                return 'Gunakan /bukti ID_PESAN.'
            with self.db() as db:
                row = db.execute('SELECT * FROM ci_messages WHERE id=? AND chat_id=?', (int(arg), chat_id)).fetchone()
            if not row or (row['telegram_id'] != uid and uid not in self.staff):
                return 'Bukti tidak ditemukan atau akses tidak diizinkan.'
            self.analyze(chat_id)
            with self.db() as db:
                result = db.execute('SELECT result FROM ci_assessments WHERE message_id=?', (row['id'],)).fetchone()[0]
            return f"Bukti M{row['id']} — NIM {row['nim']}\n{row['text']}\n\n" + json.dumps(json.loads(result), ensure_ascii=False, indent=2)
        if command in {'/tinjau', '/koreksi'}:
            if command == '/koreksi' and uid not in self.instructors:
                return 'Koreksi khusus dosen yang dikonfigurasi.'
            parts = arg.split(maxsplit=1)
            if len(parts) != 2 or not parts[0].isdigit() or len(parts[0]) > 9 or len(parts[1]) > 2000:
                return f'Gunakan {command} ID_PESAN CATATAN (maksimal 2.000 karakter).'
            with self.db() as db:
                row = db.execute('SELECT * FROM ci_messages WHERE id=? AND chat_id=?', (int(parts[0]), chat_id)).fetchone()
                if not row or (command == '/tinjau' and row['telegram_id'] != uid):
                    return 'Bukti tidak ditemukan atau bukan milik Anda.'
                db.execute('INSERT INTO ci_reviews(message_id,telegram_id,kind,note,created) VALUES (?,?,?,?,?)',
                           (row['id'], uid, 'koreksi dosen' if command == '/koreksi' else 'permintaan tinjauan', parts[1], time.time()))
            return 'Catatan tinjauan tersimpan. Koreksi dosen ditampilkan bersama asesmen; keluaran aturan asli tetap dapat diaudit.'
        return 'Perintah tahap ini tersedia melalui /help. Percakapan dicatat dari teks biasa di grup yang diizinkan.'

    def tick(self, now=None):
        """Local periodic analysis; summaries post only when source data changes."""
        now = time.time() if now is None else now
        self.purge(now)
        outgoing = []
        with self.db() as db:
            forums = db.execute('SELECT * FROM ci_forums WHERE paused=0').fetchall()
        for forum in forums:
            cid = forum['chat_id']
            if cid not in self.chats:
                continue
            if now - forum['last_analysis'] >= self.analysis_seconds:
                self.analyze(cid)
            if now - forum['last_summary'] >= self.summary_seconds:
                rows = self.state(cid)['rows']
                fingerprint = hashlib.sha256(json.dumps([(r['id'], r['revision']) for r in rows]).encode()).hexdigest()
                if rows and fingerprint != forum['summary_fingerprint']:
                    outgoing.append((cid, self.report(cid, summary=True), fingerprint, now))
        return outgoing

    def mark_summary(self, chat_id, fingerprint, now):
        with self.db() as db:
            db.execute('UPDATE ci_forums SET last_summary=?,summary_fingerprint=? WHERE chat_id=?', (now, fingerprint, chat_id))

    def purge(self, now=None):
        cutoff = (time.time() if now is None else now) - self.retention_days * 86400
        with self.db() as db:
            expired = db.execute('SELECT 1 FROM ci_messages WHERE timestamp<? LIMIT 1', (cutoff,)).fetchone()
            if expired:
                db.execute('DELETE FROM ci_messages WHERE timestamp<?', (cutoff,))
                db.execute('DELETE FROM ci_assessments')
            db.execute('DELETE FROM ci_audit WHERE created<?', (cutoff,))
            db.execute('DELETE FROM ci_command_results WHERE created<?', (cutoff,))
            db.execute("DELETE FROM ci_facilitators WHERE status IN ('done','cancelled') AND finished<?", (cutoff,))
            self.facilitator.purge(db, cutoff)
            self.lab.purge(db, cutoff)
