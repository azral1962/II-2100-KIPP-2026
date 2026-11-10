import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from ci import CIBot,Forum
from ci_observer import Observer
from telegram_bot import TelegramAPIError


class ForumJoiningTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name); self.roster=root/'peserta.csv'
        self.roster.write_text('NIM,Nama,ID,repo\n1,Ani,11,\n2,Budi,22,\n')
        self.o=Observer(root/'ci.sqlite3',self.roster,chats={-100})
        self.bot=CIBot('dummy',self.roster,Forum(self.o.path),observer=self.o)
        self.bot.send_message=Mock()
        self.bot._api_call=Mock(side_effect=self.api)

    def api(self,method,parameters,**kwargs):
        if method=='getChatMember': return {'status':'left'}
        if method=='createChatInviteLink': return {'invite_link':'https://t.me/+synthetic-test'}
        return True

    def message(self,text,uid=11,update=1,kind='private'):
        self.bot.handle_update({'update_id':update,'message':{'text':text,'from':{'id':uid},'chat':{'id':uid,'type':kind}}})

    def join(self,uid=11,update=100,chat=-100,link='https://t.me/+synthetic-test'):
        self.bot.handle_update({'update_id':update,'chat_join_request':{'chat':{'id':chat},'from':{'id':uid},'invite_link':{'invite_link':link}}})

    def test_consent_sends_link_without_reregistration(self):
        original=self.roster.read_bytes()
        self.message('/setuju')
        self.assertTrue(self.o.consent(11))
        self.assertIn('https://t.me/',self.bot.send_message.call_args.args[1])
        create=[c for c in self.bot._api_call.call_args_list if c.args[0]=='createChatInviteLink']
        self.assertEqual('true',create[0].args[1]['creates_join_request'])
        self.assertNotIn('member_limit',create[0].args[1])
        self.assertEqual(original,self.roster.read_bytes())

    def test_invite_requires_registered_consent_private_chat(self):
        self.message('/gabung')
        self.assertIn('/setuju',self.bot.send_message.call_args.args[1])
        self.message('/gabung',uid=999,update=2)
        self.assertIn('belum terhubung',self.bot.send_message.call_args.args[1])
        self.message('/setuju',update=3,kind='group')
        self.bot._api_call.assert_not_called()

    def test_invite_cache_and_retry_command(self):
        self.message('/setuju')
        self.message('/gabung',update=2)
        self.message('/setuju',update=1) # Telegram retries the same update
        self.assertEqual(1,sum(c.args[0]=='createChatInviteLink' for c in self.bot._api_call.call_args_list))

    def test_verified_request_approved_and_deduplicated(self):
        self.message('/setuju')
        self.bot._api_call.reset_mock()
        self.join()
        self.join()
        approvals=[c for c in self.bot._api_call.call_args_list if c.args[0]=='approveChatJoinRequest']
        self.assertEqual(1,len(approvals))
        self.assertEqual({'chat_id':-100,'user_id':11},approvals[0].args[1])

    def test_forwarded_link_declines_unknown_or_nonconsenting_account(self):
        self.message('/setuju')
        self.bot._api_call.reset_mock()
        self.join(uid=999)
        self.join(uid=22,update=101)
        self.assertEqual(2,sum(c.args[0]=='declineChatJoinRequest' for c in self.bot._api_call.call_args_list))
        self.assertFalse(any(c.args[0]=='approveChatJoinRequest' for c in self.bot._api_call.call_args_list))

    def test_withdrawn_consent_rechecked_at_join_time(self):
        self.message('/setuju')
        self.message('/tarik',update=2)
        self.bot._api_call.reset_mock()
        self.join()
        self.bot._api_call.assert_called_once_with('declineChatJoinRequest',{'chat_id':-100,'user_id':11})

    def test_other_groups_and_other_admin_links_untouched(self):
        self.message('/setuju')
        self.bot._api_call.reset_mock()
        self.join(chat=-999)
        self.join(link='https://t.me/+another-admin',update=101)
        self.bot._api_call.assert_not_called()

    def test_existing_and_banned_members_are_not_reinvited(self):
        self.o.command(11,{'NIM':'1'},{'id':11,'type':'private'},'/setuju','')
        self.bot._api_call.return_value={'status':'member'}
        self.bot._api_call.side_effect=None
        self.message('/gabung')
        self.assertIn('sudah menjadi anggota',self.bot.send_message.call_args.args[1])
        self.bot._api_call.assert_called_once_with('getChatMember',{'chat_id':-100,'user_id':11})
        self.bot._api_call.return_value={'status':'kicked'}
        self.message('/gabung',update=2)
        self.assertIn('dibatasi administrator',self.bot.send_message.call_args.args[1])

    def test_missing_permission_preserves_consent_and_allows_later_retry(self):
        self.bot._api_call.side_effect=TelegramAPIError('failure')
        self.message('/setuju')
        self.assertTrue(self.o.consent(11))
        self.assertIn('/gabung',self.bot.send_message.call_args.args[1])
        self.bot._api_call.side_effect=self.api
        self.message('/gabung',update=2)
        self.assertIn('https://t.me/',self.bot.send_message.call_args.args[1])
