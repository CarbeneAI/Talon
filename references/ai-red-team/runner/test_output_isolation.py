"""Disposable output directories, fixed clocks, and mocked tool commands only."""
import contextlib
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import stat
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import redteam
from report_test_support import rendered_text


class OutputIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / "output"
        self.cfg = {
            "authorized": True,
            "target": {"name": "synthetic-target", "type": "openai", "model": "synthetic-model",
                       "api_key_env": "OPENAI_API_KEY"},
            "phases": ["2_prompt_injection"],
        }

    def run_main(self, label="synthetic", dry_run=False):
        argv = ["redteam.py", "--config", "synthetic.yaml", "--out", str(self.base)]
        if dry_run:
            argv.append("--dry-run")
        raw = (json.dumps({"probe": "synthetic", "prompt": label + " row"}) + "\n").encode()
        def command(_cmd, cwd):
            (cwd / (label + ".hitlog.jsonl")).write_bytes(raw)
            return 0, "synthetic tool output"
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", argv), \
                patch.object(redteam, "load_config", return_value=self.cfg), \
                patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-value"}), \
                patch.object(redteam, "run_cmd", side_effect=command) as run_cmd, \
                patch.object(redteam, "datetime") as clock, \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            clock.now.return_value = datetime(2026, 10, 19, 12, 30, tzinfo=timezone.utc)
            status = redteam.main()
        return status, raw, run_cmd

    def test_same_clock_runs_are_separate_and_stale_timestamp_directory_is_untouched(self):
        stale = self.base / "synthetic-target-20261019T123000Z"
        stale.mkdir(parents=True)
        original = {
            "stale.hitlog.jsonl": b'{"prompt":"stale evidence"}\n',
            "findings-report.md": b"stale report\n",
            "2_prompt_injection.log": b"stale log\n",
        }
        for name, raw in original.items():
            (stale / name).write_bytes(raw)
        expected = {}
        for label in ("first", "second"):
            status, raw, run_cmd = self.run_main(label)
            self.assertEqual(status, 0)
            run_cmd.assert_called_once()
            expected[label + ".hitlog.jsonl"] = raw
        created = [path for path in self.base.iterdir() if path != stale]
        self.assertEqual(len(created), 2)
        self.assertNotEqual(created[0], created[1])
        observed = set()
        for directory in created:
            self.assertTrue(directory.name.startswith("synthetic-target-20261019T123000Z-"))
            raw_files = list(directory.glob("*.hitlog.jsonl"))
            self.assertEqual(len(raw_files), 1)
            evidence = raw_files[0]
            observed.add(evidence.name)
            self.assertEqual(evidence.read_bytes(), expected[evidence.name])
            report = rendered_text((directory / "findings-report.md").read_text())
            self.assertIn("Parsed 1 untriaged hit(s)", report)
            self.assertIn(evidence.name.removesuffix(".hitlog.jsonl") + " row", report)
            self.assertNotIn("stale evidence", report)
        self.assertEqual(observed, set(expected))
        self.assertEqual({path.name: path.read_bytes() for path in stale.iterdir()}, original)

    @unittest.skipUnless(os.name == "posix", "POSIX directory permission bits")
    def test_permissive_umask_still_creates_private_child_and_preserves_existing_base_mode(self):
        self.base.mkdir()
        self.base.chmod(0o775)
        previous = os.umask(0)
        try:
            status, _, _ = self.run_main()
        finally:
            os.umask(previous)
        self.assertEqual(status, 0)
        self.assertEqual(stat.S_IMODE(self.base.stat().st_mode), 0o775)
        children = list(self.base.iterdir())
        self.assertEqual(len(children), 1)
        self.assertEqual(stat.S_IMODE(children[0].stat().st_mode), 0o700)

    def test_dry_run_and_invalid_config_do_not_create_output_or_invoke_tools(self):
        status, _, run_cmd = self.run_main(dry_run=True)
        self.assertEqual(status, 0)
        self.assertFalse(self.base.exists())
        run_cmd.assert_not_called()
        self.cfg["target"]["endpoint"] = "https://unsupported.invalid"
        with self.assertRaises(SystemExit):
            self.run_main()
        self.assertFalse(self.base.exists())
