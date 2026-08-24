import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from llm import (
    ASSESSMENT_RESPONSE_FORMAT,
    AssessmentResult,
    AssessmentWorker,
    DEFAULT_TEST_PROMPT,
    LlamaCppClient,
    PermanentAssessmentError,
    REVIEW_STATUS,
    RemoteRequestError,
    fetch_portfolio_page,
    html_to_text,
    load_assessment_prompts,
    parse_assessment,
    parse_args,
    official_score_from_result,
    read_queue,
    run_simple_prompt_test,
    update_assessment_file,
    validate_result_week,
)
from course_service import ASSESSMENT_CODES


def structured_assessment(
    scores: tuple[int | None, ...] = (2, 2, 3, 2, 3),
    *,
    evidence_status: str = "Lengkap",
    decision: str = "Perlu revisi",
) -> dict:
    keys = (
        "person_character",
        "objective_state",
        "repertoire_language_ai",
        "response_adaptation",
        "agreement_action_relationship",
    )
    total = None if any(score is None for score in scores) else sum(scores)  # type: ignore[arg-type]
    level = (
        None
        if total is None
        else "Awal"
        if total <= 8
        else "Berkembang"
        if total <= 12
        else "Kompeten"
        if total <= 16
        else "Lanjut"
    )
    return {
        "week_task": "W02 - Journal",
        "evidence_status": evidence_status,
        "decision": decision,
        "total": total,
        "level": level,
        "summary": "Evidence menunjukkan refleksi, tetapi tindakan belum terukur.",
        "dimensions": {
            key: {
                "score": score,
                "evidence": f"Evidence spesifik untuk {key}.",
                "reason": f"Alasan rubrik untuk {key}.",
            }
            for key, score in zip(keys, scores)
        },
        "strengths": ["Alternatif narasi dibedakan dengan jelas."],
        "improvement_priority": "Tambahkan bukti tindakan dan indikator hasil.",
        "additional_suggestions": [],
        "questions": ["Apa bukti tindakan setelah kesepakatan internal?"],
        "integrity_notes": "Tautan eksternal tidak diverifikasi.",
    }


class PromptAndResponseTest(unittest.TestCase):
    def test_maps_llm_result_to_official_score(self) -> None:
        cases = (
            (5, "PERLU REVISI", 1),
            (9, "PERLU REVISI", 2),
            (13, "TERCAPAI", 3),
            (17, "TERCAPAI", 4),
            (17, "PERLU REVISI", 2),
            (None, "BELUM DAPAT DINILAI", None),
        )
        for total, status, expected in cases:
            with self.subTest(total=total, status=status):
                result = AssessmentResult(total=total, status=status, content="hasil")
                self.assertEqual(expected, official_score_from_result(result))

    def test_llama_client_disables_thinking_by_default(self) -> None:
        client = LlamaCppClient("http://llama.test", model="test-model")
        client._request_json = Mock(  # type: ignore[method-assign]
            return_value={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "hasil"},
                    }
                ]
            }
        )

        result = client.complete([{"role": "user", "content": "nilai ini"}])

        self.assertEqual("hasil", result)
        payload = client._request_json.call_args.kwargs["payload"]
        self.assertEqual(
            {"enable_thinking": False},
            payload["chat_template_kwargs"],
        )

    def test_llama_client_sends_llamacpp_schema_format(self) -> None:
        client = LlamaCppClient("http://llama.test", model="test-model")
        client._request_json = Mock(  # type: ignore[method-assign]
            return_value={
                "choices": [
                    {"finish_reason": "stop", "message": {"content": "{}"}}
                ]
            }
        )

        client.complete(
            [{"role": "user", "content": "nilai"}],
            response_format=ASSESSMENT_RESPONSE_FORMAT,
        )

        payload = client._request_json.call_args.kwargs["payload"]
        self.assertEqual("json_object", payload["response_format"]["type"])
        self.assertIn("schema", payload["response_format"])

    def test_empty_content_reports_reasoning_exhaustion(self) -> None:
        client = LlamaCppClient(
            "http://llama.test",
            model="test-model",
            enable_thinking=True,
        )
        client._request_json = Mock(  # type: ignore[method-assign]
            return_value={
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {
                            "content": "",
                            "reasoning_content": "berpikir panjang",
                        },
                    }
                ]
            }
        )

        with self.assertRaisesRegex(RemoteRequestError, "reasoning.*finish_reason=length"):
            client.complete([{"role": "user", "content": "nilai ini"}])

    def test_test_option_uses_default_or_custom_prompt(self) -> None:
        self.assertEqual(DEFAULT_TEST_PROMPT, parse_args(["--test"]).test)
        self.assertEqual("Jawab singkat", parse_args(["--test", "Jawab singkat"]).test)
        self.assertIsNone(parse_args([]).test)
        self.assertEqual("7", parse_args(["--approve", "7"]).approve)

    def test_simple_prompt_test_does_not_require_queue(self) -> None:
        client = Mock()
        client.complete.return_value = "LLAMA_CPP_OK"

        response = run_simple_prompt_test(client, "  Balas OK  ")

        self.assertEqual("LLAMA_CPP_OK", response)
        messages = client.complete.call_args.args[0]
        self.assertEqual("Balas OK", messages[1]["content"])

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

    def test_validates_five_dimension_structured_result(self) -> None:
        data = structured_assessment()

        result = parse_assessment(json.dumps(data), require_structured=True)

        self.assertEqual(12, result.total)
        self.assertEqual("PERLU REVISI", result.status)
        self.assertEqual(data, result.data)

    def test_rejects_inconsistent_structured_total(self) -> None:
        data = structured_assessment()
        data["total"] = 13

        with self.assertRaisesRegex(PermanentAssessmentError, "jumlah dimensi"):
            parse_assessment(json.dumps(data), require_structured=True)

    def test_rejects_structured_result_for_wrong_week(self) -> None:
        result = parse_assessment(
            json.dumps(structured_assessment()), require_structured=True
        )

        with self.assertRaisesRegex(PermanentAssessmentError, "W03"):
            validate_result_week(result, "W03")

    def test_requires_structured_output_for_new_llm_response(self) -> None:
        with self.assertRaisesRegex(PermanentAssessmentError, "JSON terstruktur"):
            parse_assessment(
                "- Keputusan rekomendasi: Tercapai\n"
                "- Total dan tingkat: 15/20 - Kompeten\n",
                require_structured=True,
            )

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

    def test_portfolio_fetch_rejects_non_github_pages_url(self) -> None:
        with self.assertRaisesRegex(PermanentAssessmentError, "tidak diizinkan"):
            fetch_portfolio_page("http://127.0.0.1/private")


class AssessmentWorkerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.queue_path = self.root / "antrian.csv"
        self.assessment_path = self.root / "assessment.csv"
        self.participant_path = self.root / "peserta.csv"
        self.input_dir = self.root / "inputs"
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
        self._write_participants()
        self._write_assessments()
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

    def _write_participants(self) -> None:
        with self.participant_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=("NIM", "Nama", "ID", "repo"),
            )
            writer.writeheader()
            writer.writerows(
                [
                    {
                        "NIM": "18225001",
                        "Nama": "Kezia Josephine Manik",
                        "ID": "100",
                        "repo": "https://github.com/example/course",
                    },
                    {
                        "NIM": "07381119",
                        "Nama": "Ali Baba",
                        "ID": "200",
                        "repo": "https://github.com/example/other",
                    },
                ]
            )

    def _write_assessments(self) -> None:
        fieldnames = ("NIM", "name", *ASSESSMENT_CODES, "TOTAL")
        with self.assessment_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            row = {fieldname: "" for fieldname in fieldnames}
            row.update(
                {
                    "NIM": "18225001",
                    "name": "Kezia Josephine Manik",
                    "A01": "3",
                    "TOTAL": "3",
                }
            )
            writer.writerow(row)

    def _read_assessments(self) -> list[dict[str, str]]:
        with self.assessment_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            return list(csv.DictReader(csv_file))

    def _worker(self, client: Mock) -> AssessmentWorker:
        return AssessmentWorker(
            queue_path=self.queue_path,
            assessment_path=self.assessment_path,
            participant_path=self.participant_path,
            prompt_path=self.prompt_path,
            input_dir=self.input_dir,
            report_dir=self.report_dir,
            client=client,
            page_loader=Mock(return_value="Journal evidence mahasiswa."),
        )

    def test_processes_queue_and_writes_full_report(self) -> None:
        client = Mock()
        client.complete.return_value = json.dumps(structured_assessment())
        worker = self._worker(client)

        completed, failed = worker.process_pending()

        self.assertEqual((1, 0), (completed, failed))
        _, rows = read_queue(self.queue_path)
        self.assertEqual("12", rows[0]["skor"])
        self.assertEqual(REVIEW_STATUS, rows[0]["status"])
        self.assertIn("refleksi", rows[0]["ringkasan"])
        self.assertIn("bukti tindakan", rows[0]["saran"])
        assessment = self._read_assessments()[0]
        self.assertEqual("", assessment["A02"])
        self.assertEqual("3", assessment["TOTAL"])
        report = (self.report_dir / "tiket-7-W02.md").read_text(encoding="utf-8")
        self.assertIn("NIM: 18225001", report)
        self.assertIn("Person & Character", report)

        update = worker.approve_ticket("7")
        self.assertEqual(2, update.score)
        _, rows = read_queue(self.queue_path)
        self.assertEqual("PERLU REVISI", rows[0]["status"])
        assessment = self._read_assessments()[0]
        self.assertEqual("2", assessment["A02"])
        self.assertEqual("5", assessment["TOTAL"])

        prompt_file = self.input_dir / "tiket-7-W02-prompts.txt"
        portfolio_file = self.input_dir / "tiket-7-W02-portfolio.txt"
        self.assertTrue(prompt_file.exists())
        self.assertTrue(portfolio_file.exists())
        self.assertIn("PROMPT SISTEM PENILAI", prompt_file.read_text(encoding="utf-8"))
        self.assertIn("Nilai evidence Minggu 02", prompt_file.read_text(encoding="utf-8"))
        self.assertIn(
            "Journal evidence mahasiswa",
            portfolio_file.read_text(encoding="utf-8"),
        )

        messages = client.complete.call_args.args[0]
        response_format = client.complete.call_args.kwargs["response_format"]
        self.assertEqual(ASSESSMENT_RESPONSE_FORMAT, response_format)
        self.assertEqual("system", messages[0]["role"])
        self.assertIn(prompt_file.name, messages[0]["content"])
        self.assertIn(portfolio_file.name, messages[1]["content"])
        self.assertIn("Nilai evidence Minggu 02", messages[0]["content"])
        self.assertIn("Journal evidence mahasiswa", messages[1]["content"])

    def test_adds_missing_assessment_row_from_participant_file(self) -> None:
        result = AssessmentResult(total=17, status="TERCAPAI", content="hasil")

        update = update_assessment_file(
            self.assessment_path,
            self.participant_path,
            "07381119",
            "W01",
            result,
        )

        self.assertEqual(4, update.score)
        rows = self._read_assessments()
        added = next(row for row in rows if row["NIM"] == "07381119")
        self.assertEqual("Ali Baba", added["name"])
        self.assertEqual("4", added["A01"])
        self.assertEqual("4", added["TOTAL"])

    def test_unassessable_result_does_not_erase_existing_score(self) -> None:
        before = self.assessment_path.read_bytes()
        result = AssessmentResult(
            total=None,
            status="BELUM DAPAT DINILAI",
            content="hasil",
        )

        update = update_assessment_file(
            self.assessment_path,
            self.participant_path,
            "18225001",
            "W01",
            result,
        )

        self.assertIsNone(update.score)
        self.assertEqual(before, self.assessment_path.read_bytes())

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

    def test_only_one_worker_can_claim_a_ticket(self) -> None:
        first = self._worker(Mock())
        second = self._worker(Mock())
        first.worker_id = "worker-one"
        second.worker_id = "worker-two"

        claimed = first._claim_ticket("7")

        self.assertIsNotNone(claimed)
        self.assertIsNone(second._claim_ticket("7"))
        _, rows = read_queue(self.queue_path)
        self.assertEqual("worker-one", rows[0]["worker_id"])
        self.assertEqual("PROSES", rows[0]["status"])

    def test_process_ticket_number_only_processes_requested_ticket(self) -> None:
        with self.queue_path.open("a", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=("tiket", "nim", "week", "url", "skor", "status"),
            )
            writer.writerow(
                {
                    "tiket": "8",
                    "nim": "07381119",
                    "week": "W02",
                    "url": "https://example.github.io/other/week-02.html",
                    "skor": "",
                    "status": "ANTRI",
                }
            )
        client = Mock()
        client.complete.return_value = json.dumps(structured_assessment())
        worker = self._worker(client)

        completed, failed = worker.process_ticket_number("7")

        self.assertEqual((1, 0), (completed, failed))
        _, rows = read_queue(self.queue_path)
        rows_by_ticket = {row["tiket"]: row for row in rows}
        self.assertEqual(REVIEW_STATUS, rows_by_ticket["7"]["status"])
        self.assertEqual("ANTRI", rows_by_ticket["8"]["status"])


if __name__ == "__main__":
    unittest.main()
