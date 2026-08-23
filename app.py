"""Entry point for Student Course Services."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from course_service import GitHubRepositoryValidator, ParticipantRegistry
from telegram_bot import TelegramBot


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE entries without overriding process variables."""
    if not path.exists():
        return

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SystemExit(f"Format .env tidak valid pada baris {line_number}.")

        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip()
        if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
            value = value[1:-1]
        if not key:
            raise SystemExit(f"Nama variabel .env kosong pada baris {line_number}.")
        os.environ.setdefault(key, value)


def main() -> None:
    load_env_file(Path(__file__).with_name(".env"))

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    token = os.environ.get("TELEGRAM_BOT_TOKEN_KIPP", "").strip()
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN_KIPP belum diisi di file .env.")

    participant_file = Path(os.environ.get("PESERTA_CSV", "peserta.csv"))
    poll_timeout = int(os.environ.get("TELEGRAM_POLL_TIMEOUT", "30"))
    github_token = os.environ.get("GITHUB_TOKEN", "")
    registry = ParticipantRegistry(
        participant_file,
        repo_validator=GitHubRepositoryValidator(github_token),
    )
    TelegramBot(token, registry, poll_timeout=poll_timeout).run()


if __name__ == "__main__":
    main()
