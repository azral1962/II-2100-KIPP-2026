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
from decimal import Decimal, InvalidOperation
from pathlib import Path

from file_lock import exclusive_file_lock


REQUIRED_COLUMNS = ("NIM", "Nama", "ID", "repo")
ASSESSMENT_CODES = tuple(f"A{number:02d}" for number in range(1, 16))
REQUIRED_ASSESSMENT_COLUMNS = ("NIM", "name", *ASSESSMENT_CODES, "TOTAL")
QUEUE_COLUMNS = ("tiket", "nim", "week", "url", "skor", "status")
GITHUB_OWNER_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
GITHUB_REPO_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
REQUIRED_README_FIRST_LINE = "# Portfolio Mahasiswa KIPP-2026"


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


@dataclass(frozen=True)
class PageValidationResult:
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


def build_portfolio_url(repo_url: str, week_code: str) -> str | None:
    """Build a GitHub Pages portfolio URL from a canonical GitHub repo URL."""
    normalized_url = normalize_github_repo_url(repo_url)
    code = week_code.strip().upper()
    if normalized_url is None or not re.fullmatch(r"W(?:0[1-9]|1[0-5])", code):
        return None

    owner, repo = normalized_url.removeprefix("https://github.com/").split("/", 1)
    owner_host = owner.lower()
    if repo.lower() == f"{owner_host}.github.io":
        repo_path = ""
    else:
        repo_path = f"/{repo}"
    week_number = code[1:]
    return f"https://{owner_host}.github.io{repo_path}/portfolio/week-{week_number}.html"


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


