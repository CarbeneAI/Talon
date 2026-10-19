# Talon — Claude Code Project Instructions

Talon is a penetration testing workflow toolkit that connects Claude Code to a Kali Linux VM via SSH MCP.

## MCP Server

Talon does not bundle or validate an SSH MCP provider. `mcp-config.example.json`
is a structure template with placeholder command and arguments, not a working
connection. Select a reviewed provider and register it as `kali-ssh` using the
[README setup instructions](README.md#quick-start). Claude Code uses `.mcp.json`
for shared project configuration; local registration uses `~/.claude.json`.
See the [official MCP documentation](https://code.claude.com/docs/en/mcp).

Run repository development, offline tests, and Claude Code registration commands
on the local workstation. Run target-facing security tools on the authorized
Kali VM through a verified MCP connection. SSH setup and file-copy commands run
where their instructions specify. Do not assume a provider or connection works
from the presence of the example configuration.

## Methodology

Follow the 5-phase pentest methodology defined in `references/` and `SKILL.md`:

1. **Recon** — `scripts/recon.sh <target-ip>` for automated initial recon
2. **Enumeration** — Use `references/service-enum.md` for per-service commands
3. **Exploitation** — Document and execute with searchsploit / metasploit / manual exploits
4. **Post-Exploitation** — PrivEsc enumeration, credential harvesting, persistence
5. **Reporting** — Use `references/report-template.md` for structured findings

## Obsidian Notes

Use templates in `templates/` for engagement tracking:

- `templates/engagement.md` — One per engagement, tracks all targets and credentials
- `templates/target.md` — One per machine, tracks recon, foothold, and PrivEsc

## Key References

- `references/service-enum.md` — Enumeration commands for 13 service types
- `references/report-template.md` — OSCP-style report structure
- `docs/setup-kali.md` — Kali VM setup guide
- `docs/ssh-access.md` — Remote access methods (SSH tunnel, VPN, ngrok, Cloudflare)
- `docs/usage.md` — Example prompts and workflows

## Security Rules

- Always confirm you have written authorization before testing any target
- Never store credentials, flags, or loot in this repository
- Keep scan output and results in local directories (gitignored)
- Rotate SSH keys regularly

## Common Prompts

Ask Claude:

- "Run recon on [IP] using Kali"
- "Enumerate [service] on [IP]"
- "I have a shell as [user] — check for PrivEsc paths"
- "Generate a report for this engagement"

## Offline runner development

From the repository root, use an installed `python3.12` executable to create a
test-only virtual environment outside the checkout. Use its interpreter for both
pip and tests; the shell's default `python` may select another version.

```bash
cd references/ai-red-team/runner
TALON_TEST_VENV="$HOME/.venvs/talon-tests-py312"
python3.12 -m venv "$TALON_TEST_VENV"
"$TALON_TEST_VENV/bin/python" -m pip install -r requirements-test.txt
"$TALON_TEST_VENV/bin/python" -B -m unittest discover -v
```

These checks use synthetic evidence, mocked tool commands, real configuration
validation, temporary Git repositories, and a CommonMark/GFM renderer with raw
HTML and autolinking enabled. They do not validate live tools or integrations. See the runner README for status semantics and storage limits:
requested automated failures or hitlog parsing issues return nonzero after
writing the report; manual
guidance alone does not fail. Directories named `engagements/` are ignored at
any depth in the checkout. Keep custom evidence paths outside the
repository or add explicit ignore rules before use.

For the supported `openai` runner target, leave `target.endpoint` empty and use
`target.api_key_env: OPENAI_API_KEY`. Unsupported values fail before creating
output or invoking tools. Provider environment settings remain inherited and
require separate review; these checks do not establish endpoint authenticity.

Keep every untrusted report field behind `report_text`. It redacts supported
token patterns before escaping HTML and Markdown punctuation and flattening
line breaks. Lone surrogate code points display as literal Unicode escape text,
so a decoded JSON string cannot prevent UTF-8 report writing. Keep hitlog redaction before truncation; never modify raw evidence
for display. Report structure is trusted template text, while names, evidence,
filenames, and phase notes must remain literal in the rendered report.

`parse_garak_hits` returns named `hits`, `raw_files`, and `issues` fields. Iterate
binary physical lines with strict UTF-8; keep valid rows and raw bytes unchanged.
Each parsing issue stores only filename, physical line (or file-level location),
and a fixed reason code. Never include rejected payloads or exception text in a
diagnostic. Preserve the current alternate names and string rendering of
object-valued prompt/output fields; do not impose a string-only schema. Keep
parsing issue counts separate from command failures. Missing/empty hitlogs are
inconclusive warning-only cases, not proof of a clean target or a failed command.

Allocate each execution with exclusive `tempfile.mkdtemp` beneath the resolved
output base, retaining the safe target/timestamp prefix. Never reuse an existing
engagement folder: it can mix evidence from separate runs. Preserve owner-only
POSIX child permissions and do not chmod an existing base. Keep dry runs and
invalid configuration free of output effects. Parent directories must be trusted;
these fixtures do not establish hostile-parent or Windows ACL guarantees.
