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
    # Import ditunda untuk menghindari siklus: llm.py memakai helper path/env
    # dari modul ini saat dijalankan sebagai CLI mandiri.
    from llm import (
        DEFAULT_SERVER_URL,
        AssessmentWorker,
        LlamaCppClient,
        _boolean_env,
        _positive_int,
        fetch_portfolio_page,
    )

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
    llm_prompt_file = resolve_project_path(
        project_dir,
        os.environ.get("LLM_PROMPT_FILE", "llm-assessment-prompts.md"),
    )
    llm_input_dir = resolve_project_path(
        project_dir,
        os.environ.get("LLM_INPUT_DIR", "assessment-inputs"),
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
    page_timeout = _positive_int("LLM_PAGE_TIMEOUT", "30")
    page_max_bytes = _positive_int("LLM_PAGE_MAX_BYTES", "2000000")
    llm_worker = AssessmentWorker(
        queue_path=queue_file,
        assessment_path=assessment_file,
        participant_path=participant_file,
        prompt_path=llm_prompt_file,
        input_dir=llm_input_dir,
        report_dir=llm_report_dir,
        client=LlamaCppClient(
            server_url=os.environ.get("LLM_SERVER_URL", DEFAULT_SERVER_URL),
            model=os.environ.get("LLM_MODEL", ""),
            api_key=os.environ.get("LLM_API_KEY", ""),
            timeout=_positive_int("LLM_REQUEST_TIMEOUT", "300"),
            max_tokens=_positive_int("LLM_MAX_TOKENS", "4096"),
            temperature=float(os.environ.get("LLM_TEMPERATURE", "0.1")),
            enable_thinking=_boolean_env("LLM_ENABLE_THINKING", False),
        ),
        page_loader=lambda url: fetch_portfolio_page(
            url,
            timeout=page_timeout,
            max_bytes=page_max_bytes,
        ),
        max_evidence_chars=_positive_int("LLM_MAX_EVIDENCE_CHARS", "100000"),
        auto_approve=_boolean_env("LLM_AUTO_APPROVE", False),
        lease_seconds=_positive_int("LLM_LEASE_SECONDS", "900"),
    )
    try:
        TelegramBot(
            token,
            registry,
            poll_timeout=poll_timeout,
            offset_path=offset_file,
            llm_processor=llm_worker.process_ticket_number,
        ).run()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Student Course Services bot dihentikan.")


if __name__ == "__main__":
    main()
