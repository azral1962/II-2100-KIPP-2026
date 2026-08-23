import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from llm import (
    AssessmentWorker,
    RemoteRequestError,
    html_to_text,
    load_assessment_prompts,
    parse_assessment,
    read_queue,
)


class PromptAndResponseTest(unittest.TestCase):
    def test_loads_system_and_selected_week_prompt(self) -> None:
        system_prompt, week_prompt = load_assessment_prompts(
            Path(__file__).parents[1] / "llm-assessment-prompts.md",
            "W02",
        )

        self.assertIn("Anda adalah assessor portfolio", system_prompt)
        self.assertIn("Nilai evidence Minggu 02", week_prompt)
        self.assertNotIn("Nilai evidence Minggu 03", week_prompt)

    def test_parses_bold_markdown_summary(self) -> None:
        result = parse_assessment(
            "- **Keputusan rekomendasi:** **Tercapai**\n"
            "- **Total dan tingkat:** **14/20 - Kompeten**\n"
        )

        self.assertEqual(14, result.total)
        self.assertEqual("TERCAPAI", result.status)

    def test_allows_no_total_when_evidence_cannot_be_assessed(self) -> None:
        result = parse_assessment(
            "- Keputusan rekomendasi: Belum dapat dinilai\n"
            "- Total dan tingkat: Belum dapat dihitung\n"
        )

        self.assertIsNone(result.total)
        self.assertEqual("BELUM DAPAT DINILAI", result.status)

    def test_html_extraction_omits_scripts_and_keeps_links(self) -> None:
        content = html_to_text(
            "<h1>Evidence</h1><script>ignore me</script>"
            "<p>Tindakan nyata</p><a href='/proof.pdf'>Bukti</a>",
            "https://example.github.io/portfolio/week-02.html",
        )

        self.assertIn("Evidence", content)
        self.assertIn("Tindakan nyata", content)
        self.assertNotIn("ignore me", content)
        self.assertIn("https://example.github.io/proof.pdf", content)


class AssessmentWorkerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.queue_path = self.root / "antrian.csv"
        self.report_dir = self.root / "reports"
        self.prompt_path = self.root / "prompts.md"
        self.prompt_path.write_text(
            """# Prompts

## Prompt sistem penilai

```text
Gunakan evidence saja.
```

## Prompt Minggu 02 - Journal

```text
Nilai evidence Minggu 02.
```
""",
            encoding="utf-8",
        )
        self._write_queue()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_queue(self) -> None:
        with self.queue_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=("tiket", "nim", "week", "url", "skor", "status"),
            )
            writer.writeheader()
            writer.writerow(
                {
                    "tiket": "7",
                    "nim": "18225001",
                    "week": "W02",
                    "url": "https://example.github.io/portfolio/week-02.html",
                    "skor": "",
                    "status": "ANTRI",
                }
            )

    def _worker(self, client: Mock) -> AssessmentWorker:
        return AssessmentWorker(
            queue_path=self.queue_path,
            prompt_path=self.prompt_path,
            report_dir=self.report_dir,
            client=client,
            page_loader=Mock(return_value="Journal evidence mahasiswa."),
        )

    def test_processes_queue_and_writes_full_report(self) -> None:
        client = Mock()
        client.complete.return_value = (
            "### Ringkasan keputusan\n"
            "- Keputusan rekomendasi: Perlu revisi\n"
            "- Total dan tingkat: 12/20 - Berkembang\n"
        )
        worker = self._worker(client)

        completed, failed = worker.process_pending()

        self.assertEqual((1, 0), (completed, failed))
        _, rows = read_queue(self.queue_path)
        self.assertEqual("12", rows[0]["skor"])
        self.assertEqual("PERLU REVISI", rows[0]["status"])
        report = (self.report_dir / "tiket-7-W02.md").read_text(encoding="utf-8")
        self.assertIn("NIM: 18225001", report)
        self.assertIn("Total dan tingkat: 12/20", report)

        messages = client.complete.call_args.args[0]
        self.assertEqual("system", messages[0]["role"])
        self.assertIn("Nilai evidence Minggu 02", messages[1]["content"])
        self.assertIn("Journal evidence mahasiswa", messages[1]["content"])

    def test_transient_server_failure_leaves_ticket_pending(self) -> None:
        client = Mock()
        client.complete.side_effect = RemoteRequestError("server offline")
        worker = self._worker(client)

        completed, failed = worker.process_pending()

        self.assertEqual((0, 1), (completed, failed))
        _, rows = read_queue(self.queue_path)
        self.assertEqual("ANTRI", rows[0]["status"])
        self.assertEqual("", rows[0]["skor"])

    def test_unparseable_response_marks_ticket_failed(self) -> None:
        client = Mock()
        client.complete.return_value = "Respons tanpa ringkasan wajib."
        worker = self._worker(client)

        completed, failed = worker.process_pending()

        self.assertEqual((0, 1), (completed, failed))
        _, rows = read_queue(self.queue_path)
        self.assertEqual("GAGAL", rows[0]["status"])
        self.assertTrue((self.report_dir / "tiket-7-W02-unparsed.md").exists())
        self.assertTrue((self.report_dir / "tiket-7-W02-error.md").exists())


if __name__ == "__main__":
    unittest.main()