class PortfolioPageValidator:
    """Check that a public portfolio page is reachable."""

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    def validate(self, page_url: str) -> PageValidationResult:
        request = urllib.request.Request(
            page_url,
            headers={"User-Agent": "II2100-Student-Course-Services"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    return PageValidationResult(
                        "unavailable",
                        f"Halaman portfolio merespons HTTP {status}.",
                    )
                response.read(1)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return PageValidationResult(
                    "not_found",
                    "Halaman portfolio belum ditemukan.",
                )
            return PageValidationResult(
                "unavailable",
                f"Halaman portfolio tidak dapat diperiksa (HTTP {exc.code}).",
            )
        except (urllib.error.URLError, TimeoutError):
            return PageValidationResult(
                "unavailable",
                "Halaman portfolio tidak dapat diperiksa saat ini.",
            )

        return PageValidationResult("valid", "Halaman portfolio valid.")


class ParticipantRegistry:
    """Read and update Telegram registrations in a participant CSV file."""

    def __init__(
        self,
        csv_path: str | Path,
        repo_validator: GitHubRepositoryValidator | None = None,
        assessment_csv_path: str | Path = "assessment.csv",
        queue_csv_path: str | Path = "antrian.csv",
        page_validator: PortfolioPageValidator | None = None,
    ) -> None:
        self.csv_path = Path(csv_path)
        self.assessment_csv_path = Path(assessment_csv_path)
        self.queue_csv_path = Path(queue_csv_path)
        self._lock = threading.Lock()
        self.repo_validator = repo_validator or GitHubRepositoryValidator()
        self.page_validator = page_validator or PortfolioPageValidator()

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

    def score(self, telegram_id: int, assessment_code: str) -> RegistrationResult:
        code = assessment_code.strip().upper()
        if code not in ASSESSMENT_CODES:
            return RegistrationResult(
                "invalid_assessment_code",
                "Kode tugas tidak valid. Gunakan A01 sampai A15, misalnya: /skor A01",
            )

        telegram_id_text = str(telegram_id)
        with self._lock:
            _, participant_rows = self._read_rows()
            participant = next(
                (
                    row
                    for row in participant_rows
                    if row["ID"].strip() == telegram_id_text
                ),
                None,
            )

        if participant is None:
            return RegistrationResult(
                "not_registered",
                "Akun Telegram ini belum terdaftar. Daftar dahulu dengan /reg NIM.",
            )

        assessment_rows = self._read_assessment_rows()
        nim = participant["NIM"].strip()
        assessment = next(
            (row for row in assessment_rows if row["NIM"].strip() == nim),
            None,
        )
        if assessment is None:
            return RegistrationResult(
                "assessment_not_found",
                "Data nilai untuk NIM Anda tidak ditemukan. Hubungi instruktur.",
            )

        raw_score = assessment[code].strip()
        if not raw_score:
            return RegistrationResult(
                "score_empty",
                f"Nilai {code} masih kosong. Kerjakan {code} terlebih dahulu.",
            )

        try:
            numeric_score = Decimal(raw_score.replace(",", "."))
        except InvalidOperation:
            return RegistrationResult(
                "score_invalid",
                f"Nilai {code} tidak valid. Hubungi instruktur.",
            )
        if not numeric_score.is_finite():
            return RegistrationResult(
                "score_invalid",
                f"Nilai {code} tidak valid. Hubungi instruktur.",
            )

        if numeric_score < Decimal("3.0"):
            return RegistrationResult(
                "revision_required",
                f"Nilai {code}: {raw_score}\nStatus: revisi.",
            )

        return RegistrationResult(
            "achieved",
            f"Nilai {code}: {raw_score}\nStatus: tercapai.",
        )

    def submit(self, telegram_id: int, week_code: str) -> RegistrationResult:
        code = week_code.strip().upper()
        if not re.fullmatch(r"W(?:0[1-9]|1[0-5])", code):
            return RegistrationResult(
                "invalid_week",
                "Kode minggu tidak valid. Gunakan W01 sampai W15, misalnya: /submit W01",
            )

        telegram_id_text = str(telegram_id)
        with self._lock:
            _, participant_rows = self._read_rows()
            participant = next(
                (
                    row
                    for row in participant_rows
                    if row["ID"].strip() == telegram_id_text
                ),
                None,
            )

        if participant is None:
            return RegistrationResult(
                "not_registered",
                "Akun Telegram ini belum terdaftar. Daftar dahulu dengan /reg NIM.",
            )

        page_url = build_portfolio_url(participant["repo"], code)
        if page_url is None:
            return RegistrationResult(
                "repo_missing_or_invalid",
                "Repo belum terdaftar atau tidak valid. Gunakan /repo URL terlebih dahulu.",
            )

        validation = self.page_validator.validate(page_url)
        if not validation.is_valid:
            return RegistrationResult(validation.status, validation.message)

        with self._lock:
            with exclusive_file_lock(self.queue_csv_path):
                queue_rows = self._read_queue_rows()
                ticket_numbers: list[int] = []
                for row in queue_rows:
                    raw_ticket = row["tiket"].strip()
                    if not raw_ticket.isdigit() or int(raw_ticket) < 1:
                        raise ParticipantDataError(
                            "Kolom tiket pada file antrian harus berupa bilangan positif."
                        )
                    ticket_numbers.append(int(raw_ticket))

                ticket = max(ticket_numbers, default=0) + 1
                queue_rows.append(
                    {
                        "tiket": str(ticket),
                        "nim": participant["NIM"].strip(),
                        "week": code,
                        "url": page_url,
                        "skor": "",
                        "status": "ANTRI",
                    }
                )
                self._write_queue_rows(queue_rows)

        return RegistrationResult(
            "queued",
            f"Tiket: {ticket}\nStatus: ANTRI\nURL: {page_url}",
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

    def _read_assessment_rows(self) -> list[dict[str, str]]:
        try:
            with self.assessment_csv_path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as csv_file:
                reader = csv.DictReader(csv_file)
                fieldnames = reader.fieldnames
                if fieldnames is None:
                    raise ParticipantDataError("File assessment tidak memiliki header.")

                missing = [
                    column
                    for column in REQUIRED_ASSESSMENT_COLUMNS
                    if column not in fieldnames
                ]
                if missing:
                    raise ParticipantDataError(
                        "Kolom assessment wajib tidak ditemukan: " + ", ".join(missing)
                    )

                return [
                    {column: (value or "") for column, value in row.items()}
                    for row in reader
                ]
        except FileNotFoundError as exc:
            raise ParticipantDataError(
                f"File assessment tidak ditemukan: {self.assessment_csv_path}"
            ) from exc
        except OSError as exc:
            raise ParticipantDataError(
                f"File assessment tidak dapat dibaca: {self.assessment_csv_path}"
            ) from exc

    def _read_queue_rows(self) -> list[dict[str, str]]:
        try:
            with self.queue_csv_path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as csv_file:
                reader = csv.DictReader(csv_file)
                fieldnames = reader.fieldnames
                if fieldnames is None:
                    raise ParticipantDataError("File antrian tidak memiliki header.")

                missing = [column for column in QUEUE_COLUMNS if column not in fieldnames]
                if missing:
                    raise ParticipantDataError(
                        "Kolom antrian wajib tidak ditemukan: " + ", ".join(missing)
                    )

                return [
                    {column: (value or "") for column, value in row.items()}
                    for row in reader
                ]
        except FileNotFoundError as exc:
            raise ParticipantDataError(
                f"File antrian tidak ditemukan: {self.queue_csv_path}"
            ) from exc
        except OSError as exc:
            raise ParticipantDataError(
                f"File antrian tidak dapat dibaca: {self.queue_csv_path}"
            ) from exc

    def _write_queue_rows(self, rows: list[dict[str, str]]) -> None:
        self.queue_csv_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="",
                dir=self.queue_csv_path.parent,
                prefix=f".{self.queue_csv_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                writer = csv.DictWriter(
                    temporary_file,
                    fieldnames=QUEUE_COLUMNS,
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(rows)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            os.replace(temporary_path, self.queue_csv_path)
        except OSError as exc:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise ParticipantDataError(
                f"File antrian tidak dapat diperbarui: {self.queue_csv_path}"
            ) from exc

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
