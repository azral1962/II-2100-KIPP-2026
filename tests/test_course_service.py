import csv
import tempfile
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

from course_service import (
    ASSESSMENT_CODES,
    REQUIRED_README_FIRST_LINE,
    GitHubRepositoryValidator,
    PageValidationResult,
    ParticipantRegistry,
    RepoValidationResult,
    build_portfolio_url,
    normalize_github_repo_url,
)


class ParticipantRegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "peserta.csv"
        with self.csv_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file, lineterminator="\n")
            writer.writerow(["NIM", "Nama", "ID", "repo"])
            writer.writerow(["18225001", "Kezia Josephine Manik", "", ""])
            writer.writerow(["18225003", "Erin Cherryl Angela", "200", ""])
        self.assessment_path = Path(self.temp_dir.name) / "assessment.csv"
        with self.assessment_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as csv_file:
            writer = csv.writer(csv_file, lineterminator="\n")
            writer.writerow(["NIM", "name", *ASSESSMENT_CODES, "TOTAL"])
            scores = {code: "" for code in ASSESSMENT_CODES}
            scores.update(
                {
                    "A01": "2.5",
                    "A02": "3.0",
                    "A04": "bukan-angka",
                    "A05": "2,75",
                }
            )
            writer.writerow(
                [
                    "18225001",
                    "Kezia Josephine Manik",
                    *(scores[code] for code in ASSESSMENT_CODES),
                    "",
                ]
            )
            writer.writerow(
                [
                    "18225003",
                    "Erin Cherryl Angela",
                    *("" for _ in ASSESSMENT_CODES),
                    "",
                ]
            )
        self.repo_validator = Mock()
        self.repo_validator.validate.return_value = RepoValidationResult(
            "valid",
            "Repo dan README.md valid.",
        )
        self.page_validator = Mock()
        self.page_validator.validate.return_value = PageValidationResult(
            "valid",
            "Halaman portfolio valid.",
        )
        self.queue_path = Path(self.temp_dir.name) / "antrian.csv"
        self.report_dir = Path(self.temp_dir.name) / "assessment-results"
        with self.queue_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file, lineterminator="\n")
            writer.writerow(["tiket", "nim", "week", "url", "skor", "status"])
        self.registry = ParticipantRegistry(
            self.csv_path,
            repo_validator=self.repo_validator,
            assessment_csv_path=self.assessment_path,
            queue_csv_path=self.queue_path,
            page_validator=self.page_validator,
            llm_report_dir=self.report_dir,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def read_rows(self) -> list[dict[str, str]]:
        with self.csv_path.open(encoding="utf-8", newline="") as csv_file:
            return list(csv.DictReader(csv_file))

    def read_queue_rows(self) -> list[dict[str, str]]:
        with self.queue_path.open(encoding="utf-8", newline="") as csv_file:
            return list(csv.DictReader(csv_file))

    def test_registers_known_nim_with_telegram_id(self) -> None:
        result = self.registry.register("18225001", 100)

        self.assertEqual("registered", result.status)
        self.assertEqual("100", self.read_rows()[0]["ID"])

    def test_repeating_same_registration_is_idempotent(self) -> None:
        self.registry.register("18225001", 100)

        result = self.registry.register("18225001", 100)

        self.assertEqual("already_registered", result.status)

    def test_rejects_unknown_nim(self) -> None:
        result = self.registry.register("99999999", 100)

        self.assertEqual("not_found", result.status)
        self.assertEqual("", self.read_rows()[0]["ID"])

    def test_rejects_takeover_of_registered_nim(self) -> None:
        result = self.registry.register("18225003", 999)

        self.assertEqual("nim_taken", result.status)
        self.assertEqual("200", self.read_rows()[1]["ID"])

    def test_rejects_one_telegram_id_for_two_nims(self) -> None:
        result = self.registry.register("18225001", 200)

        self.assertEqual("telegram_id_taken", result.status)
        self.assertEqual("", self.read_rows()[0]["ID"])

    def test_rejects_non_numeric_nim(self) -> None:
        result = self.registry.register("abc", 100)

        self.assertEqual("invalid_nim", result.status)

    def test_saves_repo_for_registered_telegram_id(self) -> None:
        self.registry.register("18225001", 100)

        result = self.registry.set_repo(100, "https://www.github.com/example/course.git/")

        self.assertEqual("repo_saved", result.status)
        self.assertEqual(
            "https://github.com/example/course",
            self.read_rows()[0]["repo"],
        )

    def test_replaces_existing_repo(self) -> None:
        self.registry.register("18225001", 100)
        self.registry.set_repo(100, "https://github.com/example/old")

        result = self.registry.set_repo(100, "https://github.com/example/new")

        self.assertEqual("repo_saved", result.status)
        self.assertIn("diperbarui", result.message)
        self.assertEqual("https://github.com/example/new", self.read_rows()[0]["repo"])

    def test_rejects_repo_for_unregistered_telegram_id(self) -> None:
        result = self.registry.set_repo(999, "https://github.com/example/course")

        self.assertEqual("not_registered", result.status)

    def test_rejects_invalid_repo_without_changing_csv(self) -> None:
        self.registry.register("18225001", 100)

        result = self.registry.set_repo(100, "https://evil.example/example/course")

        self.assertEqual("invalid_repo", result.status)
        self.assertEqual("", self.read_rows()[0]["repo"])

    def test_rejects_repo_with_wrong_readme_heading(self) -> None:
        self.registry.register("18225001", 100)
        self.repo_validator.validate.return_value = RepoValidationResult(
            "invalid_readme",
            f"Baris pertama README.md harus tepat: {REQUIRED_README_FIRST_LINE}",
        )

        result = self.registry.set_repo(100, "https://github.com/example/course")

        self.assertEqual("invalid_readme", result.status)
        self.assertEqual("", self.read_rows()[0]["repo"])

    def test_status_reports_valid_repo(self) -> None:
        self.registry.register("18225001", 100)
        self.registry.set_repo(100, "https://github.com/example/course")

        result = self.registry.status(100)

        self.assertEqual("registered_with_valid_repo", result.status)
        self.assertIn("Repo: valid", result.message)

    def test_status_reports_missing_repo(self) -> None:
        result = self.registry.status(200)

        self.assertEqual("registered_without_repo", result.status)

    def test_status_reports_unregistered_id(self) -> None:
        result = self.registry.status(999)

        self.assertEqual("not_registered", result.status)

    def test_github_url_validation_rejects_non_repo_pages(self) -> None:
        invalid_urls = [
            "http://github.com/example/course",
            "https://github.com/example",
            "https://github.com/example/course/issues",
            "https://github.com@example.com/example/course",
            "https://github.com/example/course?tab=readme",
        ]

        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertIsNone(normalize_github_repo_url(url))

    def test_score_below_three_requires_revision(self) -> None:
        self.registry.register("18225001", 100)

        result = self.registry.score(100, "A01")

        self.assertEqual("revision_required", result.status)
        self.assertIn("Nilai A01: 2.5", result.message)
        self.assertIn("Status: revisi", result.message)

    def test_score_three_is_achieved(self) -> None:
        self.registry.register("18225001", 100)

        result = self.registry.score(100, "a02")

        self.assertEqual("achieved", result.status)
        self.assertIn("Status: tercapai", result.message)

    def test_empty_score_asks_student_to_complete_work(self) -> None:
        self.registry.register("18225001", 100)

        result = self.registry.score(100, "A03")

        self.assertEqual("score_empty", result.status)
        self.assertIn("Kerjakan A03 terlebih dahulu", result.message)

    def test_invalid_score_value_is_reported(self) -> None:
        self.registry.register("18225001", 100)

        result = self.registry.score(100, "A04")

        self.assertEqual("score_invalid", result.status)

    def test_decimal_comma_score_is_supported(self) -> None:
        self.registry.register("18225001", 100)

        result = self.registry.score(100, "A05")

        self.assertEqual("revision_required", result.status)

    def test_score_rejects_code_outside_a01_to_a15(self) -> None:
        for code in ("A00", "A16", "A1", "B01"):
            with self.subTest(code=code):
                result = self.registry.score(200, code)
                self.assertEqual("invalid_assessment_code", result.status)

    def test_score_requires_registered_telegram_id(self) -> None:
        result = self.registry.score(999, "A01")

        self.assertEqual("not_registered", result.status)

    def test_submit_adds_valid_page_to_queue(self) -> None:
        self.registry.register("18225001", 100)
        self.registry.set_repo(100, "https://github.com/example/course")

        result = self.registry.submit(100, "W01")

        self.assertEqual("queued", result.status)
        rows = self.read_queue_rows()
        self.assertEqual(1, len(rows))
        self.assertEqual("1", rows[0]["tiket"])
        self.assertEqual("18225001", rows[0]["nim"])
        self.assertEqual("W01", rows[0]["week"])
        self.assertEqual(
            "https://example.github.io/course/portfolio/week-01.html",
            rows[0]["url"],
        )
        self.assertEqual("", rows[0]["skor"])
        self.assertEqual("ANTRI", rows[0]["status"])
        self.assertIn("Tiket: 1", result.message)
        self.assertIn("Status: ANTRI", result.message)

    def test_submit_uses_next_ticket_number(self) -> None:
        self.registry.register("18225001", 100)
        self.registry.set_repo(100, "https://github.com/example/course")
        self.registry.submit(100, "W01")

        result = self.registry.submit(100, "w02")

        self.assertEqual("queued", result.status)
        self.assertEqual("2", self.read_queue_rows()[1]["tiket"])

    def test_duplicate_active_submission_reuses_existing_ticket(self) -> None:
        self.registry.register("18225001", 100)
        self.registry.set_repo(100, "https://github.com/example/course")
        first = self.registry.submit(100, "W01")

        second = self.registry.submit(100, "W01")

        self.assertEqual("queued", first.status)
        self.assertEqual("already_queued", second.status)
        self.assertIn("Tiket: 1", second.message)
        self.assertEqual(1, len(self.read_queue_rows()))

    def test_student_can_view_queue_and_feedback(self) -> None:
        self.registry.register("18225001", 100)
        self.registry.set_repo(100, "https://github.com/example/course")
        self.registry.submit(100, "W02")
        rows = self.registry._read_queue_rows()
        rows[0].update(
            {
                "skor": "12",
                "status": "MENUNGGU PERSETUJUAN",
                "ringkasan": "Refleksi sudah jelas.",
                "saran": "Tambahkan bukti tindakan.",
            }
        )
        self.registry._write_queue_rows(rows)
        self.report_dir.mkdir()
        (self.report_dir / "tiket-1-W02.md").write_text(
            "# Hasil assessment tiket 1\n\n"
            "- NIM: 18225001\n- Minggu: W02\n\n"
            "## Skor rubrik\n\nPerson & Character: 2\n"
            "\n## Data terstruktur\n\n```json\n{}\n```\n",
            encoding="utf-8",
        )

        queue_result = self.registry.queue_status(100)
        assessment_result = self.registry.result(100, "W02")
        ticket_result = self.registry.llm_result(100, "1")

        self.assertEqual("queue_status", queue_result.status)
        self.assertIn("MENUNGGU PERSETUJUAN", queue_result.message)
        self.assertEqual("result", assessment_result.status)
        self.assertIn("masih sementara", assessment_result.message)
        self.assertIn("Refleksi sudah jelas", assessment_result.message)
        self.assertIn("Tambahkan bukti tindakan", assessment_result.message)
        self.assertEqual("llm_result", ticket_result.status)
        self.assertIn("Hasil LLM tiket 1", ticket_result.message)
        self.assertIn("Refleksi sudah jelas", ticket_result.message)
        self.assertIn("Detail assessment", ticket_result.message)
        self.assertIn("Person & Character: 2", ticket_result.message)
        self.assertNotIn("Data terstruktur", ticket_result.message)

    def test_llm_result_does_not_expose_another_students_ticket(self) -> None:
        self.registry.register("18225001", 100)
        self.registry.set_repo(100, "https://github.com/example/course")
        self.registry.submit(100, "W01")

        result = self.registry.llm_result(200, "1")

        self.assertEqual("ticket_not_found", result.status)
        self.assertNotIn("18225001", result.message)
        self.assertNotIn("W01", result.message)

    def test_llm_result_rejects_invalid_ticket_number(self) -> None:
        result = self.registry.llm_result(200, "not-a-ticket")

        self.assertEqual("invalid_ticket", result.status)

    def test_submit_rejects_invalid_week(self) -> None:
        for code in ("W00", "W16", "W1", "A01"):
            with self.subTest(code=code):
                result = self.registry.submit(200, code)
                self.assertEqual("invalid_week", result.status)

    def test_submit_requires_registered_telegram_id(self) -> None:
        result = self.registry.submit(999, "W01")

        self.assertEqual("not_registered", result.status)

    def test_submit_requires_repo(self) -> None:
        result = self.registry.submit(200, "W01")

        self.assertEqual("repo_missing_or_invalid", result.status)

    def test_submit_does_not_queue_unavailable_page(self) -> None:
        self.registry.register("18225001", 100)
        self.registry.set_repo(100, "https://github.com/example/course")
        self.page_validator.validate.return_value = PageValidationResult(
            "not_found",
            "Halaman portfolio belum ditemukan.",
        )

        result = self.registry.submit(100, "W01")

        self.assertEqual("not_found", result.status)
        self.assertEqual([], self.read_queue_rows())

    def test_build_portfolio_url_supports_user_site_repo(self) -> None:
        self.assertEqual(
            "https://example.github.io/portfolio/week-15.html",
            build_portfolio_url(
                "https://github.com/example/example.github.io",
                "W15",
            ),
        )


class GitHubRepositoryValidatorTest(unittest.TestCase):
    @staticmethod
    def response_with(content: str) -> Mock:
        response = Mock()
        response.read.return_value = content.encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        return response

    def test_accepts_required_readme_first_line(self) -> None:
        validator = GitHubRepositoryValidator()
        response = self.response_with(
            f"{REQUIRED_README_FIRST_LINE}\n\nIsi portfolio.\n"
        )

        with patch("course_service.urllib.request.urlopen", return_value=response):
            result = validator.validate("https://github.com/example/course")

        self.assertTrue(result.is_valid)

    def test_rejects_heading_on_second_line(self) -> None:
        validator = GitHubRepositoryValidator()
        response = self.response_with(
            f"Judul lain\n{REQUIRED_README_FIRST_LINE}\n"
        )

        with patch("course_service.urllib.request.urlopen", return_value=response):
            result = validator.validate("https://github.com/example/course")

        self.assertEqual("invalid_readme", result.status)

    def test_reports_missing_repo_or_readme(self) -> None:
        validator = GitHubRepositoryValidator()
        error = urllib.error.HTTPError(
            "https://api.github.com/repos/example/course/readme",
            404,
            "Not Found",
            {},
            BytesIO(b"Not Found"),
        )

        try:
            with patch("course_service.urllib.request.urlopen", side_effect=error):
                result = validator.validate("https://github.com/example/course")
        finally:
            error.close()

        self.assertEqual("not_found", result.status)

    def test_sends_optional_github_token(self) -> None:
        validator = GitHubRepositoryValidator("github-secret")
        response = self.response_with(REQUIRED_README_FIRST_LINE)

        with patch(
            "course_service.urllib.request.urlopen",
            return_value=response,
        ) as urlopen:
            validator.validate("https://github.com/example/course")

        request = urlopen.call_args.args[0]
        self.assertEqual("Bearer github-secret", request.get_header("Authorization"))


if __name__ == "__main__":
    unittest.main()
