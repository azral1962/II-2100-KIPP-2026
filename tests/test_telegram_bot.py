import unittest
from unittest.mock import Mock

from course_service import RegistrationResult
from telegram_bot import START_MESSAGE, TelegramBot


class TelegramBotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = Mock()
        self.bot = TelegramBot("test-token", self.registry)
        self.bot.send_message = Mock()

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


if __name__ == "__main__":
    unittest.main()
