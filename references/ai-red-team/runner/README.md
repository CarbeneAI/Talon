# Talon AI Red-Team Runner

A thin orchestrator over open-source LLM red-team tooling. It runs the automated
attack classes against an **authorized** target, collects the output, and writes
a findings-report skeleton for a human tester to triage.

This is a harness, not an autopilot. It gets you to evidence faster. A person
still reads the output and decides what actually matters.

## Install

Run the Install, Configure, and Run commands from
`references/ai-red-team/runner` within this repository. The examples select an
installed `python3.12` executable to match the offline CI interpreter. Create the
virtual environment outside the checkout, then activate it so `garak` resolves
from that environment when the runner invokes it.

Garak `0.17.1` declares Python `>=3.11`; Talon's CI and the offline CLI
verification use Python 3.12.

```bash
TALON_RUNNER_VENV="$HOME/.venvs/talon-runner-py312"
python3.12 -m venv "$TALON_RUNNER_VENV"
. "$TALON_RUNNER_VENV/bin/activate"
"$TALON_RUNNER_VENV/bin/python" -m pip install -r requirements.txt
# optional, per phase:
npm install -g promptfoo      # phase 2 evals
# Manual phases 5 and 6: follow the selected tool's installation instructions.
# The runner does not invoke PyRIT or modelscan.
```

If you open another terminal, set `TALON_RUNNER_VENV` to the same path and
activate it again before configuring or running the harness. Do not install
runtime/scanner dependencies for the offline tests below.

The runner pins Garak to `0.17.1`. The lightweight unit tests check the runner's
CLI arguments and phase selectors without installing Garak. They run on
Ubuntu and macOS with Python 3.12. Installing Garak also installs its
model-scanning dependencies. The plugin names below were verified against
`0.17.1` using list-only mode on macOS with Python 3.12; that check does not
contact a provider or execute probes.

## Configure

```bash
cp config.example.yaml config.yaml
# edit config.yaml: set authorized: true, target name, and model
export OPENAI_API_KEY=sk-...   # garak reads the provider environment variable
```

## Run

```bash
"$TALON_RUNNER_VENV/bin/python" redteam.py --config config.yaml --dry-run   # validate + show the plan
"$TALON_RUNNER_VENV/bin/python" redteam.py --config config.yaml             # execute
```

Output lands in `engagements/<target>-<timestamp>-<random>/`:
- per-phase logs
- raw garak JSONL reports
- `findings-report.md`: untriaged skeleton

Each execution exclusively creates a new output directory, including runs with
identical target names and timestamps. It does not reuse an old timestamp
folder. The new child has owner-only POSIX permissions (`0700`, possibly further
restricted by the process umask); existing output-base permissions are unchanged.
Choose a trusted output parent. These checks do not address hostile parent-directory
replacement or establish Windows ACL behavior. Dry runs and invalid configuration
do not create output.

The runner writes its report before returning status 1 if a requested automated
command fails, times out, or is unavailable, a configured promptfoo file is
missing, or hitlog parsing records an issue. The report lists execution failures separately from intentional manual
phases and evidence parsing issues. Status 0 means neither an execution failure
nor a parsing issue was recorded; it does not establish
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
| 2 prompt injection | Garak `probes.promptinject`, `probes.latentinjection` |
| 3 jailbreak | Garak `probes.dan`, `probes.grandma` |
| 4 disclosure | Garak `probes.leakreplay`, `probes.web_injection.MarkdownXSS`, and `probes.web_injection.TaskXSS` |
| 5 tool / agent abuse | manual (guidance printed; PyRIT is not invoked) |
| 6 supply chain | manual (guidance printed for artifact review with modelscan/fickling) |

To verify the installed plugin names without running probes, use Garak's
list-only mode, for example:

```bash
garak --list_probes --spec probes.leakreplay,probes.web_injection.MarkdownXSS,probes.web_injection.TaskXSS
```

