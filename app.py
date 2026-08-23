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


def resolve_project_path(project_dir: Path, value: str) -> Path:
    """Resolve relative runtime paths against the application directory."""
    path = Path(value)
    return path if path.is_absolute() else project_dir / path


def main() -> None:
    project_dir = Path(__file__).resolve().parent
    load_env_file(project_dir / ".env")

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    token = os.environ.get("TELEGRAM_BOT_TOKEN_KIPP", "").strip()
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN_KIPP belum diisi di file .env.")

    participant_file = resolve_project_path(
        project_dir, os.environ.get("PESERTA_CSV", "peserta.csv")
    )
    assessment_file = resolve_project_path(
        project_dir, os.environ.get("ASSESSMENT_CSV", "assessment.csv")
    )
    queue_file = resolve_project_path(
        project_dir, os.environ.get("ANTRIAN_CSV", "antrian.csv")
    )
    offset_file = resolve_project_path(
        project_dir,
        os.environ.get("TELEGRAM_OFFSET_FILE", "telegram-offset.txt"),
    )
    llm_report_dir = resolve_project_path(
        project_dir,
        os.environ.get("LLM_REPORT_DIR", "assessment-results"),
    )
    try:
        poll_timeout = int(os.environ.get("TELEGRAM_POLL_TIMEOUT", "30"))
    except ValueError as exc:
        raise SystemExit(
            "TELEGRAM_POLL_TIMEOUT harus berupa bilangan bulat positif."
        ) from exc
    if poll_timeout <= 0:
        raise SystemExit("TELEGRAM_POLL_TIMEOUT harus berupa bilangan bulat positif.")
    github_token = os.environ.get("GITHUB_TOKEN", "")
    registry = ParticipantRegistry(
        participant_file,
        repo_validator=GitHubRepositoryValidator(github_token),
        assessment_csv_path=assessment_file,
        queue_csv_path=queue_file,
        llm_report_dir=llm_report_dir,
    )
    try:
        TelegramBot(
            token,
            registry,
            poll_timeout=poll_timeout,
            offset_path=offset_file,
        ).run()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Student Course Services bot dihentikan.")


if __name__ == "__main__":
    main()
