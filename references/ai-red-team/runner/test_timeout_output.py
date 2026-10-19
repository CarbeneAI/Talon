"""Check that timeout output survives the runner's command and log paths."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import redteam


class TimeoutOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="talon-timeout-output-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_with_timeout(self, stdout=None, stderr=None):
        exception = subprocess.TimeoutExpired(
            ["synthetic-tool", "--fixture"], 3600, output=stdout, stderr=stderr
        )
        with patch("subprocess.run", side_effect=exception) as run:
            result = redteam.run_cmd(["synthetic-tool", "--fixture"], self.root)
        run.assert_called_once_with(
            ["synthetic-tool", "--fixture"],
            cwd=str(self.root),
            capture_output=True,
            text=True,
            timeout=3600,
            check=False,
        )
        return result

    def test_timeout_preserves_byte_streams_and_marker(self):
        result = self.run_with_timeout(b"partial stdout\n", b"partial stderr\n")
        self.assertEqual(result, (124, "partial stdout\npartial stderr\ntimeout: synthetic-tool"))

    def test_timeout_preserves_text_streams_and_marker(self):
        result = self.run_with_timeout("partial stdout", "partial stderr")
        self.assertEqual(result, (124, "partial stdoutpartial stderr\ntimeout: synthetic-tool"))

    def test_timeout_handles_missing_or_invalid_byte_streams(self):
        self.assertEqual(self.run_with_timeout(), (124, "timeout: synthetic-tool"))
        self.assertEqual(
            self.run_with_timeout(b"partial\xff\n", None),
            (124, "partial\ufffd\ntimeout: synthetic-tool"),
        )

    def test_main_writes_partial_timeout_output_through_existing_scrub(self):
        config = {
            "name": "synthetic-target",
            "type": "openai",
            "model": "synthetic-model",
            "endpoint": "",
            "key_env": "SYNTHETIC_KEY",
            "phases": ["2_prompt_injection"],
            "promptfoo_config": None,
        }
        output_base = self.root / "engagements"
        exception = subprocess.TimeoutExpired(
            ["garak"],
            3600,
            output=b"partial garak output sk-abcdefghijklmnopqrst\n",
            stderr=b"partial stderr\n",
        )
        argv = ["redteam.py", "--config", "synthetic.yaml", "--out", str(output_base)]
        with patch.object(sys, "argv", argv), \
                patch.object(redteam, "load_config", return_value={}), \
                patch.object(redteam, "validate", return_value=config), \
                patch("subprocess.run", side_effect=exception), \
                contextlib.redirect_stdout(io.StringIO()):
            try:
                main_status = redteam.main()
            except SystemExit as exc:
                main_status = exc.code

        # The upstream baseline has no execution status; the report PR returns nonzero.
        if main_status is not None:
            self.assertEqual(main_status, 1)

        logs = list(output_base.glob("*/2_prompt_injection.log"))
        self.assertEqual(len(logs), 1)
        log = logs[0].read_text(encoding="utf-8")
        self.assertIn("partial garak output", log)
        self.assertIn("partial stderr", log)
        self.assertIn("timeout: garak", log)
        self.assertIn("[REDACTED]", log)
        self.assertNotIn("sk-abcdefghijklmnopqrst", log)


if __name__ == "__main__":
    unittest.main()
