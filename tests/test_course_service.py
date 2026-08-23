import csv
import tempfile
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

from course_service import (
    REQUIRED_README_FIRST_LINE,
    GitHubRepositoryValidator,
    ParticipantRegistry,
    RepoValidationResult,
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
        self.repo_validator = Mock()
        self.repo_validator.validate.return_value = RepoValidationResult(
            "valid",
            "Repo dan README.md valid.",
        )
        self.registry = ParticipantRegistry(
            self.csv_path,
            repo_validator=self.repo_validator,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def read_rows(self) -> list[dict[str, str]]:
        with self.csv_path.open(encoding="utf-8", newline="") as csv_file:
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
