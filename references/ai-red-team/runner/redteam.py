#!/usr/bin/env python3
"""
Talon AI Red-Team runner.

Orchestrates open-source LLM red-team tooling (garak, promptfoo) against an
AUTHORIZED target, collects the output, and generates a findings report
skeleton mapped to the OWASP LLM Top 10.

For authorized testing only. See references/ai-red-team/README.md.

Usage:
    python redteam.py --config config.yaml --dry-run   # validate + show plan
    python redteam.py --config config.yaml             # run

This script never reads an API key from the config file. Credentials come from
the environment variable named in `target.api_key_env`, and are never printed
or passed on a command line.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: pyyaml. Install with: pip install -r requirements.txt")

# garak probe suites per phase. Kept conservative and well-known.
PHASE_GARAK_PROBES = {
    "2_prompt_injection": ["promptinject", "latentinjection"],
    "3_jailbreak": ["dan", "grandma"],
    "4_disclosure": ["leakreplay", "xss"],
}
# Phases handled by other means (documented, not auto-run here).
PHASE_MANUAL = {
    "1_recon": "Model fingerprinting — run garak recon probes or manual capability probes.",
    "5_tool_abuse": "Tool/agent abuse — manual, or PyRIT orchestration against the live agent.",
    "6_supply_chain": "Supply chain — run modelscan/fickling against the model artifact, not the endpoint.",
}
VALID_PHASES = list(PHASE_GARAK_PROBES) + list(PHASE_MANUAL)
# Only 'openai' is wired end-to-end today. openai_compatible/rest need a garak
# generator option file built from the endpoint; that is on the roadmap, so we
# refuse them rather than silently hit the wrong target.
SUPPORTED_TYPES = {"openai"}
ROADMAP_TYPES = {"openai_compatible", "rest"}
# Redact anything that looks like a key or bearer token from tool output on disk.
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|Bearer\s+\S+|xoxb-\S+|gh[pousr]_[A-Za-z0-9]{20,})")
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_COMMAND_TIMEOUT_SECONDS = 3600
_TIMEOUT_CLEANUP_SECONDS = 1.0
_TIMEOUT_REAP_SECONDS = 0.5
_TIMEOUT_CLEANUP_WARNING = "timeout cleanup incomplete: child processes or output pipes may remain"


def fail(msg: str) -> None:
    sys.exit(f"error: {msg}")


def load_config(path: Path) -> dict:
    if not path.is_file():
        fail(f"config not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        fail(f"invalid YAML in {path}: {exc}")
    if not isinstance(data, dict):
        fail("config must be a YAML mapping")
    return data


def validate(cfg: dict) -> dict:
    """Validate config and return a normalized copy. Fail closed."""
    if cfg.get("authorized") is not True:
        fail(
            "config.authorized is not true. This tool runs only against systems you "
            "own or are explicitly authorized to test. Set `authorized: true` in the "
            "config to confirm you have written authorization."
        )

    target = cfg.get("target")
    if not isinstance(target, dict):
        fail("config.target must be a mapping")

    name = str(target.get("name") or "").strip()
    if not name:
        fail("target.name is required")
    if name.startswith("-"):
        fail("target.name must not start with '-'")

    ttype = str(target.get("type") or "").strip().lower()
    if ttype in ROADMAP_TYPES:
        fail(f"target.type '{ttype}' is not wired yet (endpoint pass-through is on the "
             f"roadmap). Only these are supported today: {sorted(SUPPORTED_TYPES)}")
    if ttype not in SUPPORTED_TYPES:
        fail(f"target.type must be one of: {sorted(SUPPORTED_TYPES)}")

    model = str(target.get("model") or "").strip()
    if not model:
        fail("target.model is required")
    if model.startswith("-"):
        fail("target.model must not start with '-' (argument-injection guard)")

    endpoint = str(target.get("endpoint") or "").strip()
    if endpoint:
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            fail("target.endpoint must be an http(s) URL")

    key_env = str(target.get("api_key_env") or "").strip()
    if not key_env:
        fail("target.api_key_env is required (name of the env var holding the API key)")
    if not os.environ.get(key_env):
        fail(f"environment variable {key_env} is not set (holds the target API key)")

    # Distinguish "key absent -> full default" from "key present but empty -> error".
    if "phases" in cfg:
        phases = cfg["phases"]
    else:
        phases = list(PHASE_GARAK_PROBES)
    if not isinstance(phases, list) or not phases:
        fail("config.phases must be a non-empty list")
    unknown = [p for p in phases if p not in VALID_PHASES]
    if unknown:
        fail(f"unknown phases: {unknown}. valid: {VALID_PHASES}")

    promptfoo_config = cfg.get("promptfoo_config")
    if promptfoo_config is not None and not isinstance(promptfoo_config, str):
        fail("config.promptfoo_config must be a string path or null")

    return {
        "name": name,
        "type": ttype,
        "model": model,
        "endpoint": endpoint,
        "key_env": key_env,
        "phases": phases,
        "promptfoo_config": promptfoo_config,
    }


def safe_slug(name: str) -> str:
    # Collapses every path separator and '..' run to a hyphen, so the value can
    # only ever be a single, inert path component.
    slug = SAFE_NAME.sub("-", name).strip("-.")
    return slug or "target"


def scrub(text: str) -> str:
    """Redact key-shaped tokens before writing tool output to disk."""
    return SECRET_RE.sub("[REDACTED]", text)


def build_garak_cmd(cfg: dict, probes: list[str], report_prefix: Path) -> list[str]:
    # Arg list only. No shell. API key is NOT passed here — garak reads it from
    # the provider's own env var (e.g. OPENAI_API_KEY).
    return [
        "garak",
        "--model_type", "openai",
        "--model_name", cfg["model"],
        "--probes", ",".join(probes),
        "--report_prefix", str(report_prefix),
    ]


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    # TimeoutExpired may expose captured bytes even when text mode was requested.
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _kill_immediate_child(proc: subprocess.Popen) -> bool:
    try:
        if proc.poll() is None:
            proc.kill()
    except ProcessLookupError:
        pass
    except OSError:
        return False
    return True


def _signal_owned_work(proc: subprocess.Popen) -> bool:
    """Stop the POSIX command group, or the immediate child elsewhere."""
    incomplete = os.name != "posix"
    if os.name == "posix":
        try:
            # The process is the group leader of a session created for this command.
            # Signal by group even if the leader exited while descendants keep pipes open.
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            incomplete = True
            if not _kill_immediate_child(proc):
                incomplete = True
    else:
        # Without POSIX process groups, only the direct child is owned here.
        if not _kill_immediate_child(proc):
            incomplete = True
    return incomplete


def _close_process_pipes(proc: subprocess.Popen) -> bool:
    incomplete = False
    for stream in (proc.stdout, proc.stderr):
        if stream is None:
            continue
        try:
            stream.close()
        except OSError:
            incomplete = True
    return incomplete


def _cleanup_timed_out_process(
    proc: subprocess.Popen,
    previous_stdout: str | bytes | None,
    previous_stderr: str | bytes | None,
) -> tuple[str | bytes | None, str | bytes | None, bool]:
    """Kill owned work, drain for a bounded interval, then close and reap."""
    incomplete = _signal_owned_work(proc)
    latest_stdout = previous_stdout
    latest_stderr = previous_stderr
    try:
        stdout, stderr = proc.communicate(timeout=_TIMEOUT_CLEANUP_SECONDS)
        if stdout is not None:
            latest_stdout = stdout
        if stderr is not None:
            latest_stderr = stderr
    except subprocess.TimeoutExpired as exc:
        # A later communicate snapshot is cumulative. Keep it once, per stream.
        if exc.output is not None:
            latest_stdout = exc.output
        if exc.stderr is not None:
            latest_stderr = exc.stderr
        incomplete = True
    except Exception:
        incomplete = True

    if incomplete:
        incomplete = _close_process_pipes(proc) or incomplete
        if not _kill_immediate_child(proc):
            incomplete = True
        try:
            proc.wait(timeout=_TIMEOUT_REAP_SECONDS)
        except subprocess.TimeoutExpired:
            incomplete = True
        except Exception:
            incomplete = True
    return latest_stdout, latest_stderr, incomplete


def _cleanup_after_interruption(proc: subprocess.Popen) -> None:
    """Best-effort bounded cleanup that never replaces the original exception."""
    try:
        _signal_owned_work(proc)
    except BaseException:
        pass
    try:
        proc.communicate(timeout=_TIMEOUT_CLEANUP_SECONDS)
        return
    except BaseException:
        pass
    try:
        _close_process_pipes(proc)
    except BaseException:
        pass
    try:
        _kill_immediate_child(proc)
    except BaseException:
        pass
    try:
        proc.wait(timeout=_TIMEOUT_REAP_SECONDS)
    except BaseException:
        pass


def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str]:
    kwargs = {
        "cwd": str(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
    }
    if os.name == "posix":
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen(cmd, **kwargs)
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except OSError as exc:
        return 1, f"failed to run {cmd[0]}: {exc}"

    try:
        stdout, stderr = proc.communicate(timeout=_COMMAND_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        try:
            stdout, stderr, incomplete = _cleanup_timed_out_process(
                proc, exc.output, exc.stderr
            )
        except BaseException:
            # An interrupt during timeout cleanup still belongs to the caller.
            _cleanup_after_interruption(proc)
            raise
        output = _timeout_text(stdout) + _timeout_text(stderr)
        if output and not output.endswith(("\n", "\r")):
            output += "\n"
        output += f"timeout: {cmd[0]}"
        if incomplete:
            output += f"\n{_TIMEOUT_CLEANUP_WARNING}"
        return 124, output
    except BaseException:
        _cleanup_after_interruption(proc)
        raise
    return proc.returncode, _timeout_text(stdout) + _timeout_text(stderr)


def parse_garak_hits(out_dir: Path) -> tuple[list[dict], list[str]]:
    """Read garak's purpose-built hitlog(s). Every line in a hitlog is a
    confirmed hit, so there is no pass/fail threshold to reimplement. Field
    extraction is defensive: garak's schema varies by version, so we fall back
    gracefully and always surface the raw file path for the tester."""
    hits: list[dict] = []
    raw_files: list[str] = []
    for hl in sorted(out_dir.glob("*.hitlog.jsonl")):
        raw_files.append(hl.name)
        for line in hl.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            hits.append({
                "probe": str(rec.get("probe") or rec.get("probe_classname") or "unknown"),
                "detector": str(rec.get("detector") or rec.get("detector_name") or ""),
                "prompt": str(rec.get("prompt") or rec.get("output") or "")[:280],
            })
    return hits, raw_files


def write_report(out_dir: Path, cfg: dict, ran: list[str], skipped: dict,
                 hits: list[dict], raw_files: list[str]) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# AI / LLM Red-Team Assessment Report",
        "",
        f"**Target:** {cfg['name']} ({cfg['model']})",
        f"**Generated:** {ts}",
        f"**Phases run:** {', '.join(ran) or 'none'}",
        "",
        "> Skeleton auto-generated by the Talon AI Red-Team runner. A human tester "
        "must triage every item below: assign real severity, confirm reproduction, "
        "and discard false positives before this goes to a client.",
        "",
        "## Automated hits (from garak hitlog, untriaged)",
        "",
    ]
    if hits:
        lines += [f"garak recorded {len(hits)} hit(s). Raw hitlog: {', '.join(raw_files)}",
                  "", "| Probe | Detector | Prompt/output (truncated) |", "|---|---|---|"]
        for h in hits:
            prompt = h["prompt"].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {h['probe']} | {h['detector']} | {prompt} |")
    elif raw_files:
        lines.append(f"garak produced hitlog file(s) ({', '.join(raw_files)}) but no "
                     "hits were parsed. Open the raw hitlog to confirm before trusting a clean result.")
    else:
        lines.append("_No garak hitlog found. Confirm the run completed and probes executed "
                     "(check the per-phase .log files) before treating this as a clean result._")
    lines += ["", "## Phases needing manual work", ""]
    for phase, note in skipped.items():
        lines.append(f"- **{phase}**: {note}")
    lines += [
        "",
        "## Next steps for the tester",
        "1. Triage each automated hit: severity, reproduction, OWASP LLM + MITRE ATLAS tags.",
        "2. Complete the manual phases above.",
        "3. Roll findings up to NIST AI RMF and fill the full template at "
        "`references/ai-red-team/report-template.md`.",
        "",
    ]
    report_path = out_dir / "findings-report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Talon AI Red-Team runner")
    ap.add_argument("--config", required=True, type=Path, help="path to engagement config YAML")
    ap.add_argument("--out", type=Path, default=Path("engagements"), help="output base directory")
    ap.add_argument("--dry-run", action="store_true", help="validate config and print the plan only")
    args = ap.parse_args()

    cfg = validate(load_config(args.config))

    print(f"Target: {cfg['name']} ({cfg['model']}, type={cfg['type']})")
    print(f"Phases: {', '.join(cfg['phases'])}")
    print("Authorization: confirmed in config (authorized: true)")

    if args.dry_run:
        print("\n[dry-run] plan:")
        for phase in cfg["phases"]:
            if phase in PHASE_GARAK_PROBES:
                print(f"  {phase}: garak probes -> {', '.join(PHASE_GARAK_PROBES[phase])}")
            else:
                print(f"  {phase}: manual — {PHASE_MANUAL[phase]}")
        if cfg["promptfoo_config"]:
            print(f"  promptfoo: {cfg['promptfoo_config']}")
        print("\n[dry-run] no probes executed.")
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = args.out.resolve()
    out_dir = base / f"{safe_slug(cfg['name'])}-{stamp}"
    # Defense-in-depth: safe_slug already yields an inert single component, but
    # confirm the resolved path stays under the base dir before creating it.
    if base not in out_dir.resolve().parents:
        fail("resolved output path escaped the output base directory")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output: {out_dir}")

    ran: list[str] = []
    skipped: dict[str, str] = {}

    for phase in cfg["phases"]:
        if phase in PHASE_GARAK_PROBES:
            # Per-phase prefix so phases never overwrite each other's reports.
            report_prefix = out_dir / f"garak-{phase}"
            cmd = build_garak_cmd(cfg, PHASE_GARAK_PROBES[phase], report_prefix)
            print(f"\n>> {phase}: {' '.join(cmd)}")
            code, output = run_cmd(cmd, out_dir)
            (out_dir / f"{phase}.log").write_text(scrub(output), encoding="utf-8")
            if code == 0:
                ran.append(phase)
            else:
                skipped[phase] = f"garak exited {code} — see {phase}.log"
        else:
            skipped[phase] = PHASE_MANUAL[phase]

    if cfg["promptfoo_config"]:
        pf = Path(cfg["promptfoo_config"])
        if pf.is_file():
            cmd = ["promptfoo", "redteam", "run", "-c", str(pf)]
            print(f"\n>> promptfoo: {' '.join(cmd)}")
            code, output = run_cmd(cmd, out_dir)
            (out_dir / "promptfoo.log").write_text(scrub(output), encoding="utf-8")
            if code == 0:
                ran.append("promptfoo")
            else:
                skipped["promptfoo"] = f"promptfoo exited {code} — see promptfoo.log"
        else:
            skipped["promptfoo"] = f"config not found: {pf}"

    hits, raw_files = parse_garak_hits(out_dir)
    report = write_report(out_dir, cfg, ran, skipped, hits, raw_files)
    print(f"\nReport skeleton: {report}")
    print(f"Automated hits (untriaged): {len(hits)}")


if __name__ == "__main__":
    main()
