"""Exercise production main with synthetic config and mocked tool commands."""
import contextlib
import io
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import redteam
from report_test_support import rendered_text


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.invocation = 0
        self.cfg = {
            "name": "synthetic-target", "type": "openai", "model": "synthetic-model",
            "phases": ["2_prompt_injection", "1_recon"], "promptfoo_config": None,
        }

    def run_main(self, result=(0, "synthetic output"), dry_run=False):
        self.invocation += 1
        output_base = self.root / f"output-{self.invocation}"
        argv = ["redteam.py", "--config", "synthetic.yaml", "--out", str(output_base)]
        if dry_run:
            argv.append("--dry-run")
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", argv), \
                patch.object(redteam, "load_config", return_value={}), \
                patch.object(redteam, "validate", return_value=self.cfg), \
                patch.object(redteam, "run_cmd", return_value=result) as run_cmd, \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = redteam.main()
        reports = list(output_base.glob("*/findings-report.md"))
        self.assertEqual(len(reports), 0 if dry_run else 1)
        report = rendered_text(reports[0].read_text()) if reports else ""
        return status, report, run_cmd, stdout.getvalue() + stderr.getvalue()

    def test_success_preserves_report_and_manual_guidance(self):
        status, report, run_cmd, _ = self.run_main()
        self.assertEqual(status, 0)
        run_cmd.assert_called_once()
        self.assertIn("Phases run: 2_prompt_injection", report)
        self.assertIn("Execution failures: 0", report)
        self.assertIn("1_recon", report)

    def test_garak_failures_preserve_report_and_return_nonzero(self):
        for code in (1, 124, 127):
            with self.subTest(code=code):
                status, report, _, output = self.run_main((code, "Bearer synthetic-token"))
                self.assertEqual(status, 1)
                self.assertIn("Execution failures: 1", report)
                self.assertIn(f"garak exited {code}", report)
                self.assertIn("Execution failures: 1", output)
                logs = list((self.root / f"output-{self.invocation}").glob("*/2_prompt_injection.log"))
                self.assertTrue(logs)
                self.assertEqual(logs[0].read_text(), "[REDACTED]")

    def test_manual_only_run_is_an_intentional_skip(self):
        self.cfg["phases"] = ["1_recon", "5_tool_abuse"]
        status, report, run_cmd, _ = self.run_main()
        self.assertEqual(status, 0)
        run_cmd.assert_not_called()
        self.assertIn("Phases run: none", report)
        self.assertIn("Execution failures: 0", report)
        self.assertIn("5_tool_abuse", report)

    def test_missing_promptfoo_config_fails_after_writing_report(self):
        self.cfg["phases"] = ["1_recon"]
        self.cfg["promptfoo_config"] = str(self.root / "missing.yaml")
        status, report, run_cmd, _ = self.run_main()
        self.assertEqual(status, 1)
        run_cmd.assert_not_called()
        self.assertIn("Execution failures: 1", report)
        self.assertIn("config not found:", report)

    def test_promptfoo_success_and_failure(self):
        config = self.root / "promptfoo.yaml"
        config.write_text("# synthetic fixture\n")
        self.cfg["phases"] = ["1_recon"]
        self.cfg["promptfoo_config"] = str(config)
        for code in (0, 2, 127):
            with self.subTest(code=code):
                status, report, run_cmd, _ = self.run_main((code, "synthetic output"))
                self.assertEqual(status, int(code != 0))
                self.assertEqual(run_cmd.call_args.args[0][:3], ["promptfoo", "redteam", "run"])
                if code:
                    self.assertIn(f"promptfoo exited {code}", report)
                else:
                    self.assertIn("Phases run: promptfoo", report)

    def test_dry_run_does_not_execute_or_write_report(self):
        status, report, run_cmd, _ = self.run_main(dry_run=True)
        self.assertEqual(status, 0)
        self.assertEqual(report, "")
        run_cmd.assert_not_called()


if __name__ == "__main__":
    unittest.main()
