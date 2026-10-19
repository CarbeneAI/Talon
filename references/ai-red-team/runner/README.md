# Talon AI Red-Team Runner

A thin orchestrator over open-source LLM red-team tooling. It runs the automated
attack classes against an **authorized** target, collects the output, and writes
a findings-report skeleton for a human tester to triage.

This is a harness, not an autopilot. It gets you to evidence faster. A person
still reads the output and decides what actually matters.

## Install

Run the Install, Configure, and Run commands from
`references/ai-red-team/runner` within this repository.

```bash
pip install -r requirements.txt
# optional, per phase:
npm install -g promptfoo      # phase 2 evals
# Manual phases 5 and 6: follow the selected tool's installation instructions.
# The runner does not invoke PyRIT or modelscan.
```

## Configure

```bash
cp config.example.yaml config.yaml
# edit config.yaml: set authorized: true, target name, and model
export OPENAI_API_KEY=sk-...   # garak reads the provider environment variable
```

## Run

```bash
python redteam.py --config config.yaml --dry-run   # validate + show the plan
python redteam.py --config config.yaml             # execute
```

Output lands in `engagements/<target>-<timestamp>/`:
- per-phase logs
- raw garak JSONL reports
- `findings-report.md`: untriaged skeleton

The runner writes its report before returning status 1 if a requested automated
command fails, times out, or is unavailable, or a configured promptfoo file is
missing. The report lists execution failures separately from intentional manual
phases. Status 0 means no execution failure was recorded; it does not establish
a clean assessment or completion of manual work. Configuration errors also exit
nonzero. A dry run writes no report and executes no probes.

The repository ignores directories named `engagements/` anywhere in the checkout,
so default output is covered from any working directory inside it, plus the copied
`references/ai-red-team/runner/config.yaml` and root `.mcp.json`. Examples and
fixtures outside `engagements/` remain trackable. Custom `--out` locations and
custom config paths require your own ignore rules or storage outside the
repository. Ignore rules do not protect files already tracked by Git. Keep
evidence access restricted, follow the engagement retention agreement, review
reports before sharing, and remove local evidence when that agreement requires.

## Phase coverage

| Phase | How it runs |
|-------|-------------|
| 1 recon / fingerprinting | manual (guidance printed) |
| 2 prompt injection | garak `promptinject`, `latentinjection` |
| 3 jailbreak | garak `dan`, `grandma` |
| 4 disclosure | garak `leakreplay`, `xss` |
| 5 tool / agent abuse | manual (guidance printed; PyRIT is not invoked) |
| 6 supply chain | manual (guidance printed for artifact review with modelscan/fickling) |

**Target types:** only `openai` is wired end-to-end today. `openai_compatible`
and `rest` need a garak generator option file built from the endpoint; that is
on the roadmap, and the runner refuses those types until it lands rather than
hit the wrong target silently.

For `openai`, leave `target.endpoint` empty and use
`target.api_key_env: OPENAI_API_KEY`. The garak command does not map custom key
variables or pass through endpoint settings, so validation rejects those
unsupported options before creating output or invoking tools, including during
a dry run. This guards configuration fields only. garak inherits the process
environment; review provider environment settings separately before testing.

**Reading results:** the runner parses garak's `.hitlog.jsonl`, where every line
is a confirmed hit. If it reports zero hits, open the raw hitlog and per-phase
`.log` files to confirm the run actually executed before you call it clean.

## Safety

- Runs only when `authorized: true` is set in the config.
- Validation requires `target.api_key_env: OPENAI_API_KEY` and checks that this
  provider environment variable is set. garak reads it directly. The runner does
  not pass the key on a command line.
- Subprocesses are invoked with argument lists, never a shell.
- Tool logs and the generated findings report redact a limited set of token
  patterns: `sk-`, `Bearer`, `xoxb-`, and certain GitHub token prefixes. This is
  not comprehensive secret detection. Review generated reports before sharing.
  Raw tool reports are preserved and may contain secrets or other sensitive
  evidence. Treat engagement output directories as sensitive.
- Interpolated report fields are literal text: target and model names, phases,
  hitlog filenames, probe and detector names, prompt/output excerpts, and failure
  or manual notes. Supported token patterns are redacted before escaping; hitlog
  prompt/output text is still redacted before its 280-character truncation.
  Field line breaks become spaces. HTML entities and Markdown punctuation are
  escaped, including URL punctuation, so evidence does not create HTML, images,
  links, or report sections in the tested CommonMark/GFM renderer. The template
  keeps its intended headings and table. Raw evidence is not modified.
  These fixtures do not establish identical behavior in every Markdown viewer;
  do not decode or concatenate untrusted HTML after rendering.
- **Treat engagement config files as trusted input.** `promptfoo_config` points
  at a file that promptfoo can use to execute arbitrary code (`exec:` providers,
  custom scripts). Do not run a config file you did not write or review.
- For authorized testing only.

## Tests

From the repository root, run the same minimal checks as
[the report-test CI job](../../../.github/workflows/runner-tests.yml):

```bash
cd references/ai-red-team/runner
python -m pip install -r requirements-test.txt
python -B -m unittest discover -v
```

Use Python 3.12 to match CI. `requirements-test.txt` pins PyYAML 6.0.3,
markdown-it-py 4.2.0, and linkify-it-py 2.2.0 as test dependencies. These 20 offline tests cover report redaction,
preservation of raw evidence, production `main()` success and failure paths
with mocked tool commands, fail-closed configuration with real validation,
the actual Git ignore rules in temporary repositories, and report rendering
with raw HTML and GFM autolinking enabled. They do not require scanner dependencies, invoke scanners, call
model APIs, or verify a live service, SSH MCP integration, or all Talon features.
