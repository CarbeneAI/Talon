"""Offline tests for the runner's pinned Garak CLI contract."""

from pathlib import Path
import unittest

from redteam import PHASE_GARAK_PROBES, build_garak_cmd


EXPECTED_PHASE_SPECS = {
    "2_prompt_injection": "probes.promptinject,probes.latentinjection",
    "3_jailbreak": "probes.dan,probes.grandma",
    "4_disclosure": (
        "probes.leakreplay,probes.web_injection.MarkdownXSS,"
        "probes.web_injection.TaskXSS"
    ),
}


class GarakCliContractTests(unittest.TestCase):
    def test_each_automated_phase_selects_supported_plugin_names(self):
        for phase, expected_spec in EXPECTED_PHASE_SPECS.items():
            with self.subTest(phase=phase):
                self.assertIn(phase, PHASE_GARAK_PROBES)
                command = build_garak_cmd(
                    {"model": "synthetic-offline-model"},
                    PHASE_GARAK_PROBES[phase],
                    Path("offline-report"),
                )
                self.assertEqual(command[command.index("--spec") + 1], expected_spec)

    def test_command_uses_current_cli_flags_and_keeps_openai_routing(self):
        command = build_garak_cmd(
            {
                "model": "synthetic-offline-model",
                "endpoint": "https://example.invalid",
            },
            PHASE_GARAK_PROBES["2_prompt_injection"],
            Path("offline-report"),
        )

        self.assertEqual(
            command,
            [
                "garak",
                "--target_type",
                "openai",
                "--target_name",
                "synthetic-offline-model",
                "--spec",
                "probes.promptinject,probes.latentinjection",
                "--report_prefix",
                "offline-report",
            ],
        )
        self.assertNotIn("--model_type", command)
        self.assertNotIn("--model_name", command)
        self.assertNotIn("--probes", command)
        self.assertNotIn("--endpoint", command)


if __name__ == "__main__":
    unittest.main()
