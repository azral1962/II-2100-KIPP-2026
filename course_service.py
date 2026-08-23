"""Core registration service for the II2100 Telegram bot."""

from __future__ import annotations

import csv
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


REQUIRED_COLUMNS = ("NIM", "Nama", "ID", "repo")
GITHUB_OWNER_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
GITHUB_REPO_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
REQUIRED_README_FIRST_LINE = "# Portfolio Mahasiswa KIPP-2"


class ParticipantDataError(RuntimeError):
    """Raised when the participant CSV cannot be used safely."""


@dataclass(frozen=True)
class RegistrationResult:
    status: str
    message: str


@dataclass(frozen=True)
class RepoValidationResult:
    status: str
    message: str

    @property
    def is_valid(self) -> bool:
        return self.status == "valid"


def normalize_github_repo_url(url: str) -> str | None:
    """Return a canonical GitHub repository URL, or None for invalid input."""
    candidate = url.strip()
    try:
        parsed = urllib.parse.urlsplit(candidate)
        port = parsed.port
    except ValueError:
        return None

    if (
        parsed.scheme.lower() != "https"
        or parsed.hostname not in {"github.com", "www.github.com"}
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return None

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) != 2:
        return None

    owner, repo = path_parts
    if repo.lower().endswith(".git"):
        repo = repo[:-4]
    if not GITHUB_OWNER_PATTERN.fullmatch(owner) or not GITHUB_REPO_PATTERN.fullmatch(repo):
        return None
    if repo in {".", ".."}:
        return None

    return f"https://github.com/{owner}/{repo}"


class GitHubRepositoryValidator:
    """Validate the first line of a repository README through GitHub's API."""

    def __init__(self, token: str = "", timeout: int = 10) -> None:
        self.token = token.strip()
        self.timeout = timeout

    def validate(self, repo_url: str) -> RepoValidationResult:
        normalized_url = normalize_github_repo_url(repo_url)
        if normalized_url is None:
            return RepoValidationResult("invalid_url", "Format URL GitHub tidak valid.")

        owner, repo = normalized_url.removeprefix("https://github.com/").split("/", 1)
        request = urllib.request.Request(
            f"https://api.github.com/repos/{owner}/{repo}/readme",
            headers={
                "Accept": "application/vnd.github.raw+json",
                "User-Agent": "II2100-Student-Course-Services",
                "X-GitHub-Api-Version": "2026-03-10",
            },
            method="GET",
        )
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                readme = response.read(8192).decode("utf-8-sig")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return RepoValidationResult(
                    "not_found",
                    "Repo atau README.md tidak ditemukan di GitHub.",
                )
            return RepoValidationResult(
                "unavailable",
                f"GitHub tidak dapat memvalidasi repo saat ini (HTTP {exc.code}).",
            )
        except (urllib.error.URLError, TimeoutError, UnicodeDecodeError):
            return RepoValidationResult(
                "unavailable",
                "GitHub tidak dapat memvalidasi repo saat ini.",
            )

        lines = readme.splitlines()
        first_line = lines[0].strip() if lines else ""
        if first_line != REQUIRED_README_FIRST_LINE:
            return RepoValidationResult(
                "invalid_readme",
                f"Baris pertama README.md harus tepat: {REQUIRED_README_FIRST_LINE}",
            )

        return RepoValidationResult("valid", "Repo dan README.md valid.")


