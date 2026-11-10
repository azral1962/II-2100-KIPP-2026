"""Invite consenting registered students and verify their join requests."""
import time

from telegram_bot import TelegramAPIError


class ForumJoining:
    def __init__(self, bot):
        self.bot=bot
        self.o=bot.observer
        with self.o.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS ci_join_invites (
                    link TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, expires INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS ci_join_invites_chat ON ci_join_invites(chat_id,expires);
                CREATE TABLE IF NOT EXISTS ci_join_receipts (
                    update_id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL, action TEXT NOT NULL, handled REAL NOT NULL);
            ''')

    @staticmethod
    def is_member(member):
        return member.get('status') in {'creator','administrator','member'} or (
            member.get('status')=='restricted' and member.get('is_member') is True)

    def invite(self, chat_id):
        now=int(time.time())
        with self.o.db() as db:
            cached=db.execute('SELECT link FROM ci_join_invites WHERE chat_id=? AND expires>? ORDER BY expires DESC LIMIT 1',(chat_id,now+60)).fetchone()
        if cached:
            return cached[0]
        expires=now+86400
        result=self.bot._api_call('createChatInviteLink',{'chat_id':chat_id,'name':'KIPP-CI consent',
                                   'creates_join_request':'true','expire_date':expires})
        link=result.get('invite_link')
        if not isinstance(link,str) or not link.startswith('https://t.me/'):
            raise TelegramAPIError('Tautan undangan CI tidak valid.')
        with self.o.db() as db:
            db.execute('INSERT OR REPLACE INTO ci_join_invites VALUES (?,?,?)',(link,chat_id,expires))
        return link

    def links_for(self, uid):
        # Unlike configured staff, students must have a real CSV identity.
        from ci import participant
        if participant(self.bot.participants,uid) is None:
            return 'Akun Telegram ini belum terhubung di peserta.csv. Hubungi dosen untuk koreksi data.'
        if not self.o.consent(uid):
            return 'Baca /start lalu kirim /setuju di chat pribadi sebelum bergabung melalui bot.'
        if not self.o.chats:
            return 'Persetujuan sudah tersimpan. Operator perlu mengisi CI_CHAT_IDS sebelum bot dapat mengundang ke forum.'
        lines=['Bergabung ke forum CI:','Tekan tautan lalu pilih Request to Join / Minta Bergabung. Bot akan memeriksa akun dan menyetujui permintaan peserta terdaftar yang masih memberi persetujuan.']
        for chat_id in sorted(self.o.chats):
            try:
                member=self.bot._api_call('getChatMember',{'chat_id':chat_id,'user_id':uid})
                if self.is_member(member):
                    lines.append(f'Forum {chat_id}: Anda sudah menjadi anggota.')
                elif member.get('status')=='kicked':
                    lines.append(f'Forum {chat_id}: akses akun dibatasi administrator. Hubungi dosen.')
                else:
                    lines.append(f'Forum {chat_id}: {self.invite(chat_id)}')
            except TelegramAPIError:
                # Consent remains committed even when Telegram/admin permissions fail.
                lines.append(f'Forum {chat_id}: tautan belum tersedia. Bot perlu menjadi admin dengan izin mengundang pengguna. Coba /gabung setelah operator memperbaiki akses.')
        return '\n\n'.join(lines)

    def handle_request(self, update):
        request=update.get('chat_join_request') or {}
        cid=request.get('chat',{}).get('id')
        uid=request.get('from',{}).get('id')
        update_id=update.get('update_id')
        if cid not in self.o.chats or not isinstance(uid,int) or not isinstance(update_id,int):
            return
        with self.o.db() as db:
            if db.execute('SELECT 1 FROM ci_join_receipts WHERE update_id=?',(update_id,)).fetchone():
                return
            link=request.get('invite_link',{}).get('invite_link')
            owned=db.execute('SELECT 1 FROM ci_join_invites WHERE chat_id=? AND link=?',(cid,link)).fetchone()
        if not owned:
            return  # Requests through other admins' links remain theirs to review.
        from ci import participant
        eligible=participant(self.bot.participants,uid) is not None and self.o.consent(uid)
        method='approveChatJoinRequest' if eligible else 'declineChatJoinRequest'
        if eligible:
            member=self.bot._api_call('getChatMember',{'chat_id':cid,'user_id':uid})
            already=self.is_member(member)
        else:
            already=False
        if not already:
            try:
                self.bot._api_call(method,{'chat_id':cid,'user_id':uid})
            except TelegramAPIError:
                # Recover if approval succeeded just before a process/network failure.
                if not eligible or not self.is_member(self.bot._api_call('getChatMember',{'chat_id':cid,'user_id':uid})):
                    raise
        with self.o.db() as db:
            db.execute('INSERT OR IGNORE INTO ci_join_receipts VALUES (?,?,?,?,?)',
                       (update_id,cid,uid,'approved' if eligible else 'declined',time.time()))

    def purge(self):
        cutoff=time.time()-self.o.retention_days*86400
        with self.o.db() as db:
            db.execute('DELETE FROM ci_join_receipts WHERE handled<?',(cutoff,))
            db.execute('DELETE FROM ci_join_invites WHERE expires<?',(cutoff,))
