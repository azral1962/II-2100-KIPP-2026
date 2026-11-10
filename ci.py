"""KIPP-CI v3: TISE Collective Intelligence Laboratory. Jalankan: python3 ci.py."""

from __future__ import annotations

import argparse
import csv
import json
import time
import logging
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from app import load_env_file, resolve_project_path
from course_service import ParticipantDataError
from telegram_bot import TelegramAPIError, TelegramBot
from ci_observer import Observer


LEGACY_HELP = """Forum Collective Intelligence (CI)
Bangun pemahaman bersama: ajukan pertanyaan, bagikan ide dan bukti,
tanggapi dengan alasan, lalu susun sintesis bersama.

/topik JUDUL - buka diskusi
/daftar [HALAMAN] - lihat topik, terbaru dahulu
/baca TOPIK [HALAMAN] - baca diskusi (10 kontribusi per halaman)
/ide TOPIK TEKS - sampaikan gagasan
/bukti TOPIK TEKS - tambahkan data, sumber, atau tautan
/tanya TOPIK TEKS - ajukan pertanyaan
/balas KONTRIBUSI TEKS - tanggapi kontribusi tertentu
/sintesis TOPIK TEKS - rumuskan pemahaman dan langkah bersama
/ringkas TOPIK - lihat jumlah kontribusi dan sintesis terakhir
/status - periksa identitas peserta
/bantuan - lihat panduan

Semua peserta berbagi forum yang sama melalui chat pribadi dengan bot.
Kontribusi beserta nama penulis dapat dibaca seluruh peserta.
Gunakan /daftar dan /baca untuk mengikuti percakapan.
Sintesis ditulis peserta; belum merupakan konsensus atau rangkuman AI.
"""


def participant(path: Path, telegram_id: int) -> dict | None:
    """Read the existing identity mapping afresh; never change registrations."""
    try:
        with path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            if not {"NIM", "Nama", "ID"}.issubset(reader.fieldnames or []):
                raise ParticipantDataError("peserta.csv harus memiliki NIM, Nama, dan ID.")
            matches = [row for row in reader if (row.get("ID") or "").strip() == str(telegram_id)]
    except (OSError, csv.Error, UnicodeError) as exc:
        raise ParticipantDataError("Daftar peserta tidak dapat dibaca.") from exc
    if len(matches) > 1:
        raise ParticipantDataError("ID Telegram ganda dalam daftar peserta; hubungi dosen.")
    return matches[0] if matches else None


