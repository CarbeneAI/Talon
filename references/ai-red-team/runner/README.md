# Talon AI Red-Team Runner

A thin orchestrator over open-source LLM red-team tooling. It runs the automated
attack classes against an **authorized** target, collects the output, and writes
a findings-report skeleton for a human tester to triage.

This is a harness, not an autopilot. It gets you to evidence faster. A person
still reads the output and decides what actually matters.

## Install

```bash
pip install -r requirements.txt
# optional, per phase:
npm install -g promptfoo      # phase 2 evals
pip install pyrit modelscan   # phases 5 and 6
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
| 5 tool / agent abuse | manual / PyRIT (guidance printed) |
| 6 supply chain | modelscan against the model artifact |

**Target types:** only `openai` is wired end-to-end today. `openai_compatible`
and `rest` need a garak generator option file built from the endpoint; that is
on the roadmap, and the runner refuses those types until it lands rather than
hit the wrong target silently.

**Reading results:** the runner parses garak's `.hitlog.jsonl`, where every line
is a confirmed hit. If it reports zero hits, open the raw hitlog and per-phase
`.log` files to confirm the run actually executed before you call it clean.

## Safety

- Runs only when `authorized: true` is set in the config.
- API keys are read from the environment, never from the config file, never
  printed, never passed on a command line.
- Subprocesses are invoked with argument lists, never a shell.
- Tool logs and the generated findings report are scrubbed of key-shaped tokens.
  Raw tool reports are preserved, so treat engagement output directories as sensitive.
- **Treat engagement config files as trusted input.** `promptfoo_config` points
  at a file that promptfoo can use to execute arbitrary code (`exec:` providers,
  custom scripts). Do not run a config file you did not write or review.
- For authorized testing only.

## Tests

From this directory, install `PyYAML` and run `python -B -m unittest discover -v`.
The tests use synthetic evidence files and do not run scanners or call model APIs.
