"""Check the repository's actual ignore rules in a disposable Git repository."""
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest


class EngagementIgnoreTests(unittest.TestCase):
    def test_default_output_and_local_configs_are_ignored(self):
        self.check_paths(True, [
            "engagements/synthetic-target/garak.hitlog.jsonl",
            "engagements/synthetic-target/findings-report.md",
            "references/ai-red-team/runner/engagements/synthetic-target/2_prompt_injection.log",
            "arbitrary/nested/cwd/engagements/synthetic-target/garak.hitlog.jsonl",
            "references/ai-red-team/runner/config.yaml",
            ".mcp.json",
        ])

    def test_examples_and_fixtures_remain_trackable(self):
        self.check_paths(False, [
            "references/ai-red-team/runner/config.example.yaml",
            "mcp-config.example.json",
            "tests/fixtures/garak.hitlog.jsonl",
            "fixtures/config.yaml",
            "fixtures/.mcp.json",
        ])

    def check_paths(self, ignored, paths):
        with TemporaryDirectory() as temp:
            repo = Path(temp)
            source = Path(__file__).resolve().parents[3] / ".gitignore"
            shutil.copy2(source, repo / ".gitignore")
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            for name in paths:
                with self.subTest(path=name):
                    path = repo / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("synthetic fixture\n")
                    result = subprocess.run(
                        ["git", "-c", "core.excludesFile=/dev/null", "check-ignore", "--no-index", "-q", name],
                        cwd=repo, capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0 if ignored else 1, result.stderr or name)


if __name__ == "__main__":
    unittest.main()
