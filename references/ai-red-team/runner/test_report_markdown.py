"""Untrusted report fields must stay literal under real GFM rendering."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from redteam import parse_garak_hits, write_report
from report_test_support import RenderedReport


class LiteralReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)

    def render_fields(self, value):
        report = write_report(
            self.out, {"name": value, "model": value}, [value], {value: value},
            [{"probe": value, "detector": value, "prompt": value}], [value], {value: value},
        )
        return report.read_text(), RenderedReport(report.read_text())

    def assert_inert(self, rendered):
        self.assertFalse(set(rendered.tags) & {"script", "img", "a", "iframe", "svg", "math", "style", "input"})
        self.assertFalse(any(name.lower().startswith("on") for name, _ in rendered.attributes))
        self.assertEqual(rendered.tags.count("h1"), 1)
        self.assertEqual(rendered.tags.count("h2"), 5)
        self.assertEqual(rendered.tags.count("table"), 1)
        self.assertEqual(rendered.tags.count("tr"), 2)
        self.assertEqual(rendered.tags.count("td"), 3)

    def test_every_field_renders_html_and_markdown_as_readable_literal_text(self):
        payloads = [
            '<img src="https://attacker.invalid/pixel" onerror="alert(1)"><script>alert(1)</script>',
            '[attacker](https://attacker.invalid/) ![tracking](https://attacker.invalid/pixel)',
            '<https://attacker.invalid/> https://attacker.invalid/ www.attacker.invalid user@attacker.invalid',
            '&lt;img src=x onerror=alert(1)&gt; &#60;script&#62; &quot;quoted&quot;',
            '`code` ``backticks`` **bold** _emphasis_ ~~strike~~',
            '# injected\n\n## heading\r\n| injected | cells |\n|---|---|\n> blockquote',
            r'backslash \\ and \| pipe and \`tick` [reference][id]',
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                _, rendered = self.render_fields(payload)
                self.assert_inert(rendered)
                literal = " ".join(payload.splitlines())
                # name, model, ran phase, three hit cells, filename, and both
                # failure/manual phase names and notes must all remain readable.
                self.assertEqual(rendered.content.count(literal), 11)

    def test_filenames_remain_literal_when_no_hits_were_parsed(self):
        payload = '<img src=x onerror=alert(1)> [raw](https://attacker.invalid/)'
        report = write_report(self.out, {"name": "target", "model": "model"}, [], {}, [], [payload])
        rendered = RenderedReport(report.read_text())
        self.assertNotIn("img", rendered.tags)
        self.assertNotIn("a", rendered.tags)
        self.assertIn(payload, rendered.content)

    def test_supported_redaction_precedes_escaping_in_every_field(self):
        token = "sk-synthetic_key_0123456789"
        source, rendered = self.render_fields(f'<img> [evidence]({token})')
        self.assertNotIn(token, source)
        self.assertNotIn(token, rendered.content)
        self.assertEqual(rendered.content.count('<img> [evidence]([REDACTED])'), 11)
        self.assert_inert(rendered)

    def test_hitlog_redaction_precedes_truncation_and_literal_rendering(self):
        prefix = "x" * 266
        raw = json.dumps({"probe": '<svg onload="alert(1)">', "detector": '[detector](https://attacker.invalid/)',
                          "prompt": prefix + "sk-synthetic_key_0123456789"}) + "\n"
        hitlog = self.out / "synthetic.hitlog.jsonl"
        hitlog.write_text(raw)
        parsed = parse_garak_hits(self.out)
        hits, files = parsed.hits, parsed.raw_files
        report = write_report(self.out, {"name": "target", "model": "model"}, [], {}, hits, files)
        source = report.read_text()
        rendered = RenderedReport(source)
        self.assertIn(prefix + "[REDACTED]", rendered.content)
        self.assertNotIn("sk-synthetic", source)
        self.assertIn('<svg onload="alert(1)">', rendered.content)
        self.assertNotIn("svg", rendered.tags)
        self.assertNotIn("a", rendered.tags)
        self.assertEqual(hitlog.read_text(), raw)


if __name__ == "__main__":
    unittest.main()