class Forum:
    """Archived private-forum storage API; retained for existing data and tools."""
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with closing(self.connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                    nim TEXT NOT NULL, name TEXT NOT NULL,
                    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY, topic INTEGER NOT NULL REFERENCES topics(id),
                    parent INTEGER REFERENCES posts(id), kind TEXT NOT NULL,
                    body TEXT NOT NULL, nim TEXT NOT NULL, name TEXT NOT NULL,
                    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE INDEX IF NOT EXISTS posts_topic ON posts(topic, id);
                CREATE TABLE IF NOT EXISTS receipts (
                    update_id INTEGER PRIMARY KEY, response TEXT NOT NULL);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def execute(self, update_id: int, user: dict, text: str) -> str:
        # Persist the reply together with the mutation so Telegram retries cannot
        # create a second topic or contribution after a failed sendMessage.
        db = self.connect()
        try:
            with db:
                db.execute("BEGIN IMMEDIATE")
                prior = db.execute("SELECT response FROM receipts WHERE update_id=?", (update_id,)).fetchone()
                if prior:
                    return prior[0]
                try:
                    response = self.dispatch(db, user, text)
                except ValueError as exc:
                    response = str(exc)
                db.execute("INSERT INTO receipts VALUES (?, ?)", (update_id, response))
                return response
        finally:
            db.close()

    @staticmethod
    def number(value: str) -> int:
        if len(value) > 9 or not value.isascii() or not value.isdigit() or int(value) < 1:
            raise ValueError("Nomor topik, kontribusi, dan halaman harus bilangan bulat positif.")
        return int(value)

    def dispatch(self, db, user, text):
        parts = text.strip().split(maxsplit=1)
        command = parts[0].split("@", 1)[0].lower() if parts else ""
        arg = parts[1].strip() if len(parts) == 2 else ""
        if command in {"/start", "/bantuan", "/help"}:
            return f"Selamat datang, {user['Nama']}!\n\n{LEGACY_HELP}"
        if command == "/status":
            return f"Terdaftar: {user['Nama']} ({user['NIM']}). Tidak perlu registrasi ulang."
        if command == "/topik":
            if not arg or len(arg) > 160:
                raise ValueError("Gunakan /topik JUDUL (1–160 karakter).")
            topic = db.execute("INSERT INTO topics(title,nim,name) VALUES (?,?,?)",
                               (arg, user['NIM'], user['Nama'])).lastrowid
            return f"Topik #{topic}: {arg}\nMulai dengan /ide {topic} gagasan Anda."
        if command == "/daftar":
            page = self.number(arg) if arg else 1
            rows = db.execute("SELECT * FROM topics ORDER BY id DESC LIMIT 10 OFFSET ?", ((page-1)*10,)).fetchall()
            return f"Topik — halaman {page}\n" + ("\n".join(f"#{r['id']} {r['title']} — {r['name']}" for r in rows) or "Belum ada topik pada halaman ini.") + "\nGunakan /baca NOMOR atau /daftar HALAMAN."
        if command in {"/ide", "/bukti", "/tanya", "/sintesis", "/balas"}:
            values = arg.split(maxsplit=1)
            if len(values) != 2 or len(values[1]) > 2000:
                raise ValueError(f"Gunakan {command} NOMOR TEKS (maksimal 2.000 karakter).")
            target = self.number(values[0])
            parent = None
            if command == "/balas":
                post = db.execute("SELECT topic FROM posts WHERE id=?", (target,)).fetchone()
                if not post:
                    raise ValueError("Kontribusi tidak ditemukan.")
                parent, target = target, post['topic']
            if not db.execute("SELECT id FROM topics WHERE id=?", (target,)).fetchone():
                raise ValueError("Topik tidak ditemukan. Lihat /daftar.")
            post_id = db.execute("INSERT INTO posts(topic,parent,kind,body,nim,name) VALUES (?,?,?,?,?,?)",
                                 (target, parent, command[1:], values[1], user['NIM'], user['Nama'])).lastrowid
            return f"Kontribusi #{post_id} tersimpan di topik #{target}.\nBaca: /baca {target}"
        if command in {"/baca", "/ringkas"}:
            values = arg.split()
            if len(values) not in ({1, 2} if command == "/baca" else {1}):
                raise ValueError(f"Gunakan {command} TOPIK" + (" [HALAMAN]." if command == "/baca" else "."))
            topic_id = self.number(values[0])
            topic = db.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()
            if not topic:
                raise ValueError("Topik tidak ditemukan. Lihat /daftar.")
            count, authors = db.execute("SELECT COUNT(*), COUNT(DISTINCT nim) FROM posts WHERE topic=?", (topic_id,)).fetchone()
            header = f"Topik #{topic_id}: {topic['title']}\nOleh {topic['name']}\n{count} kontribusi, {authors} kontributor\n"
            if command == "/ringkas":
                last = db.execute("SELECT * FROM posts WHERE topic=? AND kind='sintesis' ORDER BY id DESC LIMIT 1", (topic_id,)).fetchone()
                return header + (f"\nSintesis terakhir oleh {last['name']}:\n{last['body']}" if last else "\nBelum ada sintesis. Tambahkan dengan /sintesis TOPIK TEKS.")
            page = self.number(values[1]) if len(values) == 2 else 1
            rows = db.execute("SELECT * FROM posts WHERE topic=? ORDER BY id LIMIT 10 OFFSET ?", (topic_id, (page-1)*10)).fetchall()
            body = "\n\n".join(f"#{r['id']} [{r['kind']}] {r['name']} ({r['created']} UTC)" + (f" → #{r['parent']}" if r['parent'] else "") + f"\n{r['body']}" for r in rows)
            return header + f"Halaman {page}/{max(1, (count+9)//10)}\n\n" + (body or "Belum ada kontribusi pada halaman ini.") + f"\n\n/baca {topic_id} HALAMAN • /balas KONTRIBUSI TEKS"
        return "Gunakan /bantuan untuk panduan forum. Untuk berkontribusi: /ide TOPIK TEKS."


class CIBot(TelegramBot):
    def __init__(self, token, participants, forum, *, observer=None, **kwargs):
        super().__init__(token, registry=None, **kwargs)
        self.participants = participants
        self.forum = forum
        self.observer = observer or Observer(forum.path, participants)
        self.username = None
        from ci_joining import ForumJoining
        self.joining = ForumJoining(self)

    def handle_update(self, update):
        if 'chat_join_request' in update:
            self.joining.handle_request(update)
            return
        message = update.get('message') or update.get('edited_message') or {}
        text = message.get('text', '')
        if text.startswith('/') and '@' in text.split()[0] and self.username:
            if text.split()[0].split('@', 1)[1].casefold() != self.username.casefold():
                return
        command=text.strip().split(maxsplit=1)[0].split('@',1)[0].lower() if text.strip() else ''
        private=message.get('chat',{}).get('type')=='private'
        uid=message.get('from',{}).get('id')
        if command=='/gabung' and 'message' in update:
            if private and isinstance(uid,int) and message.get('chat',{}).get('id')==uid:
                self.send_message(uid,self.joining.links_for(uid))
            return
        try:
            responses = self.observer.handle(update)
        except sqlite3.Error as exc:
            raise ParticipantDataError('Penyimpanan Forum Observer bermasalah.') from exc
        for chat_id, response in responses:
            self.send_message(chat_id, response)
        if command=='/setuju' and private and isinstance(uid,int) and 'message' in update:
            if participant(self.participants,uid) is not None and self.observer.consent(uid):
                self.send_message(uid,self.joining.links_for(uid))

    def run(self):
        offset = self._load_offset()
        self.username = self._api_call('getMe', {}).get('username')
        logging.info('KIPP-CI TISE Collective Intelligence Laboratory v3 dimulai')
        while True:
            try:
                updates = self._api_call('getUpdates', {
                    'timeout': self.poll_timeout, 'offset': offset,
                    'allowed_updates': json.dumps(['message', 'edited_message', 'chat_join_request'])},
                    request_timeout=self.poll_timeout + 10)
                for update in updates:
                    if not isinstance(update.get('update_id'), int):
                        continue
                    self.handle_update(update)
                    offset = update['update_id'] + 1
                    self._save_offset(offset)
                for chat_id, response, fingerprint, now in self.observer.tick():
                    self.send_message(chat_id, response)
                    self.observer.mark_summary(chat_id, fingerprint, now)
                self.joining.purge()
                for recipient, response, intervention, kind in self.observer.facilitator.pending_deliveries():
                    try:
                        self.send_message(recipient, response)
                    except TelegramAPIError:
                        # One facilitator who has not opened a DM must not block others.
                        logging.warning('Intervensi CI belum terkirim; menunggu percobaan berikutnya.')
                        continue
                    self.observer.facilitator.mark_delivered(recipient, intervention, kind)
            except (TelegramAPIError, ParticipantDataError, sqlite3.Error, OSError):
                # API exception strings can contain a request URL and its token.
                logging.warning('Gangguan Telegram/data CI; mencoba kembali dalam 3 detik.')
                time.sleep(3)

    def send_message(self, chat_id, text):
        # A page may contain ten long contributions. Keep each Telegram payload
        # below its UTF-16 length limit, including names and emoji.
        chunk, units = '', 0
        for char in text:
            size = len(char.encode('utf-16-le')) // 2
            if units + size > 3500:
                super().send_message(chat_id, chunk)
                chunk, units = '', 0
            chunk += char
            units += size
        if chunk:
            super().send_message(chat_id, chunk)


def main():
    parser = argparse.ArgumentParser(description='KIPP-CI TISE Collective Intelligence Laboratory v3')
    parser.add_argument('--simulate', action='store_true', help='Demo sintetik lokal tanpa token')
    parser.add_argument('--database', type=Path, help='Database simulasi, wajib untuk --simulate')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--policy', choices=['none','inclusive','bridge'], default='inclusive')
    parser.add_argument('--steps', type=int, default=120)
    args = parser.parse_args()
    if args.simulate:
        if args.database is None:
            parser.error('--simulate membutuhkan --database PATH database simulasi baru')
        from ci_lab_simulator import run_experiment, summary
        try:
            observer, sid = run_experiment(args.database,args.seed,args.policy,args.steps)
        except ValueError as exc:
            parser.error(str(exc))
        print(summary(observer,sid))
        return
    if args.database is not None:
        parser.error('--database hanya untuk simulasi; gunakan CI_DATABASE untuk bot')
    root = Path(__file__).resolve().parent
    load_env_file(root / '.env')
    token = os.environ.get('TELEGRAM_BOT_TOKEN_CI', '').strip()
    if not token:
        raise SystemExit('TELEGRAM_BOT_TOKEN_CI belum diisi di .env.')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        timeout = int(os.environ.get('CI_POLL_TIMEOUT', '30'))
        if timeout <= 0:
            raise ValueError
    except ValueError:
        raise SystemExit('CI_POLL_TIMEOUT harus bilangan bulat positif.')
    def ids(name):
        try:
            return {int(value.strip()) for value in os.environ.get(name, '').split(',') if value.strip()}
        except ValueError:
            raise SystemExit(f'{name} harus daftar ID numerik dipisahkan koma.')

    def positive(name, default):
        try:
            value = int(os.environ.get(name, str(default)))
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            raise SystemExit(f'{name} harus bilangan bulat positif.')

    participants = resolve_project_path(root, os.environ.get('PESERTA_CSV', 'peserta.csv'))
    database = resolve_project_path(root, os.environ.get('CI_DATABASE', 'ci.sqlite3'))
    def ratio(name, default):
        try:
            value = float(os.environ.get(name, str(default)))
            if not 0 < value <= 1:
                raise ValueError
            return value
        except ValueError:
            raise SystemExit(f'{name} harus angka lebih dari 0 sampai 1.')
    observer = Observer(database, participants, chats=ids('CI_CHAT_IDS'),
                        staff=ids('CI_FACILITATOR_IDS'), instructors=ids('CI_INSTRUCTOR_IDS'),
                        retention_days=positive('CI_RETENTION_DAYS', 90),
                        analysis_seconds=positive('CI_ANALYSIS_SECONDS', 600),
                        summary_seconds=positive('CI_SUMMARY_SECONDS', 1200),
                        facilitator_options={
                            'min_messages': positive('CI_PARTICIPATION_MIN_MESSAGES', 6),
                            'dominance_share': ratio('CI_DOMINANCE_SHARE', .45),
                            'active_ratio': ratio('CI_ACTIVE_RATIO', .60),
                            'cooldown_seconds': positive('CI_INTERVENTION_COOLDOWN_SECONDS', 1200)})
    if not observer.chats:
        logging.warning('CI_CHAT_IDS kosong: pengamatan grup belum aktif.')
    bot = CIBot(token,
                resolve_project_path(root, os.environ.get('PESERTA_CSV', 'peserta.csv')),
                Forum(database), observer=observer,
                poll_timeout=timeout,
                offset_path=resolve_project_path(root, os.environ.get('CI_OFFSET_FILE', 'ci-offset.txt')))
    try:
        bot.run()
    except KeyboardInterrupt:
        logging.info('Bot CI dihentikan.')
    except TelegramAPIError:
        raise SystemExit('Koneksi awal Telegram gagal. Periksa token, koneksi, dan konfigurasi bot.') from None


if __name__ == '__main__':
    main()