class ParticipantRegistry:
    """Read and update Telegram registrations in a participant CSV file."""

    def __init__(
        self,
        csv_path: str | Path,
        repo_validator: GitHubRepositoryValidator | None = None,
    ) -> None:
        self.csv_path = Path(csv_path)
        self._lock = threading.Lock()
        self.repo_validator = repo_validator or GitHubRepositoryValidator()

    def register(self, nim: str, telegram_id: int) -> RegistrationResult:
        normalized_nim = nim.strip()
        telegram_id_text = str(telegram_id)

        if not normalized_nim.isdigit():
            return RegistrationResult(
                "invalid_nim",
                "Format NIM tidak valid. Gunakan: /reg NIM",
            )

        with self._lock:
            fieldnames, rows = self._read_rows()
            participant = next(
                (row for row in rows if row["NIM"].strip() == normalized_nim),
                None,
            )

            if participant is None:
                return RegistrationResult(
                    "not_found",
                    "NIM tidak ditemukan dalam daftar peserta kelas.",
                )

            current_id = participant["ID"].strip()
            if current_id == telegram_id_text:
                return RegistrationResult(
                    "already_registered",
                    f"Anda sudah terdaftar sebagai {participant['Nama']} ({normalized_nim}).",
                )

            if current_id:
                return RegistrationResult(
                    "nim_taken",
                    "NIM tersebut sudah terhubung ke akun Telegram lain. Hubungi instruktur jika perlu koreksi.",
                )

            telegram_id_owner = next(
                (
                    row
                    for row in rows
                    if row["ID"].strip() == telegram_id_text
                    and row["NIM"].strip() != normalized_nim
                ),
                None,
            )
            if telegram_id_owner is not None:
                return RegistrationResult(
                    "telegram_id_taken",
                    "Akun Telegram ini sudah terhubung ke NIM lain. Hubungi instruktur jika perlu koreksi.",
                )

            participant["ID"] = telegram_id_text
            self._write_rows(fieldnames, rows)

            return RegistrationResult(
                "registered",
                f"Registrasi berhasil. Selamat datang, {participant['Nama']} ({normalized_nim}).",
            )

    def set_repo(self, telegram_id: int, repo_url: str) -> RegistrationResult:
        telegram_id_text = str(telegram_id)
        normalized_url = normalize_github_repo_url(repo_url)
        if normalized_url is None:
            return RegistrationResult(
                "invalid_repo",
                "URL repo tidak valid. Gunakan URL seperti: https://github.com/pemilik/repo",
            )

        with self._lock:
            fieldnames, rows = self._read_rows()
            participant = next(
                (row for row in rows if row["ID"].strip() == telegram_id_text),
                None,
            )
            if participant is None:
                return RegistrationResult(
                    "not_registered",
                    "Akun Telegram ini belum terdaftar. Daftar dahulu dengan /reg NIM.",
                )

            validation = self.repo_validator.validate(normalized_url)
            if not validation.is_valid:
                return RegistrationResult(validation.status, validation.message)

            action = "diperbarui" if participant["repo"].strip() else "disimpan"
            participant["repo"] = normalized_url
            self._write_rows(fieldnames, rows)
            return RegistrationResult(
                "repo_saved",
                f"URL repo berhasil {action}: {normalized_url}",
            )

    def status(self, telegram_id: int) -> RegistrationResult:
        telegram_id_text = str(telegram_id)

        with self._lock:
            _, rows = self._read_rows()
            participant = next(
                (row for row in rows if row["ID"].strip() == telegram_id_text),
                None,
            )

        if participant is None:
            return RegistrationResult(
                "not_registered",
                "Status: belum terdaftar.\nDaftar dengan /reg NIM.",
            )

        identity = f"{participant['Nama']} ({participant['NIM']})"
        repo_url = participant["repo"].strip()
        if not repo_url:
            return RegistrationResult(
                "registered_without_repo",
                f"Status: terdaftar sebagai {identity}.\nRepo: belum diisi. Gunakan /repo URL.",
            )

        if normalize_github_repo_url(repo_url) is None:
            return RegistrationResult(
                "registered_with_invalid_repo",
                f"Status: terdaftar sebagai {identity}.\nRepo: tidak valid. Perbarui dengan /repo URL.",
            )

        validation = self.repo_validator.validate(repo_url)
        if validation.status == "unavailable":
            return RegistrationResult(
                "registered_repo_unavailable",
                f"Status: terdaftar sebagai {identity}.\nRepo: belum dapat diperiksa ({validation.message})",
            )
        if not validation.is_valid:
            return RegistrationResult(
                "registered_with_invalid_repo",
                f"Status: terdaftar sebagai {identity}.\nRepo: tidak valid. {validation.message}",
            )

        return RegistrationResult(
            "registered_with_valid_repo",
            f"Status: terdaftar sebagai {identity}.\nRepo: valid, README.md sesuai ({repo_url})",
        )

    def _read_rows(self) -> tuple[list[str], list[dict[str, str]]]:
        try:
            with self.csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                fieldnames = reader.fieldnames
                if fieldnames is None:
                    raise ParticipantDataError("File peserta tidak memiliki header.")

                missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
                if missing:
                    raise ParticipantDataError(
                        "Kolom wajib tidak ditemukan: " + ", ".join(missing)
                    )

                rows = [
                    {column: (value or "") for column, value in row.items()}
                    for row in reader
                ]
        except FileNotFoundError as exc:
            raise ParticipantDataError(
                f"File peserta tidak ditemukan: {self.csv_path}"
            ) from exc
        except OSError as exc:
            raise ParticipantDataError(
                f"File peserta tidak dapat dibaca: {self.csv_path}"
            ) from exc

        return fieldnames, rows

    def _write_rows(self, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="",
                dir=self.csv_path.parent,
                prefix=f".{self.csv_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                writer = csv.DictWriter(
                    temporary_file,
                    fieldnames=fieldnames,
                    extrasaction="ignore",
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(rows)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            os.replace(temporary_path, self.csv_path)
        except OSError as exc:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise ParticipantDataError(
                f"File peserta tidak dapat diperbarui: {self.csv_path}"
            ) from exc
