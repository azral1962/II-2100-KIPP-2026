import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import uts
from course_service import ParticipantRegistry, REQUIRED_ASSESSMENT_COLUMNS, QUEUE_FIELDNAMES
from llm import (AssessmentWorker, AssessmentResult, PermanentAssessmentError,
                 RemoteRequestError, fetch_portfolio_page, html_to_text, read_queue,
                 update_assessment_file, load_assessment_prompts, parse_args)


def session_result(score=3):
    return {"evidence_status": "Lengkap", "summary": "Tujuan dan respons ditunjukkan pada U001.",
            "improvement_priority": "Periksa transfer tindakan nyata.",
            "dimensions": {key: {"score": score, "evidence": "U001: bukti dialog aktual.",
                                 "reason": "Sesuai descriptor fixture tes."} for key in uts.DIMENSIONS}}


class UTSCalculationTest(unittest.TestCase):
    def test_weighted_total_and_extremes(self):
        values = {key: uts.session_score(session_result()["dimensions"]) for key in uts.SESSIONS}
        self.assertEqual(Decimal("75.50"), uts.final_score(Decimal(80), values))
        self.assertEqual(Decimal("67.50"), uts.final_score(Decimal(0), values))
        for score, expected in ((1, 25), (4, 100)):
            values = {key: uts.session_score(session_result(score)["dimensions"]) for key in uts.SESSIONS}
            self.assertEqual(Decimal(expected), uts.final_score(Decimal(expected), values))

    def test_bt_blocks_aggregation_and_is_not_zero(self):
        data = session_result()
        data["dimensions"]["objective_context"]["score"] = None
        self.assertIsNone(uts.session_score(data["dimensions"]))
        values = {key: Decimal(75) for key in uts.SESSIONS}
        self.assertIsNone(uts.final_score(None, values))
        values["3b"] = None
        self.assertIsNone(uts.final_score(Decimal(80), values))

    def test_rejects_invalid_scores_shape_and_evidence(self):
        for score in (0, 5, True, 3.0, "3"):
            with self.subTest(score=score), self.assertRaises(ValueError):
                uts.validate_session(session_result(score))
        for value in (Decimal("NaN"), Decimal("Infinity"), Decimal(-1), Decimal(101)):
            with self.assertRaises(ValueError):
                uts.final_score(value, {key: Decimal(75) for key in uts.SESSIONS})
        bad = session_result()
        bad["dimensions"].pop("objective_context")
        with self.assertRaises(ValueError):
            uts.validate_session(bad)
        bad = session_result()
        bad["dimensions"]["objective_context"]["evidence"] = ""
        with self.assertRaises(ValueError):
            uts.validate_session(bad)
        for status in ("Parsial", "Tidak memadai"):
            bad = session_result()
            bad["evidence_status"] = status
            with self.assertRaises(ValueError):
                uts.validate_session(bad)

    def test_extracts_current_links_and_rejects_ambiguous_reports(self):
        base = "https://student.github.io/course/portfolio/week-08.html"
        html = '''<a href="UTS/hasil_2a_001.html">Sesi</a>
        <a href="UTS/hasil_3b_Old.html">Old</a><a href="../examples/UTS/hasil_1.html">Contoh</a>
        <a href="https://evil.github.io/course/portfolio/UTS/paper.html">Luar</a>
        <a href="UTS/hasil_2b_002.html">NIM lain</a>
        <a href="UTS/paper.html#ref">Makalah</a>'''
        urls = uts.artifact_urls(base, html_to_text(html, base), "001")
        self.assertEqual({"2a", "paper"}, set(urls))
        self.assertNotIn("#", urls["paper"])
        html += '<a href="UTS/hasil_2a.html">Duplikat alternatif</a>'
        with self.assertRaises(ValueError):
            uts.artifact_urls(base, html_to_text(html, base), "001")

    def test_cli_and_prompt_use_uts_rules(self):
        args = parse_args(["--approve", "7", "--paper-score", "80", "--assessor", "Dosen"])
        self.assertEqual("80", args.paper_score)
        _, prompt = load_assessment_prompts(Path(__file__).resolve().parents[1] / "llm-assessment-prompts.md", "W08")
        self.assertIn("ENAM DIMENSI", prompt)
        self.assertIn("18%", prompt)


class UTSWorkerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.queue = self.root / "queue.csv"
        self.participants = self.root / "participants.csv"
        self.assessment = self.root / "assessment.csv"
        self.url = "https://student.github.io/course/portfolio/week-08.html"
        self.write_csv(self.participants, ["NIM", "Nama", "ID", "repo"],
                       [{"NIM": "001", "Nama": "Mahasiswa Dummy", "ID": "100", "repo": "https://github.com/student/course"}])
        self.write_csv(self.queue, QUEUE_FIELDNAMES,
                       [{"tiket": "7", "nim": "001", "week": "W08", "url": self.url, "status": "ANTRI"}])
        self.write_csv(self.assessment, REQUIRED_ASSESSMENT_COLUMNS,
                       [{"NIM": "001", "name": "Mahasiswa Dummy", "A01": "3", "A08": "4", "A09": "2", "TOTAL": "9"}])
        self.original = self.assessment.read_bytes()
        html = "<h1>Portfolio UTS</h1>" + ''.join(
            f'<a href="UTS/{filename}.html">{key}</a>'
            for key, filename in [("paper", "paper"), *((s, f"hasil_{s}_001") for s in uts.SESSIONS)])
        self.pages = {self.url: html_to_text(html, self.url)}
        for key, url in uts.artifact_urls(self.url, self.pages[self.url], "001").items():
            self.pages[url] = "Makalah MBTI PASK" if key == "paper" else "U001: bukti dialog aktual. AI001: respons. Refleksi dan uji ulang."
        self.client = Mock()
        self.client.complete.return_value = json.dumps(session_result())
        self.loader = Mock(side_effect=lambda url: self.pages[url])
        self.references = self.root / "references"
        self.references.mkdir()
        # Synthetic test fixture, deliberately not a published rubric.
        reference = {"nim": "001", "package_version": "TEST", "assignments": {s: f"Penugasan fixture sesi {s}" for s in uts.SESSIONS},
                     "descriptors": {k: {str(n): f"Fixture level {n}" for n in range(1, 5)} for k in uts.DIMENSIONS}}
        (self.references / "001.json").write_text(json.dumps(reference), encoding="utf-8")
        self.worker = AssessmentWorker(queue_path=self.queue, assessment_path=self.assessment,
            participant_path=self.participants,
            prompt_path=Path(__file__).resolve().parents[1] / "llm-assessment-prompts.md",
            input_dir=self.root / "inputs", report_dir=self.root / "reports", client=self.client,
            page_loader=self.loader, uts_reference_dir=self.references,
            uts_assessment_path=self.root / "uts.csv", auto_approve=True)

    @staticmethod
    def write_csv(path, fields, rows):
        with path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_complete_package_waits_for_explicit_approval_and_preserves_weekly(self):
        self.assertEqual((1, 0), self.worker.process_ticket_number("7"))
        self.assertEqual(5, self.client.complete.call_count)
        self.assertEqual(7, self.loader.call_count)
        self.assertEqual("MENUNGGU PERSETUJUAN", read_queue(self.queue)[1][0]["status"])
        self.assertEqual(self.original, self.assessment.read_bytes())
        self.assertFalse(self.worker.uts_assessment_path.exists())
        with self.assertRaises(PermanentAssessmentError):
            self.worker.approve_ticket("7")
        update = self.worker.approve_ticket("7", paper_score="80", assessor="Dosen Dummy")
        self.assertEqual("75.50", update.total)
        self.assertEqual(self.original, self.assessment.read_bytes())
        with self.worker.uts_assessment_path.open(encoding="utf-8", newline="") as source:
            receipts = list(csv.DictReader(source))
        self.assertEqual("001", receipts[0]["NIM"])
        self.assertEqual("UTS DISETUJUI", read_queue(self.queue)[1][0]["status"])
        self.worker.approve_ticket("7", paper_score="80", assessor="Dosen Dummy")
        with self.worker.uts_assessment_path.open(encoding="utf-8", newline="") as source:
            self.assertEqual(1, len(list(csv.DictReader(source))))
        with self.assertRaises(PermanentAssessmentError):
            self.worker.approve_ticket("7", paper_score="81", assessor="Dosen Dummy")

    def test_missing_reference_is_bt_without_model_call(self):
        (self.references / "001.json").unlink()
        self.assertEqual((1, 0), self.worker.process_ticket_number("7"))
        self.client.complete.assert_not_called()
        with self.assertRaises(PermanentAssessmentError):
            self.worker.approve_ticket("7", paper_score="80", assessor="Dosen")

    def test_missing_template_or_oversize_session_cannot_be_approved(self):
        url = uts.artifact_urls(self.url, self.pages[self.url], "001")["3b"]
        self.pages[url] = "Template belum terisi. Belum ada transkrip."
        self.assertEqual((1, 0), self.worker.process_ticket_number("7"))
        self.assertEqual(4, self.client.complete.call_count)
        with self.assertRaises(PermanentAssessmentError):
            self.worker.approve_ticket("7", paper_score="80", assessor="Dosen")
        self.worker.retry_uts("7")
        self.pages[url] = "X" * (self.worker.max_evidence_chars + 1)
        self.assertEqual((1, 0), self.worker.process_ticket_number("7"))
        self.assertEqual(8, self.client.complete.call_count)

    def test_model_invalid_response_fails_without_official_write(self):
        self.client.complete.return_value = json.dumps(session_result(True))
        self.assertEqual((0, 1), self.worker.process_ticket_number("7"))
        self.assertEqual("GAGAL", read_queue(self.queue)[1][0]["status"])
        self.assertFalse(self.worker.uts_assessment_path.exists())

    def test_cache_uses_fresh_evidence_and_ignores_old_week08_report(self):
        self.worker.report_dir.mkdir()
        (self.worker.report_dir / "tiket-7-W08.md").write_text("Old five-dimension result", encoding="utf-8")
        self.worker.process_ticket_number("7")
        self.worker.retry_uts("7")
        self.worker.process_ticket_number("7")
        self.assertEqual(5, self.client.complete.call_count)
        self.worker.retry_uts("7")
        self.pages[uts.artifact_urls(self.url, self.pages[self.url], "001")["1"]] += " Koreksi evidence."
        self.worker.process_ticket_number("7")
        self.assertEqual(10, self.client.complete.call_count)

    def test_rejects_wrong_repository_and_weekly_approval_of_uts(self):
        fields, rows = read_queue(self.queue)
        rows[0]["url"] = self.url.replace("student", "other")
        self.write_csv(self.queue, fields, rows)
        self.assertEqual((0, 1), self.worker.process_ticket_number("7"))
        self.loader.assert_not_called()
        with self.assertRaises(PermanentAssessmentError):
            update_assessment_file(self.assessment, self.participants, "001", "W08", AssessmentResult(20, "TERCAPAI", "old"))

    def test_network_error_requeues_without_grade(self):
        self.loader.side_effect = RemoteRequestError("Offline")
        self.assertEqual((0, 1), self.worker.process_ticket_number("7"))
        self.assertEqual("ANTRI", read_queue(self.queue)[1][0]["status"])

    def test_missing_html_artifact_is_reported_and_not_retried_forever(self):
        missing = uts.artifact_urls(self.url, self.pages[self.url], "001")["3b"]
        def loader(url):
            if url == missing:
                raise PermanentAssessmentError("404")
            return self.pages[url]
        self.loader.side_effect = loader
        self.assertEqual((1, 0), self.worker.process_ticket_number("7"))
        with self.assertRaises(PermanentAssessmentError):
            self.worker.approve_ticket("7", paper_score="80", assessor="Dosen")

    def test_score_and_result_use_correct_units_and_ownership(self):
        registry = ParticipantRegistry(self.participants, assessment_csv_path=self.assessment,
            queue_csv_path=self.queue, llm_report_dir=self.worker.report_dir,
            uts_assessment_csv_path=self.worker.uts_assessment_path)
        self.assertEqual("uts_score_empty", registry.score(100, "A08").status)
        self.assertEqual("not_registered", registry.score(999, "A08").status)
        self.worker.process_ticket_number("7")
        self.assertIn("Nilai UTS /100", registry.result(100, "W08").message)
        self.worker.approve_ticket("7", paper_score="80", assessor="Dosen")
        message = registry.score(100, "A08").message
        self.assertIn("75.50 /100", message)
        self.assertNotIn("tercapai", message.lower())
        self.assertIn("Sesi 1", registry.llm_result(100, "7").message)

    def test_migration_backs_up_preserves_a08_and_excludes_it_from_total(self):
        backup = uts.migrate_weekly_totals(self.assessment)
        self.assertEqual(self.original, backup.read_bytes())
        with self.assessment.open(encoding="utf-8", newline="") as source:
            row = next(csv.DictReader(source))
        self.assertEqual("4", row["A08"])
        self.assertEqual("5", row["TOTAL"])
        uts.migrate_weekly_totals(self.assessment)
        self.assertEqual(self.original, backup.read_bytes())

    def test_reference_rejects_mismatched_nim_and_missing_descriptors(self):
        path = self.references / "001.json"
        reference = json.loads(path.read_text())
        reference["nim"] = "002"
        path.write_text(json.dumps(reference))
        with self.assertRaises(ValueError):
            uts.load_reference(self.references, "001")
        reference["nim"] = "001"
        reference["descriptors"] = {}
        path.write_text(json.dumps(reference))
        with self.assertRaises(ValueError):
            uts.load_reference(self.references, "001")

    def test_cli_approval_and_retry_without_network(self):
        self.worker.process_ticket_number("7")
        project = Path(__file__).resolve().parents[1]
        env = {**os.environ, "ANTRIAN_CSV": str(self.queue), "PESERTA_CSV": str(self.participants),
               "ASSESSMENT_CSV": str(self.assessment), "LLM_REPORT_DIR": str(self.worker.report_dir),
               "UTS_ASSESSMENT_CSV": str(self.worker.uts_assessment_path),
               "UTS_REFERENCE_DIR": str(self.references), "LLM_SERVER_URL": "http://127.0.0.1:1"}
        result = subprocess.run([sys.executable, str(project / "llm.py"), "--approve", "7",
                                "--paper-score", "80", "--assessor", "Dosen"],
                               env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("75.50", result.stdout)
        result = subprocess.run([sys.executable, str(project / "llm.py"), "--retry-uts", "7"],
                               env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(1, result.returncode)

    def test_legacy_week08_is_never_shown_as_official_uts(self):
        row = {"tiket": "7", "week": "W08", "status": "TERCAPAI", "skor": "20", "ringkasan": "Tercapai", "saran": ""}
        message = ParticipantRegistry._format_llm_result(row)
        self.assertIn("HASIL W08 LAMA", message)
        self.assertNotIn("Nilai UTS /100: 20", message)
        row["status"] = "MENUNGGU PERSETUJUAN"
        self.assertNotIn("Nilai UTS /100: 20", ParticipantRegistry._format_llm_result(row))


class UTSDownloadTest(unittest.TestCase):
    def test_redirect_rejected_before_fetching_external_target(self):
        captured = []
        def make_opener(handler):
            captured.append(handler)
            raise RuntimeError("Stop before network")
        with patch("urllib.request.build_opener", side_effect=make_opener):
            with self.assertRaises(RuntimeError):
                fetch_portfolio_page("https://student.github.io/course/portfolio/UTS/hasil_1.html", restrict_redirects=True)
        request = urllib.request.Request("https://student.github.io/course/portfolio/UTS/hasil_1.html")
        for target in ("https://evil.example/x", "https://student.github.io/other/hasil_1.html",
                       "https://student.github.io/course/portfolio/UTS/../secret.html"):
            with self.assertRaises(PermanentAssessmentError):
                captured[0].redirect_request(request, None, 302, "redirect", {}, target)

    def test_404_is_missing_but_503_is_retryable(self):
        url = "https://student.github.io/course/portfolio/UTS/hasil_1.html"
        for code, error in ((404, PermanentAssessmentError), (503, RemoteRequestError)):
            opener = Mock()
            http_error = urllib.error.HTTPError(url, code, "error", {}, None)
            self.addCleanup(http_error.close)
            opener.open.side_effect = http_error
            with patch("urllib.request.build_opener", return_value=opener), self.assertRaises(error):
                fetch_portfolio_page(url, restrict_redirects=True)


if __name__ == "__main__":
    unittest.main()
