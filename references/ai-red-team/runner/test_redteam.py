"""Offline regression tests for findings-report redaction."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from redteam import parse_garak_hits, write_report
from report_test_support import rendered_text


class FindingsReportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.out_dir = Path(self.temp_dir.name)
        self.cfg = {"name": "example-target", "model": "example-model"}

    def test_report_redacts_tokens_from_hitlog_without_changing_raw_evidence(self):
        tokens = (
            "sk-synthetic_key_0123456789",
            "Bearer synthetic-bearer-token",
            "xoxb-synthetic-slack-token",
            "ghp_syntheticgithubtoken0123456789",
        )
        for token in tokens:
            with self.subTest(token=token):
                raw = json.dumps({"probe": "example", "prompt": f"Observed {token}"}) + "\n"
                hitlog = self.out_dir / "example.hitlog.jsonl"
                hitlog.write_text(raw, encoding="utf-8")

                parsed = parse_garak_hits(self.out_dir)
                hits, raw_files = parsed.hits, parsed.raw_files
                report = write_report(self.out_dir, self.cfg, ["example"], {}, hits, raw_files)
                content = rendered_text(report.read_text(encoding="utf-8"))

                self.assertNotIn(token, content)
                self.assertIn("Observed [REDACTED]", content)
                self.assertEqual(hitlog.read_text(encoding="utf-8"), raw)

    def test_report_redacts_metadata_and_phase_notes(self):
        target_token = "sk-synthetic_target_0123456789"
        note_token = "Bearer synthetic-note-token"
        cfg = {**self.cfg, "name": target_token}
        report = write_report(
            self.out_dir, cfg, [], {"example": f"Tool returned {note_token}"}, [], []
        )
        content = rendered_text(report.read_text(encoding="utf-8"))

        self.assertNotIn(target_token, content)
        self.assertNotIn(note_token, content)
        self.assertIn("Target: [REDACTED] (example-model)", content)
        self.assertIn("Tool returned [REDACTED]", content)

    def test_report_redacts_before_truncating_hitlog_evidence(self):
        prefix = "x" * 266
        raw = json.dumps({"output": prefix + "sk-synthetic_key_0123456789"}) + "\n"
        hitlog = self.out_dir / "example.hitlog.jsonl"
        hitlog.write_text(raw, encoding="utf-8")

        parsed = parse_garak_hits(self.out_dir)
        hits, raw_files = parsed.hits, parsed.raw_files
        report = write_report(self.out_dir, self.cfg, [], {}, hits, raw_files)
        content = rendered_text(report.read_text(encoding="utf-8"))

        self.assertIn(prefix + "[REDACTED]", content)
        self.assertNotIn("sk-synthetic", content)
        self.assertEqual(hitlog.read_text(encoding="utf-8"), raw)

    def test_report_preserves_non_secret_evidence_and_formatting(self):
        hits = [{"probe": "example-probe", "detector": "example-detector", "prompt": "A | B\nC"}]
        report = write_report(
            self.out_dir,
            self.cfg,
            ["example-phase"],
            {"manual-phase": "Review the evidence"},
            hits,
            ["example.hitlog.jsonl"],
        )
        content = rendered_text(report.read_text(encoding="utf-8"))

        self.assertIn("Target: example-target (example-model)", content)
        self.assertIn("Phases run: example-phase", content)
        self.assertIn("A | B C", content)
        self.assertIn("Raw hitlog: example.hitlog.jsonl", content)
        self.assertIn("manual-phase: Review the evidence", content)


if __name__ == "__main__":
    unittest.main()
