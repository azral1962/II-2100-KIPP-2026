"""KIPP-CI v2: fasilitasi berbukti dan konsensus dengan konfirmasi manusia.

Deteksi lokal bersifat indikatif. Tidak menyimpulkan emosi, kepercayaan, atau
konsensus dari banyaknya pesan maupun kemiripan pendapat.
"""
import hashlib
import json
import re
import time


QUESTIONS = {
    'participation_gap': ('Sebagian perspektif belum teramati dalam data.',
        ['Perspektif siapa yang belum terwakili, dan bagaimana memberi ruang tanpa memaksa?',
         'Bisakah kita memberi waktu berpikir lalu mengundang masukan tertulis dari yang bersedia?']),
    'concentration': ('Volume percakapan terkonsentrasi pada sedikit kontributor.',
        ['Apakah kita dapat memberi giliran kepada peserta yang ingin menambahkan perspektif lain?',
         'Bisakah tiap peserta yang bersedia menyampaikan satu kebutuhan sebelum tanggapan lanjutan?']),
    'disagreement': ('Ada penanda perbedaan pendapat; belum tentu konflik interpersonal.',
        ['Apa alasan dan kebutuhan di balik perbedaan ini, dan bukti apa yang bisa kita periksa bersama?',
         'Bisakah kedua perspektif dirumuskan ulang secara adil sebelum membandingkan alternatif?']),
    'integration_gap': ('Ada usulan dan tanggapan lintas peserta, tetapi integrasi eksplisit belum teramati.',
        ['Bagian mana dari dua usulan yang dapat digabungkan? Sebutkan pesan sumber dan komprominya.',
         'Bisakah seseorang menyusun alternatif ketiga yang mempertahankan kebutuhan dari kedua gagasan?']),
    'open_objection': ('Konfirmasi keputusan masih memiliki keberatan yang dicatat peserta.',
        ['Perubahan apa yang diperlukan untuk menjawab keberatan ini? Pemilik keberatan dapat memperbarui sikapnya sendiri.',
         'Mari dengarkan alasan keberatan dan rumuskan alternatif yang dapat diperiksa seluruh peserta.'])}


