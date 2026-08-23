"""Minimal Telegram Bot API client and command dispatcher."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from course_service import ParticipantDataError, ParticipantRegistry


LOGGER = logging.getLogger(__name__)

START_MESSAGE = (
    "Selamat datang di Student Course Services II2100.\n\n"
    "Perintah yang tersedia:\n"
    "/reg NIM - hubungkan akun Telegram dengan data peserta\n"
    "/repo URL - simpan atau ganti URL repo GitHub\n"
    "/skor AXX - lihat nilai dan status tugas A01 sampai A15\n"
    "/submit WXX - kirim portfolio minggu W01 sampai W15\n"
    "/status - periksa registrasi dan validitas repo\n\n"
    "Contoh:\n"
    "/reg 18225001\n"
    "/repo https://github.com/pemilik/repo\n\n"
    "Baris pertama README.md repo harus:\n"
    "# Portfolio Mahasiswa KIPP-2"
)


class TelegramAPIError(RuntimeError):
    """Raised when Telegram rejects or cannot complete an API request."""


class TelegramBot:
    def __init__(
        self,
        token: str,
        registry: ParticipantRegistry,
        poll_timeout: int = 30,
    ) -> None:
        self._base_url = f"https://api.telegram.org/bot{token}"
        self.registry = registry
        self.poll_timeout = poll_timeout

    def run(self) -> None:
        offset: int | None = None
        LOGGER.info("Student Course Services bot started")

        while True:
            try:
                updates = self._api_call(
                    "getUpdates",
                    {
                        "timeout": self.poll_timeout,
                        "offset": offset,
                        "allowed_updates": json.dumps(["message"]),
                    },
                    request_timeout=self.poll_timeout + 10,
                )
                for update in updates:
                    offset = update["update_id"] + 1
                    self.handle_update(update)
            except TelegramAPIError as exc:
                LOGGER.warning("Telegram API error: %s", exc)
                time.sleep(3)
            except ParticipantDataError as exc:
                LOGGER.error("Participant data error: %s", exc)
                time.sleep(3)

    def handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message")
        if not isinstance(message, dict):
            return

        text = message.get("text")
        chat = message.get("chat")
        sender = message.get("from")
        if not isinstance(text, str) or not isinstance(chat, dict) or not isinstance(sender, dict):
            return

        chat_id = chat.get("id")
        telegram_id = sender.get("id")
        if not isinstance(chat_id, int) or not isinstance(telegram_id, int):
            return

        command, arguments = self._parse_command(text)

        if command == "/start":
            self.send_message(chat_id, START_MESSAGE)
        elif command == "/reg":
            if len(arguments) != 1:
                self.send_message(chat_id, "Gunakan format: /reg NIM")
                return
            result = self.registry.register(arguments[0], telegram_id)
            self.send_message(chat_id, result.message)
        elif command == "/repo":
            if len(arguments) != 1:
                self.send_message(chat_id, "Gunakan format: /repo URL")
                return
            result = self.registry.set_repo(telegram_id, arguments[0])
            self.send_message(chat_id, result.message)
        elif command == "/status":
            if arguments:
                self.send_message(chat_id, "Gunakan format: /status")
                return
            result = self.registry.status(telegram_id)
            self.send_message(chat_id, result.message)
        elif command == "/skor":
            if len(arguments) != 1:
                self.send_message(chat_id, "Gunakan format: /skor AXX (A01 sampai A15)")
                return
            result = self.registry.score(telegram_id, arguments[0])
            self.send_message(chat_id, result.message)
        elif command == "/submit":
            if len(arguments) != 1:
                self.send_message(
                    chat_id,
                    "Gunakan format: /submit WXX (W01 sampai W15)",
                )
                return
            result = self.registry.submit(telegram_id, arguments[0])
            self.send_message(chat_id, result.message)
        elif command:
            self.send_message(
                chat_id,
                "Perintah belum dikenali. Gunakan /start untuk melihat petunjuk.",
            )

    def send_message(self, chat_id: int, text: str) -> None:
        self._api_call("sendMessage", {"chat_id": chat_id, "text": text})

    @staticmethod
    def _parse_command(text: str) -> tuple[str, list[str]]:
        parts = text.strip().split()
        if not parts or not parts[0].startswith("/"):
            return "", []

        command = parts[0].split("@", maxsplit=1)[0].lower()
        return command, parts[1:]

    def _api_call(
        self,
        method: str,
        parameters: dict[str, Any],
        request_timeout: int = 15,
    ) -> Any:
        data = urllib.parse.urlencode(parameters).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/{method}",
            data=data,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=request_timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise TelegramAPIError(str(exc)) from exc

        if not payload.get("ok"):
            raise TelegramAPIError(payload.get("description", "Unknown Telegram API error"))
        return payload["result"]
