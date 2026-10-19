"""Validate the supported configuration without invoking an external tool."""
import contextlib
import io
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import redteam


class ConfigTests(unittest.TestCase):
    def setUp(self):
        example = Path(__file__).with_name("config.example.yaml")
        self.cfg = redteam.load_config(example)
        self.cfg["authorized"] = True
        self.environment = {
            "OPENAI_API_KEY": "synthetic-provider-key",
            "SYNTHETIC_API_KEY": "synthetic-custom-key",
        }

    def test_authorized_example_accepts_provider_defaults(self):
        with patch.dict(os.environ, self.environment, clear=True):
            normalized = redteam.validate(self.cfg)
        self.assertEqual(normalized["type"], "openai")
        self.assertEqual(normalized["endpoint"], "")
        self.assertEqual(normalized["key_env"], "OPENAI_API_KEY")

    def test_supported_config_dry_run_does_not_execute_or_create_output(self):
        with TemporaryDirectory() as temp:
            config = Path(temp) / "synthetic.yaml"
            config.write_text(redteam.yaml.safe_dump(self.cfg))
            output = Path(temp) / "output"
            argv = ["redteam.py", "--config", str(config), "--out", str(output), "--dry-run"]
            with patch.object(sys, "argv", argv), \
                    patch.dict(os.environ, self.environment, clear=True), \
                    patch.object(redteam, "run_cmd") as run_cmd, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(redteam.main(), 0)
            run_cmd.assert_not_called()
            self.assertFalse(output.exists())

    def test_nonempty_endpoint_is_rejected_before_execution_or_output(self):
        for endpoint in ("https://synthetic.example/v1", "http://127.0.0.1:1234/v1"):
            with self.subTest(endpoint=endpoint):
                self.cfg["target"]["endpoint"] = endpoint
                self.assert_rejected_before_execution("target.endpoint", "leave it empty")

    def test_custom_key_variable_is_rejected_even_when_set(self):
        self.cfg["target"]["api_key_env"] = "SYNTHETIC_API_KEY"
        self.assert_rejected_before_execution("target.api_key_env", "OPENAI_API_KEY")

    def assert_rejected_before_execution(self, field, action):
        for dry_run in (False, True):
            with self.subTest(dry_run=dry_run), TemporaryDirectory() as temp:
                config = Path(temp) / "synthetic.yaml"
                config.write_text(redteam.yaml.safe_dump(self.cfg))
                output = Path(temp) / "output"
                argv = ["redteam.py", "--config", str(config), "--out", str(output)]
                if dry_run:
                    argv.append("--dry-run")
                with patch.object(sys, "argv", argv), \
                        patch.dict(os.environ, self.environment, clear=True), \
                        patch.object(redteam, "run_cmd", side_effect=AssertionError("unexpected tool execution")) as run_cmd, \
                        contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        redteam.main()
                message = str(raised.exception.code)
                self.assertIn(field, message)
                self.assertIn(action, message)
                self.assertNotIn("synthetic-provider-key", message)
                self.assertNotIn("synthetic-custom-key", message)
                run_cmd.assert_not_called()
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