class IntelligentFacilitator:
    def __init__(self, observer, *, min_messages=6, dominance_share=.45,
                 active_ratio=.60, cooldown_seconds=1200):
        self.o = observer
        self.min_messages, self.dominance_share = min_messages, dominance_share
        self.active_ratio, self.cooldown_seconds = active_ratio, cooldown_seconds
        with self.o.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS ci_v2_proposals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL REFERENCES ci_forums(chat_id),
                    author INTEGER NOT NULL, body TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS ci_v2_rounds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, proposal INTEGER NOT NULL REFERENCES ci_v2_proposals(id) ON DELETE CASCADE,
                    status TEXT NOT NULL CHECK(status IN ('open','confirmed','superseded')),
                    created REAL NOT NULL, confirmed_by INTEGER, confirmed_at REAL);
                CREATE UNIQUE INDEX IF NOT EXISTS ci_v2_current_round ON ci_v2_rounds(proposal) WHERE status IN ('open','confirmed');
                CREATE TABLE IF NOT EXISTS ci_v2_electorate (
                    round_id INTEGER NOT NULL REFERENCES ci_v2_rounds(id) ON DELETE CASCADE,
                    nim TEXT NOT NULL, telegram_id TEXT NOT NULL, PRIMARY KEY(round_id,nim));
                CREATE TABLE IF NOT EXISTS ci_v2_ballots (
                    round_id INTEGER NOT NULL, nim TEXT NOT NULL, stance TEXT NOT NULL
                    CHECK(stance IN ('setuju','abstain','keberatan')), reason TEXT NOT NULL, updated REAL NOT NULL,
                    PRIMARY KEY(round_id,nim), FOREIGN KEY(round_id,nim) REFERENCES ci_v2_electorate(round_id,nim) ON DELETE CASCADE);
                CREATE TABLE IF NOT EXISTS ci_v2_ballot_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, round_id INTEGER NOT NULL, nim TEXT NOT NULL,
                    stance TEXT NOT NULL, reason TEXT NOT NULL, updated REAL NOT NULL,
                    FOREIGN KEY(round_id,nim) REFERENCES ci_v2_electorate(round_id,nim) ON DELETE CASCADE);
                CREATE TABLE IF NOT EXISTS ci_v2_integrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL REFERENCES ci_forums(chat_id),
                    author INTEGER NOT NULL, body TEXT NOT NULL, created REAL NOT NULL,
                    source_count INTEGER NOT NULL DEFAULT 2);
                CREATE TABLE IF NOT EXISTS ci_v2_sources (
                    integration INTEGER NOT NULL REFERENCES ci_v2_integrations(id) ON DELETE CASCADE,
                    message_id INTEGER NOT NULL REFERENCES ci_messages(id) ON DELETE CASCADE,
                    revision TEXT NOT NULL, PRIMARY KEY(integration,message_id));
                CREATE TABLE IF NOT EXISTS ci_v2_interventions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL REFERENCES ci_forums(chat_id),
                    trigger TEXT NOT NULL, fingerprint TEXT NOT NULL, diagnosis TEXT NOT NULL,
                    question TEXT NOT NULL, sources TEXT NOT NULL, created REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','ignored','posted','stale')),
                    variant INTEGER NOT NULL DEFAULT 0, decided_by INTEGER, posted_at REAL,
                    UNIQUE(chat_id,trigger,fingerprint));
                CREATE TABLE IF NOT EXISTS ci_v2_notifications (
                    intervention INTEGER NOT NULL REFERENCES ci_v2_interventions(id) ON DELETE CASCADE,
                    recipient INTEGER NOT NULL, PRIMARY KEY(intervention,recipient));
                INSERT OR IGNORE INTO ci_schema VALUES (3);
            ''')

    @staticmethod
    def number(value):
        if not value.isascii() or not value.isdigit() or len(value) > 9 or int(value) < 1:
            raise ValueError('ID harus bilangan bulat positif, tanpa awalan M/U/R/I.')
        return int(value)

    def ensure_forum(self, db, chat_id):
        db.execute('INSERT OR IGNORE INTO ci_forums(chat_id,title,objective) VALUES (?,?,?)',
                   (chat_id, 'Forum CI', 'Merumuskan spesifikasi proyek UAS aplikasi AI fasilitasi CI.'))

    def valid_integrations(self, db, chat_id):
        return db.execute('''SELECT i.* FROM ci_v2_integrations i WHERE i.chat_id=?
            AND (SELECT COUNT(*) FROM ci_v2_sources s WHERE s.integration=i.id)=i.source_count
            AND NOT EXISTS (SELECT 1 FROM ci_v2_sources s JOIN ci_messages m ON m.id=s.message_id
                WHERE s.integration=i.id AND s.revision!=m.revision) ORDER BY i.id''', (chat_id,)).fetchall()

    def snapshot(self, chat_id):
        with self.o.db() as db:
            rows = list(reversed(db.execute('SELECT * FROM ci_messages WHERE chat_id=? ORDER BY timestamp DESC,id DESC LIMIT 200', (chat_id,)).fetchall()))
            integrations = self.valid_integrations(db, chat_id)
            objections = db.execute('''SELECT COUNT(*) FROM ci_v2_ballots b JOIN ci_v2_rounds r ON r.id=b.round_id
                JOIN ci_v2_proposals p ON p.id=r.proposal WHERE p.chat_id=? AND r.status='open' AND b.stance='keberatan' ''', (chat_id,)).fetchone()[0]
            resolved = db.execute('''SELECT COUNT(*) FROM ci_v2_ballots b JOIN ci_v2_rounds r ON r.id=b.round_id
                JOIN ci_v2_proposals p ON p.id=r.proposal WHERE p.chat_id=? AND r.status IN ('open','confirmed')
                AND b.stance='setuju' AND EXISTS (SELECT 1 FROM ci_v2_ballot_history h WHERE h.round_id=b.round_id AND h.nim=b.nim AND h.stance='keberatan')''', (chat_id,)).fetchone()[0]
        roster = {r['NIM'] for r in self.o.roster()}
        counts, disagreements, syntheses, proposals, replies = {}, [], [], [], []
        by_telegram_id = {r['telegram_message_id']: r for r in rows}
        for r in rows:
            if r['nim'] in roster:
                counts[r['nim']] = counts.get(r['nim'], 0) + 1
            low = r['text'].casefold()
            if re.search(r'\b(tidak setuju|keberatan|kurang setuju|namun|tetapi)\b', low):
                disagreements.append(r['id'])
            if re.search(r'\b(usul|usulan|sebaiknya|bagaimana jika)\b', low):
                proposals.append(r['id'])
            parent = by_telegram_id.get(r['reply_to'])
            if parent and parent['telegram_id'] != r['telegram_id']:
                replies.append([parent['id'], r['id']])
                if re.search(r'\b(gabungkan|menggabungkan|sintesis|merangkum)\b', low):
                    syntheses.append([parent['id'], r['id']])
        n = sum(counts.values())
        share = max(counts.values(), default=0) / n if n else 0
        ratio = len(counts) / len(roster) if roster else 0
        fingerprint = hashlib.sha256(json.dumps({
            'messages': [(r['id'], r['revision']) for r in rows], 'roster': sorted(roster),
            'integrations': [r['id'] for r in integrations], 'objections': objections}, sort_keys=True).encode()).hexdigest()
        triggers = []
        if n >= self.min_messages:
            if ratio < self.active_ratio:
                triggers.append('participation_gap')
            if share > self.dominance_share:
                triggers.append('concentration')
        if disagreements:
            triggers.append('disagreement')
        if proposals and replies and not (syntheses or integrations):
            triggers.append('integration_gap')
        if objections:
            triggers.append('open_objection')
        return dict(rows=rows, active=len(counts), total=len(roster), ratio=ratio, share=share,
                    disagreements=disagreements, syntheses=syntheses, proposals=proposals,
                    integrations=integrations, replies=replies, objections=objections, resolved=resolved,
                    triggers=triggers, fingerprint=fingerprint)

    def report(self, chat_id):
        s = self.snapshot(chat_id)
        lines = ['Intelligent Facilitator v2 — indikator lokal eksploratif',
                 f"Jendela: {len(s['rows'])} pesan terakhir (maksimal 200).",
                 f"Partisipasi teramati: {s['active']}/{s['total']} mahasiswa ({s['ratio']:.0%}).",
                 f"Porsi pesan mahasiswa terbesar: {s['share']:.0%}.",
                 f"Penanda perbedaan pendapat: {len(s['disagreements'])}; bukan diagnosis konflik personal.",
                 'Bukti perbedaan: ' + (', '.join(f'M{x}' for x in s['disagreements'][-10:]) or 'belum teramati'),
                 f"Balasan lintas peserta: {len(s['replies'])}; kandidat sintesis: {len(s['syntheses'])}.",
                 f"Integrasi eksplisit bersumber: {len(s['integrations'])}; keberatan formal terbuka: {s['objections']}.",
                 f"Keberatan yang kemudian diubah pemiliknya menjadi setuju: {s['resolved']}.",
                 'Ketimpangan dihitung dari volume, bukan kualitas. Peserta belum teramati belum tentu tidak berpartisipasi.',
                 'Konsensus hanya melalui /sepakat, /sikap, lalu /konfirmasi oleh fasilitator.']
        return '\n'.join(lines)

    def propose_interventions(self, chat_id):
        s = self.snapshot(chat_id)
        now = time.time()
        with self.o.db() as db:
            self.invalidate(db, chat_id)
            for trigger in s['triggers']:
                diagnosis, questions = QUESTIONS[trigger]
                # Reuse an outstanding recommendation rather than flooding DMs.
                if db.execute("SELECT 1 FROM ci_v2_interventions WHERE chat_id=? AND trigger=? AND status IN ('pending','approved')", (chat_id, trigger)).fetchone():
                    continue
                last = db.execute('SELECT MAX(created) FROM ci_v2_interventions WHERE chat_id=? AND trigger=?', (chat_id, trigger)).fetchone()[0]
                if last is not None and now-last < self.cooldown_seconds:
                    continue
                sources = {str(r['id']): [r['revision'],r['telegram_message_id'],r['telegram_id']] for r in s['rows']}
                self.ensure_forum(db, chat_id)
                db.execute('''INSERT OR IGNORE INTO ci_v2_interventions(chat_id,trigger,fingerprint,diagnosis,question,sources,created)
                    VALUES (?,?,?,?,?,?,?)''', (chat_id, trigger, s['fingerprint'], diagnosis, questions[0], json.dumps(sources), now))
        return s

    def invalidate(self, db, chat_id):
        triggers = set(self.snapshot(chat_id)['triggers'])
        for row in db.execute("SELECT * FROM ci_v2_interventions WHERE chat_id=? AND status IN ('pending','approved')", (chat_id,)).fetchall():
            valid = row['trigger'] in triggers
            for mid, expected in json.loads(row['sources']).items():
                source = db.execute('SELECT revision,telegram_message_id,telegram_id FROM ci_messages WHERE id=? AND chat_id=?', (int(mid), chat_id)).fetchone()
                if not source or list(source) != expected:
                    valid = False
                    break
            if not valid:
                db.execute("UPDATE ci_v2_interventions SET status='stale' WHERE id=?", (row['id'],))

    @staticmethod
    def intervention_text(row):
        evidence = ', '.join(f'M{mid}' for mid in list(json.loads(row['sources']))[-8:]) or 'keberatan formal pada putaran terbuka'
        return (f"Saran intervensi I{row['id']} — {row['trigger']}\n{row['diagnosis']}\n"
                f"Bukti konteks: {evidence}. Confidence: rendah (aturan lokal).\n"
                f"Pertanyaan usulan: {row['question']}\n"
                'Tujuan: memperjelas alasan, memberi ruang perspektif, dan mendukung deliberasi.\n'
                'Indikator lokal, perlu penilaian fasilitator. Tidak diposting otomatis.\n'
                f"/terapkan {row['id']} [teks pengganti]\n/alternatif {row['id']}\n/abaikan {row['id']}")

    def rounds_text(self, db, chat_id, target=None):
        sql = '''SELECT r.*,p.body,p.id proposal_id FROM ci_v2_rounds r JOIN ci_v2_proposals p ON p.id=r.proposal
                 WHERE p.chat_id=?'''
        args = [chat_id]
        if target:
            sql += ' AND r.id=?'
            args.append(target)
        else:
            sql += " AND r.status!='superseded'"
        rows = db.execute(sql + ' ORDER BY r.id DESC LIMIT 10', args).fetchall()
        out = []
        for r in rows:
            total = db.execute('SELECT COUNT(*) FROM ci_v2_electorate WHERE round_id=?', (r['id'],)).fetchone()[0]
            counts = dict(db.execute('SELECT stance,COUNT(*) FROM ci_v2_ballots WHERE round_id=? GROUP BY stance', (r['id'],)).fetchall())
            out.append(f"R{r['id']} / U{r['proposal_id']} [{r['status']}]: {r['body']}\n"
                       f"Setuju {counts.get('setuju',0)}/{total}, abstain {counts.get('abstain',0)}, "
                       f"keberatan {counts.get('keberatan',0)}, belum merespons {total-sum(counts.values())}.\n"
                       'Metode: persetujuan eksplisit seluruh daftar peserta pada awal putaran, diikuti konfirmasi fasilitator.')
        return '\n\n'.join(out) or 'Belum ada putaran konfirmasi. Fasilitator dapat memulai /sepakat ID_USULAN.'

    def command(self, uid, user, chat, chat_id, command, arg):
        private = chat['type'] == 'private'
        staff = self.o.is_facilitator(uid, chat_id)
        if command in {'/intervensi','/terapkan','/abaikan','/alternatif'}:
            if not private:
                return 'Saran intervensi hanya dikelola melalui chat pribadi dengan bot.'
            if not staff:
                return 'Perintah ini khusus fasilitator aktif atau dosen/staf.'
        if command in {'/sepakat','/konfirmasi','/bukaulang'} and not staff:
            return 'Perintah ini khusus fasilitator aktif atau dosen/staf.'
        if self.o.state(chat_id)['paused'] and command not in {'/konsensus','/usulan','/keberatan','/integrasi','/partisipasi','/konflik'}:
            return 'Forum dijeda; fasilitasi dilanjutkan setelah /resume.'
        try:
            with self.o.db() as db:
                self.ensure_forum(db, chat_id)
                if command in {'/partisipasi','/konflik'}:
                    return self.report(chat_id)
                if command == '/integrasi':
                    if arg:
                        if self.o.state(chat_id)['paused']:
                            return 'Forum dijeda. Integrasi baru belum disimpan.'
                        ids, _, body = arg.partition(' ')
                        mids = list(dict.fromkeys(self.number(x.removeprefix('M')) for x in ids.split(',')))
                        if len(mids) < 2 or len(mids) > 8 or not body.strip() or len(body) > 2000:
                            return 'Gunakan /integrasi M1,M2 TEKS (2–8 sumber berbeda, maksimal 2.000 karakter).'
                        sources = [db.execute('SELECT * FROM ci_messages WHERE id=? AND chat_id=?', (mid,chat_id)).fetchone() for mid in mids]
                        if any(r is None for r in sources):
                            return 'Semua sumber harus berupa pesan yang tersedia pada forum ini.'
                        if len({r['telegram_id'] for r in sources}) < 2:
                            return 'Integrasi membutuhkan sumber dari sedikitnya dua peserta berbeda.'
                        integration = db.execute('INSERT INTO ci_v2_integrations(chat_id,author,body,created,source_count) VALUES (?,?,?,?,?)', (chat_id,uid,body,time.time(),len(sources))).lastrowid
                        db.executemany('INSERT INTO ci_v2_sources VALUES (?,?,?)', [(integration,r['id'],r['revision']) for r in sources])
                        return f'Integrasi G{integration} tersimpan dengan sumber ' + ', '.join(f'M{x}' for x in mids) + '. Ini sintesis peserta, belum konsensus.'
                    valid = self.valid_integrations(db, chat_id)
                    return '\n'.join(f"G{r['id']}: {r['body']}" for r in valid[-10:]) or 'Belum ada integrasi eksplisit yang sumbernya masih valid. Gunakan /integrasi M1,M2 TEKS.'
                if command == '/usulan':
                    if arg:
                        if self.o.state(chat_id)['paused']:
                            return 'Forum dijeda. Usulan baru belum disimpan.'
                        if len(arg) > 2000:
                            return 'Usulan maksimal 2.000 karakter.'
                        proposal = db.execute('INSERT INTO ci_v2_proposals(chat_id,author,body,created) VALUES (?,?,?,?)', (chat_id,uid,arg,time.time())).lastrowid
                        return f'Usulan U{proposal} tersimpan. Fasilitator dapat memulai /sepakat {proposal}.'
                    rows = db.execute('SELECT * FROM ci_v2_proposals WHERE chat_id=? ORDER BY id DESC LIMIT 10', (chat_id,)).fetchall()
                    return '\n'.join(f"U{r['id']}: {r['body']}" for r in rows) or 'Belum ada usulan formal. Gunakan /usulan TEKS.'
                if command in {'/sepakat','/bukaulang'}:
                    target = self.number(arg)
                    if command == '/bukaulang':
                        row = db.execute('SELECT proposal FROM ci_v2_rounds WHERE id=?', (target,)).fetchone()
                        if not row:
                            return 'Putaran tidak ditemukan.'
                        target = row[0]
                    proposal = db.execute('SELECT * FROM ci_v2_proposals WHERE id=? AND chat_id=?', (target,chat_id)).fetchone()
                    if not proposal:
                        return 'Usulan tidak ditemukan pada forum ini.'
                    current = db.execute("SELECT * FROM ci_v2_rounds WHERE proposal=? AND status IN ('open','confirmed')", (target,)).fetchone()
                    if current and command != '/bukaulang':
                        return f"Usulan sudah memiliki putaran R{current['id']}. Gunakan /konsensus {current['id']} atau /bukaulang {current['id']}."
                    if current:
                        db.execute("UPDATE ci_v2_rounds SET status='superseded' WHERE id=?", (current['id'],))
                    round_id = db.execute("INSERT INTO ci_v2_rounds(proposal,status,created) VALUES (?,'open',?)", (target,time.time())).lastrowid
                    roster = {r['NIM']: (r.get('ID') or '').strip() for r in self.o.roster()}
                    db.executemany('INSERT INTO ci_v2_electorate VALUES (?,?,?)', [(round_id,nim,tid) for nim,tid in roster.items()])
                    return (f'Putaran R{round_id} dibuka untuk U{target}: {proposal["body"]}\n'
                            f'{len(roster)} mahasiswa pada snapshot daftar peserta. Belum ada konsensus.\n'
                            f'/sikap {round_id} setuju\n/sikap {round_id} abstain ALASAN\n/sikap {round_id} keberatan ALASAN\n'
                            'Tidak merespons bukan persetujuan. Setelah semua setuju, fasilitator menjalankan /konfirmasi ID_PUTARAN.')
                if command == '/sikap':
                    parts = arg.split(maxsplit=2)
                    if len(parts) < 2 or parts[1] not in {'setuju','abstain','keberatan'}:
                        return 'Gunakan /sikap ID_PUTARAN setuju|abstain|keberatan [ALASAN].'
                    rid, stance, reason = self.number(parts[0]), parts[1], parts[2] if len(parts)>2 else ''
                    if (stance in {'keberatan','abstain'} and not reason.strip()) or len(reason)>2000:
                        return 'Abstain/keberatan memerlukan alasan; maksimal 2.000 karakter.'
                    row = db.execute('SELECT r.* FROM ci_v2_rounds r JOIN ci_v2_proposals p ON p.id=r.proposal WHERE r.id=? AND p.chat_id=?', (rid,chat_id)).fetchone()
                    if not row or row['status'] != 'open':
                        return 'Putaran tidak terbuka. Fasilitator perlu /bukaulang untuk mengubah keputusan yang sudah dikonfirmasi.'
                    member = db.execute('SELECT telegram_id FROM ci_v2_electorate WHERE round_id=? AND nim=?', (rid,user['NIM'])).fetchone()
                    if not member or member[0] != str(uid):
                        return 'Identitas Anda tidak cocok dengan snapshot peserta putaran ini. Minta fasilitator membuka putaran baru.'
                    db.execute('INSERT INTO ci_v2_ballots VALUES (?,?,?,?,?) ON CONFLICT(round_id,nim) DO UPDATE SET stance=excluded.stance,reason=excluded.reason,updated=excluded.updated', (rid,user['NIM'],stance,reason,time.time()))
                    db.execute('INSERT INTO ci_v2_ballot_history(round_id,nim,stance,reason,updated) VALUES (?,?,?,?,?)', (rid,user['NIM'],stance,reason,time.time()))
                    return f'Sikap Anda pada R{rid} dicatat: {stance}.\n' + self.rounds_text(db,chat_id,rid)
                if command == '/konfirmasi':
                    rid = self.number(arg)
                    row = db.execute('SELECT r.* FROM ci_v2_rounds r JOIN ci_v2_proposals p ON p.id=r.proposal WHERE r.id=? AND p.chat_id=?', (rid,chat_id)).fetchone()
                    if not row or row['status'] != 'open':
                        return 'Putaran tidak terbuka atau tidak ditemukan pada forum ini.'
                    snapshot = dict(db.execute('SELECT nim,telegram_id FROM ci_v2_electorate WHERE round_id=?', (rid,)).fetchall())
                    current = {r['NIM']: (r.get('ID') or '').strip() for r in self.o.roster()}
                    if current != snapshot:
                        return 'Daftar peserta berubah. Gunakan /bukaulang agar semua mengonfirmasi snapshot terbaru.'
                    votes = db.execute("SELECT COUNT(*) FROM ci_v2_ballots WHERE round_id=? AND stance='setuju'", (rid,)).fetchone()[0]
                    if not snapshot or votes != len(snapshot):
                        return 'Belum dapat dikonfirmasi: seluruh peserta harus menyatakan setuju; abstain, keberatan, atau tidak merespons belum memenuhi metode ini.\n' + self.rounds_text(db,chat_id,rid)
                    db.execute("UPDATE ci_v2_rounds SET status='confirmed',confirmed_by=?,confirmed_at=? WHERE id=?", (uid,time.time(),rid))
                    return f'Konsensus R{rid} dikonfirmasi fasilitator setelah {votes}/{len(snapshot)} peserta menyatakan setuju.\n' + self.rounds_text(db,chat_id,rid)
                if command == '/konsensus':
                    return self.rounds_text(db,chat_id,self.number(arg) if arg else None)
                if command == '/keberatan':
                    rows = db.execute('''SELECT b.round_id,b.reason FROM ci_v2_ballots b JOIN ci_v2_rounds r ON r.id=b.round_id
                        JOIN ci_v2_proposals p ON p.id=r.proposal WHERE p.chat_id=? AND r.status='open' AND b.stance='keberatan' ORDER BY b.updated DESC LIMIT 20''', (chat_id,)).fetchall()
                    return ('Keberatan formal (alasan dapat dibaca peserta forum):\n' + '\n'.join(f"R{r['round_id']}: {r['reason']}" for r in rows)) if rows else 'Belum ada keberatan formal terbuka. Penanda perbedaan percakapan tersedia melalui /konflik.'
                if command == '/intervensi':
                    self.propose_interventions(chat_id)
                    rows = db.execute("SELECT * FROM ci_v2_interventions WHERE chat_id=? AND status='pending' ORDER BY id DESC LIMIT 5", (chat_id,)).fetchall()
                    return '\n\n'.join(self.intervention_text(r) for r in rows) or 'Tidak ada saran intervensi yang menunggu keputusan.'
                if command in {'/terapkan','/abaikan','/alternatif'}:
                    values = arg.split(maxsplit=1)
                    if not values:
                        return f'Gunakan {command} ID_INTERVENSI [teks pengganti untuk /terapkan].'
                    target = self.number(values[0])
                    self.invalidate(db, chat_id)
                    row = db.execute('SELECT * FROM ci_v2_interventions WHERE id=? AND chat_id=?', (target,chat_id)).fetchone()
                    if not row or row['status'] not in {'pending','approved'}:
                        return 'Saran tidak tersedia, sudah diposting/diabaikan, atau buktinya berubah.'
                    if command == '/abaikan':
                        db.execute("UPDATE ci_v2_interventions SET status='ignored',decided_by=? WHERE id=?", (uid,target))
                        return 'Saran diabaikan; tidak akan diposting.'
                    if command == '/alternatif':
                        if row['status'] != 'pending':
                            return 'Saran sudah disetujui; abaikan dahulu jika ingin membatalkan.'
                        variant = 1 - row['variant']
                        db.execute('UPDATE ci_v2_interventions SET question=?,variant=? WHERE id=?', (QUESTIONS[row['trigger']][1][variant],variant,target))
                        revised = db.execute('SELECT * FROM ci_v2_interventions WHERE id=?', (target,)).fetchone()
                        return self.intervention_text(revised)
                    body = values[1].strip() if len(values)>1 else row['question']
                    if not body or len(body)>2000:
                        return 'Teks intervensi harus berisi 1–2.000 karakter.'
                    db.execute("UPDATE ci_v2_interventions SET question=?,status='approved',decided_by=? WHERE id=?", (body,uid,target))
                    return f'Intervensi I{target} disetujui dan masuk antrean kirim ke forum. Teks: {body}'
        except ValueError as exc:
            return str(exc)
        return 'Perintah versi 2 tidak dikenali.'

    def pending_deliveries(self):
        deliveries = []
        with self.o.db() as db:
            forums = db.execute('SELECT chat_id FROM ci_forums WHERE paused=0').fetchall()
            for forum in forums:
                cid = forum[0]
                if cid not in self.o.chats:
                    continue
                self.invalidate(db,cid)
                self.o.refresh_facilitators(db,cid)
                active = db.execute("SELECT telegram_id FROM ci_facilitators WHERE chat_id=? AND status='active'", (cid,)).fetchone()
                recipients = self.o.staff | ({active[0]} if active else set())
                for row in db.execute("SELECT * FROM ci_v2_interventions WHERE chat_id=? AND status IN ('pending','approved') ORDER BY id", (cid,)).fetchall():
                    if row['status'] == 'approved':
                        deliveries.append((cid, f"Pertanyaan fasilitator (I{row['id']}):\n{row['question']}", row['id'], 'post'))
                    else:
                        for recipient in sorted(recipients):
                            sent = db.execute('SELECT 1 FROM ci_v2_notifications WHERE intervention=? AND recipient=?', (row['id'],recipient)).fetchone()
                            if not sent:
                                deliveries.append((recipient, f'Forum {cid}\n'+self.intervention_text(row), row['id'], 'notify'))
        return deliveries

    def mark_delivered(self, recipient, intervention, kind):
        with self.o.db() as db:
            if kind == 'post':
                db.execute("UPDATE ci_v2_interventions SET status='posted',posted_at=? WHERE id=? AND status='approved'", (time.time(),intervention))
            else:
                db.execute('INSERT OR IGNORE INTO ci_v2_notifications VALUES (?,?)', (intervention,recipient))

    def erase_user(self, db, uid):
        # Supersede a collective decision if some of its human evidence is erased.
        nims = [r[0] for r in db.execute('SELECT DISTINCT nim FROM ci_v2_electorate WHERE telegram_id=?', (str(uid),))]
        for nim in nims:
            db.execute("UPDATE ci_v2_rounds SET status='superseded' WHERE id IN (SELECT round_id FROM ci_v2_electorate WHERE nim=?)", (nim,))
            db.execute('DELETE FROM ci_v2_electorate WHERE nim=?', (nim,))
        db.execute('DELETE FROM ci_v2_integrations WHERE author=?', (uid,))
        db.execute('DELETE FROM ci_v2_proposals WHERE author=?', (uid,))
        db.execute('DELETE FROM ci_v2_notifications WHERE recipient=?', (uid,))
        db.execute('DELETE FROM ci_v2_interventions WHERE decided_by=?', (uid,))
        db.execute("UPDATE ci_v2_rounds SET status='superseded',confirmed_by=NULL WHERE confirmed_by=?", (uid,))
        # Receipts can contain authored proposals, objections, and integration text.
        db.execute('DELETE FROM ci_command_results')

    def purge(self, db, cutoff):
        db.execute('DELETE FROM ci_v2_proposals WHERE created<?', (cutoff,))
        db.execute('DELETE FROM ci_v2_integrations WHERE created<? OR id IN (SELECT i.id FROM ci_v2_integrations i LEFT JOIN ci_v2_sources s ON s.integration=i.id GROUP BY i.id HAVING COUNT(s.message_id)!=i.source_count)', (cutoff,))
        db.execute('DELETE FROM ci_v2_interventions WHERE created<?', (cutoff,))
