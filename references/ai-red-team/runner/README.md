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
# edit config.yaml — set authorized: true, target, and api_key_env
export OPENAI_API_KEY=sk-...   # the runner reads the key from the env, never the file
```

## Run

```bash
python redteam.py --config config.yaml --dry-run   # validate + show the plan
python redteam.py --config config.yaml             # execute
```

Output lands in `engagements/<target>-<timestamp>/`:
- per-phase logs
- raw garak JSONL reports
- `findings-report.md` — untriaged skeleton

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

**Reading results:** the runner parses garak's `.hitlog.jsonl`, where every line
is a confirmed hit. If it reports zero hits, open the raw hitlog and per-phase
`.log` files to confirm the run actually executed before you call it clean.

## Safety

- Runs only when `authorized: true` is set in the config.
- The configured API key is read from its named environment variable. The runner
  does not pass it on a command line.
- Subprocesses are invoked with argument lists, never a shell.
- Tool logs and the generated findings report redact a limited set of token
  patterns: `sk-`, `Bearer`, `xoxb-`, and certain GitHub token prefixes. This is
  not comprehensive secret detection. Review generated reports before sharing.
  Raw tool reports are preserved and may contain secrets or other sensitive
  evidence. Treat engagement output directories as sensitive.
- **Treat engagement config files as trusted input.** `promptfoo_config` points
  at a file that promptfoo can use to execute arbitrary code (`exec:` providers,
  custom scripts). Do not run a config file you did not write or review.
- For authorized testing only.

## Tests

From the repository root, run the same minimal checks as
[the report-test CI job](../../../.github/workflows/runner-tests.yml):

```bash
cd references/ai-red-team/runner
python -m pip install 'PyYAML==6.0.3'
python -B -m unittest discover -v
```

Use Python 3.12 to match CI. These four offline regression tests cover findings
report generation, token redaction, and preservation of raw evidence using
synthetic files. They do not require scanner dependencies, invoke scanners, call
model APIs, or verify a live service, SSH MCP integration, or all Talon features.