After creating the separate environment described in [Tests](#tests), run the
lightweight command-construction tests from this directory with:

```bash
"$TALON_TEST_VENV/bin/python" -B -m unittest test_garak_cli -v
```

**Target types:** the runner currently constructs Garak commands only for
`openai` targets. Provider execution was not part of the recorded CLI
verification. `openai_compatible` and `rest` need a Garak generator option file
built from the endpoint; the runner refuses those types until that support is
implemented rather than hitting the wrong target silently.

For `openai`, leave `target.endpoint` empty and use
`target.api_key_env: OPENAI_API_KEY`. The garak command does not map custom key
variables or pass through endpoint settings, so validation rejects those
unsupported options before creating output or invoking tools, including during
a dry run. This guards configuration fields only. garak inherits the process
environment; review provider environment settings separately before testing.

## Evidence parsing

The runner reads each `.hitlog.jsonl` as binary physical lines and decodes each
nonblank record as UTF-8 JSON. Invalid UTF-8, malformed JSON, non-object JSON
records, and file read failures are reported with a filename, a 1-based physical
line number (or file-level location), and a fixed reason. Rejected payloads and
exception messages are never retained in those diagnostics. Valid rows before
or after a bad row, and other readable files, are preserved. Unicode line
separators inside JSON strings do not split records; blank/whitespace-only lines
and CRLF are supported. The raw bytes remain unchanged.

The decoder rejects the nonstandard `NaN`, `Infinity`, and `-Infinity` literals
and records unsupported nesting as a JSON decoding issue. It otherwise retains
Python's JSON behavior, including last-value handling of duplicate object keys.
This is not a full garak schema validator. Existing probe/detector alternate
names and Python string rendering of structured prompt/output values are
preserved. Official garak records include Conversation/Message objects, as shown
by its [hitlog writer](https://github.com/NVIDIA/garak/blob/cc1215c5c301a69f115b0b2b7ef8e4172ae2e7fc/garak/evaluators/base.py#L123)
and [data types](https://github.com/NVIDIA/garak/blob/cc1215c5c301a69f115b0b2b7ef8e4172ae2e7fc/garak/attempt.py#L21).
This change does not introduce a structured-message adapter.

The report says `Parsed N untriaged hit(s)` and lists evidence parsing issues
separately from execution failures. Any parsing issue makes the runner return
status 1 after writing the report. A missing, empty, or whitespace-only hitlog
is explicitly inconclusive and does not count as a parsing failure: garak opens
hitlogs in its detector-failure path, so absence alone does not prove execution
failed. Zero parsed hits does not establish that the target is safe. Review the
raw hitlog and per-phase logs, confirm the run completed, and triage evidence.

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
  Field line breaks become spaces. Unpaired surrogate code points decoded from
  JSON are shown as literal `\uXXXX` text so one value cannot prevent UTF-8 report
  writing. HTML entities and Markdown punctuation are
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

From the repository root, create a separate Python 3.12 test environment outside
the checkout and install only the pinned offline dependencies. No activation is
needed because every command uses that environment's interpreter explicitly.
These are the same checks and dependency set as
[the report-test CI job](../../../.github/workflows/runner-tests.yml):

```bash
cd references/ai-red-team/runner
TALON_TEST_VENV="$HOME/.venvs/talon-tests-py312"
python3.12 -m venv "$TALON_TEST_VENV"
"$TALON_TEST_VENV/bin/python" -m pip install -r requirements-test.txt
"$TALON_TEST_VENV/bin/python" -B -m unittest discover -v
```

CI uses `actions/setup-python` to select Python 3.12 before its `python`
commands. The local commands above select it explicitly instead of relying on
the shell's `python` or `pip` aliases. `requirements-test.txt` pins PyYAML 6.0.3,
markdown-it-py 4.2.0, and linkify-it-py 2.2.0 as test dependencies. The offline tests cover physical-line hitlog parsing, fixed corruption/read
diagnostics, official structured fields and legacy extraction, exclusive run
directories and POSIX permissions, report redaction,
preservation of raw evidence, production `main()` success and failure paths
with mocked tool commands, fail-closed configuration with real validation,
the actual Git ignore rules in temporary repositories, and report rendering
with raw HTML and GFM autolinking enabled. They do not require scanner dependencies, invoke scanners, call
model APIs, or verify a live service, SSH MCP integration, or all Talon features.
