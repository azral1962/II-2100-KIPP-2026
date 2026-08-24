import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from course_service import (
    REQUIRED_README_FIRST_LINE,
    ParticipantDataError,
    RegistrationResult,
)
from telegram_bot import START_MESSAGE, TelegramBot


class TelegramBotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = Mock()
        self.bot = TelegramBot("test-token", self.registry)
        self.bot.send_message = Mock()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @staticmethod
    def update(text: str, telegram_id: int = 123) -> dict:
        return {
            "update_id": 1,
            "message": {
                "text": text,
                "chat": {"id": 456},
                "from": {"id": telegram_id},
            },
        }

    def test_start_shows_registration_instructions(self) -> None:
        self.bot.handle_update(self.update("/start"))

        self.bot.send_message.assert_called_once_with(456, START_MESSAGE)
        self.assertIn(REQUIRED_README_FIRST_LINE, START_MESSAGE)
        self.assertIn("/llm TICKET", START_MESSAGE)

    def test_reg_uses_telegram_sender_id(self) -> None:
        self.registry.register.return_value = RegistrationResult("registered", "OK")

        self.bot.handle_update(self.update("/reg 18225001", telegram_id=789))

        self.registry.register.assert_called_once_with("18225001", 789)
        self.bot.send_message.assert_called_once_with(456, "OK")

    def test_reg_accepts_group_command_suffix(self) -> None:
        self.registry.register.return_value = RegistrationResult("registered", "OK")

        self.bot.handle_update(self.update("/reg@CourseBot 18225001"))

        self.registry.register.assert_called_once_with("18225001", 123)

    def test_reg_requires_exactly_one_argument(self) -> None:
        self.bot.handle_update(self.update("/reg"))

        self.registry.register.assert_not_called()
        self.bot.send_message.assert_called_once_with(456, "Gunakan format: /reg NIM")

    def test_repo_uses_sender_id_and_url(self) -> None:
        self.registry.set_repo.return_value = RegistrationResult("repo_saved", "OK")

        self.bot.handle_update(
            self.update("/repo https://github.com/example/course", telegram_id=789)
        )

        self.registry.set_repo.assert_called_once_with(
            789,
            "https://github.com/example/course",
        )
        self.bot.send_message.assert_called_once_with(456, "OK")

    def test_repo_requires_exactly_one_argument(self) -> None:
        self.bot.handle_update(self.update("/repo"))

        self.registry.set_repo.assert_not_called()
        self.bot.send_message.assert_called_once_with(456, "Gunakan format: /repo URL")

    def test_status_uses_sender_id(self) -> None:
        self.registry.status.return_value = RegistrationResult(
            "registered_without_repo",
            "STATUS",
        )

        self.bot.handle_update(self.update("/status", telegram_id=789))

        self.registry.status.assert_called_once_with(789)
        self.bot.send_message.assert_called_once_with(456, "STATUS")

    def test_status_rejects_arguments(self) -> None:
        self.bot.handle_update(self.update("/status now"))

        self.registry.status.assert_not_called()
        self.bot.send_message.assert_called_once_with(456, "Gunakan format: /status")

    def test_score_uses_sender_id_and_assessment_code(self) -> None:
        self.registry.score.return_value = RegistrationResult(
            "achieved",
            "Nilai A01: 3.0\nStatus: tercapai.",
        )

        self.bot.handle_update(self.update("/skor A01", telegram_id=789))

        self.registry.score.assert_called_once_with(789, "A01")
        self.bot.send_message.assert_called_once_with(
            456,
            "Nilai A01: 3.0\nStatus: tercapai.",
        )

    def test_score_requires_exactly_one_argument(self) -> None:
        self.bot.handle_update(self.update("/skor"))

        self.registry.score.assert_not_called()
        self.bot.send_message.assert_called_once_with(
            456,
            "Gunakan format: /skor AXX (A01 sampai A15)",
        )

    def test_submit_uses_sender_id_and_week(self) -> None:
        self.registry.submit.return_value = RegistrationResult(
            "queued",
            "Tiket: 1\nStatus: ANTRI\nURL: https://example.github.io/course/portfolio/week-01.html",
        )

        self.bot.handle_update(self.update("/submit W01", telegram_id=789))

        self.registry.submit.assert_called_once_with(789, "W01")
        self.bot.send_message.assert_called_once_with(
            456,
            "Tiket: 1\nStatus: ANTRI\nURL: https://example.github.io/course/portfolio/week-01.html",
        )

    def test_submit_requires_exactly_one_argument(self) -> None:
        self.bot.handle_update(self.update("/submit"))

        self.registry.submit.assert_not_called()
        self.bot.send_message.assert_called_once_with(
            456,
            "Gunakan format: /submit WXX (W01 sampai W15)",
        )

    def test_queue_status_uses_sender_id(self) -> None:
        self.registry.queue_status.return_value = RegistrationResult(
            "queue_status", "STATUS ANTRIAN"
        )

        self.bot.handle_update(self.update("/antrian", telegram_id=789))

        self.registry.queue_status.assert_called_once_with(789)
        self.bot.send_message.assert_called_once_with(456, "STATUS ANTRIAN")

    def test_result_uses_sender_id_and_week(self) -> None:
        self.registry.result.return_value = RegistrationResult("result", "HASIL")

        self.bot.handle_update(self.update("/hasil W02", telegram_id=789))

        self.registry.result.assert_called_once_with(789, "W02")
        self.bot.send_message.assert_called_once_with(456, "HASIL")

    def test_llm_result_uses_sender_id_and_ticket(self) -> None:
        self.registry.llm_result.side_effect = (
            RegistrationResult("llm_result", "STATUS AWAL"),
            RegistrationResult("llm_result", "HASIL LLM"),
        )
        processor = Mock(return_value=(1, 0))
        self.bot.llm_processor = processor

        self.bot.handle_update(self.update("/llm 7", telegram_id=789))

        self.registry.llm_result.assert_has_calls(
            [call(789, "7"), call(789, "7")]
        )
        processor.assert_called_once_with("7")
        self.bot.send_message.assert_has_calls(
            [
                call(456, "Permintaan LLM tiket 7 diterima. Memeriksa antrean..."),
                call(456, "HASIL LLM"),
            ]
        )

    def test_llm_does_not_process_ticket_not_owned_by_sender(self) -> None:
        self.registry.llm_result.return_value = RegistrationResult(
            "ticket_not_found", "Tiket tidak ditemukan pada submission milik Anda."
        )
        processor = Mock()
        self.bot.llm_processor = processor

        self.bot.handle_update(self.update("/llm 7", telegram_id=789))

        processor.assert_not_called()
        self.registry.llm_result.assert_called_once_with(789, "7")
        self.bot.send_message.assert_called_once_with(
            456, "Tiket tidak ditemukan pada submission milik Anda."
        )

    def test_llm_result_requires_exactly_one_ticket(self) -> None:
        self.bot.handle_update(self.update("/llm"))

        self.registry.llm_result.assert_not_called()
        self.bot.send_message.assert_called_once_with(
            456,
            "Gunakan format: /llm TICKET, contoh: /llm 7",
        )

    def test_successful_update_persists_next_offset(self) -> None:
        offset_path = Path(self.temp_dir.name) / "offset.txt"
        bot = TelegramBot(
            "test-token",
            self.registry,
            poll_timeout=1,
            offset_path=offset_path,
        )
        bot.handle_update = Mock()
        bot._api_call = Mock(side_effect=[[self.update("/status")], KeyboardInterrupt])

        with self.assertRaises(KeyboardInterrupt):
            bot.run()

        self.assertEqual("2", offset_path.read_text(encoding="ascii"))

    def test_failed_update_does_not_advance_offset(self) -> None:
        offset_path = Path(self.temp_dir.name) / "offset.txt"
        bot = TelegramBot(
            "test-token",
            self.registry,
            poll_timeout=1,
            offset_path=offset_path,
        )
        bot._api_call = Mock(return_value=[self.update("/status")])
        bot.handle_update = Mock(side_effect=ParticipantDataError("CSV terkunci"))

        with patch("telegram_bot.time.sleep", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                bot.run()

        self.assertFalse(offset_path.exists())


if __name__ == "__main__":
    unittest.main()
