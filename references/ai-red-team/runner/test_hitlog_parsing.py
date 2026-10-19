"""Offline evidence integrity fixtures; tools and network are never invoked."""
import contextlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import redteam
from report_test_support import RenderedReport, rendered_text


class HitlogParsingTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.cfg = {"name": "synthetic-target", "model": "synthetic-model"}

    def parse(self, raw, name="synthetic.hitlog.jsonl"):
        path = self.out / name
        path.write_bytes(raw)
        result = redteam.parse_garak_hits(self.out)
        self.assertEqual(path.read_bytes(), raw)
        return result

    def test_mixed_corrupt_rows_keep_valid_evidence_and_exact_physical_issues(self):
        raw = (b'{"probe":"first","prompt":"kept first"}\n'
               b'{"prompt":\xff}\n'
               b'{broken secret-payload}\n'
               b'42\n[]\nnull\n'
               b'{"probe":"last","output":"kept last"}\n')
        result = self.parse(raw)
        self.assertEqual([hit["probe"] for hit in result.hits], ["first", "last"])
        self.assertEqual(result.raw_files, ["synthetic.hitlog.jsonl"])
        self.assertEqual([(issue.filename, issue.line_number, issue.reason) for issue in result.issues], [
            ("synthetic.hitlog.jsonl", 2, "invalid_utf8"),
            ("synthetic.hitlog.jsonl", 3, "invalid_json"),
            ("synthetic.hitlog.jsonl", 4, "non_object"),
            ("synthetic.hitlog.jsonl", 5, "non_object"),
            ("synthetic.hitlog.jsonl", 6, "non_object"),
        ])
        self.assertNotIn("secret-payload", repr(result.issues))

    def test_binary_crlf_blank_lines_and_unicode_separator_keep_record_boundaries(self):
        row = json.dumps({"prompt": "before\u2028after"}, ensure_ascii=False).encode()
        result = self.parse(b' \r\n\r\n' + row + b'\r\n\t\nnot JSON\n')
        self.assertEqual([hit["prompt"] for hit in result.hits], ["before\u2028after"])
        self.assertEqual([(issue.line_number, issue.reason) for issue in result.issues], [(5, "invalid_json")])

    def test_official_structured_fields_and_legacy_alternates_retain_extraction(self):
        message = {"text": "synthetic output", "lang": None, "data_path": None,
                   "data_type": None, "data_checksum": None, "notes": {}}
        conversation = {"turns": [{"role": "user", "content": {**message, "text": "synthetic input"}}], "notes": {}}
        records = [
            {"probe": "official", "detector": "detector", "prompt": conversation, "output": message},
            {"probe_classname": "legacy", "detector_name": "legacy detector", "output": message},
            {"prompt": "x" * 266 + "sk-synthetic_key_0123456789"},
        ]
        result = self.parse(b''.join((json.dumps(row) + '\n').encode() for row in records))
        self.assertEqual(result.issues, [])
        self.assertEqual(result.hits[:2], [
            {"probe": "official", "detector": "detector", "prompt": str(conversation)},
            {"probe": "legacy", "detector": "legacy detector", "prompt": str(message)},
        ])
        self.assertEqual(result.hits[2]["prompt"], "x" * 266 + "[REDACTED]")

    def test_nonstandard_json_constants_are_invalid_without_losing_later_rows(self):
        deep = b'{"ignored":' + b'[' * 10000 + b'0' + b']' * 10000 + b'}\n'
        result = self.parse(b'{"prompt":NaN}\n{"ignored":Infinity}\n{"prompt":-Infinity}\n' + deep + b'{"prompt":"kept"}\n')
        self.assertEqual([hit["prompt"] for hit in result.hits], ["kept"])
        self.assertEqual([(issue.line_number, issue.reason) for issue in result.issues],
                         [(1, "invalid_json"), (2, "invalid_json"), (3, "invalid_json"), (4, "invalid_json")])

    def test_file_read_errors_keep_prior_rows_and_later_files_without_exception_text(self):
        first = self.out / "a.hitlog.jsonl"
        first.write_bytes(b'{"prompt":"first"}\n')
        second = self.out / "b.hitlog.jsonl"
        second.write_bytes(b'{"prompt":"second"}\n')
        original_open = Path.open

        class FailingRead(io.BytesIO):
            def __next__(self):
                if self.tell():
                    raise OSError("Bearer PRIVATE_EXCEPTION_PAYLOAD")
                return super().__next__()

        for partial in (False, True):
            with self.subTest(partial=partial):
                raw_first = first.read_bytes()
                def open_fixture(path, *args, **kwargs):
                    if path == first:
                        if partial:
                            return FailingRead(raw_first)
                        raise OSError("Bearer PRIVATE_EXCEPTION_PAYLOAD")
                    return original_open(path, *args, **kwargs)
                with patch.object(Path, "open", new=open_fixture):
                    result = redteam.parse_garak_hits(self.out)
                expected = ["first", "second"] if partial else ["second"]
                self.assertEqual([hit["prompt"] for hit in result.hits], expected)
                self.assertEqual(result.raw_files, [first.name, second.name])
                self.assertEqual([(issue.filename, issue.line_number, issue.reason) for issue in result.issues],
                                 [(first.name, None, "read_error")])
                report = redteam.write_report(self.out, self.cfg, [], {}, result.hits, result.raw_files, issues=result.issues)
                self.assertNotIn("PRIVATE_EXCEPTION_PAYLOAD", report.read_text())
                self.assertEqual(first.read_bytes(), raw_first)

    def test_issue_filenames_stay_redacted_and_literal_in_real_markdown(self):
        token = "sk-synthetic_key_0123456789"
        filename = token + ' <img src=x onerror=alert(1)> [raw](https:attacker.invalid).hitlog.jsonl'
        raw = b'{broken Bearer CORRUPT_PAYLOAD}\n'
        result = self.parse(raw, filename)
        report = redteam.write_report(self.out, self.cfg, [], {}, result.hits, result.raw_files, issues=result.issues)
        rendered = RenderedReport(report.read_text())
        self.assertFalse(set(rendered.tags) & {"a", "img", "script", "svg", "iframe"})
        self.assertFalse(any(key.startswith("on") for key, _ in rendered.attributes))
        self.assertIn('[REDACTED] <img src=x onerror=alert(1)> [raw](https:attacker.invalid)', rendered.content)
        self.assertIn("line 1", rendered.content)
        self.assertNotIn(token, report.read_text())
        self.assertNotIn("CORRUPT_PAYLOAD", report.read_text())

    def run_main(self, raw, command_status=0):
        output = self.out / "engagements"
        cfg = {**self.cfg, "type": "openai", "phases": ["2_prompt_injection"], "promptfoo_config": None}
        def command(_cmd, cwd):
            if raw is not None:
                (cwd / "synthetic.hitlog.jsonl").write_bytes(raw)
            return command_status, "synthetic tool output"
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["redteam.py", "--config", "synthetic.yaml", "--out", str(output)]), \
                patch.object(redteam, "load_config", return_value={}), \
                patch.object(redteam, "validate", return_value=cfg), \
                patch.object(redteam, "run_cmd", side_effect=command), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = redteam.main()
        reports = list(output.glob("*/findings-report.md"))
        self.assertEqual(len(reports), 1)
        evidence = reports[0].parent / "synthetic.hitlog.jsonl"
        if raw is not None:
            self.assertEqual(evidence.read_bytes(), raw)
        return status, rendered_text(reports[0].read_text()), stdout.getvalue() + stderr.getvalue()

    def test_successful_tool_with_corrupt_evidence_writes_report_and_fails_separately(self):
        status, report, diagnostics = self.run_main(b'{"prompt":"kept"}\n{broken Bearer CORRUPT_PAYLOAD}\n')
        self.assertEqual(status, 1)
        self.assertIn("Parsed 1 untriaged hit(s)", report)
        self.assertIn("Execution failures: 0", report)
        self.assertIn("Evidence parsing issues: 1", report)
        self.assertIn("Evidence parsing issues: 1", diagnostics)
        self.assertNotIn("CORRUPT_PAYLOAD", report + diagnostics)

    def test_lone_surrogates_render_as_literal_escapes_and_main_persists_report(self):
        raw = (json.dumps({"probe": "probe-\ud800", "detector": "detector-\udfff",
                           "prompt": "prompt-\ud800-\udfff <img src=x onerror=alert(1)>"}) + "\n").encode("ascii")
        parsed = self.parse(raw)
        self.assertEqual(len(parsed.hits), 1)
        self.assertEqual(parsed.issues, [])
        issues = [redteam.HitlogIssue("file-\ud800-\udfff.hitlog.jsonl", None, "read_error")]
        report = redteam.write_report(self.out, self.cfg, [], {}, parsed.hits, parsed.raw_files, issues=issues)
        rendered = RenderedReport(report.read_text(encoding="utf-8"))
        self.assertIn(r"probe-\ud800", rendered.content)
        self.assertIn(r"detector-\udfff", rendered.content)
        self.assertIn(r"prompt-\ud800-\udfff <img src=x onerror=alert(1)>", rendered.content)
        self.assertIn(r"file-\ud800-\udfff.hitlog.jsonl", rendered.content)
        self.assertNotIn("img", rendered.tags)
        self.assertFalse(any(key.startswith("on") for key, _ in rendered.attributes))
        status, main_report, _ = self.run_main(raw)
        self.assertEqual(status, 0)
        self.assertIn(r"prompt-\ud800-\udfff", main_report)
        self.assertIn("Parsed 1 untriaged hit(s)", main_report)

    def test_execution_and_parsing_failure_counts_remain_distinct(self):
        status, report, diagnostics = self.run_main(b'{broken}\n', command_status=2)
        self.assertEqual(status, 1)
        for text in (report, diagnostics):
            self.assertIn("Execution failures: 1", text)
            self.assertIn("Evidence parsing issues: 1", text)
        self.assertIn("garak exited 2", report)

    def test_clean_missing_empty_and_whitespace_evidence_remain_inconclusive_without_parse_failure(self):
        # A fresh invocation directory for each case prevents old hitlogs leaking in.
        for raw in (None, b'', b' \r\n\t\r\n', b'{"prompt":"kept"}\n'):
            with self.subTest(raw=raw), TemporaryDirectory() as root:
                previous = self.out
                self.out = Path(root)
                try:
                    status, report, diagnostics = self.run_main(raw)
                finally:
                    self.out = previous
                self.assertEqual(status, 0)
                self.assertIn("Evidence parsing issues: 0", report)
                self.assertIn("Evidence parsing issues: 0", diagnostics)
                if raw in (None, b'', b' \r\n\t\r\n'):
                    self.assertIn("inconclusive", report.lower())
