"""Exercise bounded command timeout cleanup with synthetic child processes."""
import contextlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

import redteam


class TimeoutOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="talon-timeout-output-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runner = Path(__file__).resolve().parent

    def _write_fixture_scripts(self):
        command = self.root / "command.py"
        command.write_text(
            "import json, os, pathlib, subprocess, sys, time\n"
            "mode, record_name, ready_name, child_code = sys.argv[1:]\n"
            "record_path = pathlib.Path(record_name)\n"
            "ready_path = pathlib.Path(ready_name)\n"
            "record = {'leader': os.getpid(), 'group': os.getpgrp(), "
            "'descendants': [], 'detached_groups': []}\n"
            "record_path.write_text(json.dumps(record))\n"
            "stdio = {}\n"
            "if mode == 'closed':\n"
            "    stdio = {'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}\n"
            "child = subprocess.Popen([sys.executable, '-c', child_code, mode, "
            "str(ready_path)], **stdio)\n"
            "record['descendants'].append(child.pid)\n"
            "record_path.write_text(json.dumps(record))\n"
            "if mode == 'detached':\n"
            "    deadline = time.monotonic() + 3\n"
            "    while not ready_path.exists() and time.monotonic() < deadline:\n"
            "        time.sleep(0.01)\n"
            "    if not ready_path.exists():\n"
            "        raise RuntimeError('detached child did not become ready')\n"
            "    detached = json.loads(ready_path.read_text())\n"
            "    record['detached_groups'].append(detached['group'])\n"
            "    record_path.write_text(json.dumps(record))\n"
            "print('leader stdout ready', flush=True)\n"
            "print('leader stderr ready', file=sys.stderr, flush=True)\n"
            "if mode == 'leader-exited':\n"
            "    raise SystemExit(0)\n"
            "time.sleep(30)\n",
            encoding="utf-8",
        )
        child_code = (
            "import json, os, pathlib, sys, time\n"
            "mode, ready_name = sys.argv[1:]\n"
            "if mode in ('detached', 'interrupt', 'interrupt-cleanup'):\n"
            "    if mode == 'detached':\n"
            "        os.setsid()\n"
            "    pathlib.Path(ready_name).write_text(json.dumps({"
            "'pid': os.getpid(), 'group': os.getpgrp()}))\n"
            "    if mode == 'detached':\n"
            "        print('detached stdout ready', flush=True)\n"
            "        print('detached stderr ready', file=sys.stderr, flush=True)\n"
            "time.sleep(30)\n"
        )
        return command, child_code

    def _write_driver(self):
        driver = self.root / "driver.py"
        driver.write_text(
            "import json, os, pathlib, signal, subprocess, sys, time\n"
            "runner, observer_name, settings_json = sys.argv[1:]\n"
            "settings = json.loads(settings_json)\n"
            "observer = pathlib.Path(observer_name)\n"
            "sys.path.insert(0, runner)\n"
            "import redteam\n"
            "redteam._COMMAND_TIMEOUT_SECONDS = settings['timeout']\n"
            "redteam._TIMEOUT_CLEANUP_SECONDS = settings['cleanup']\n"
            "redteam._TIMEOUT_REAP_SECONDS = settings['reap']\n"
            "original_popen = subprocess.Popen\n"
            "command_process = []\n"
            "def observed_popen(*args, **kwargs):\n"
            "    proc = original_popen(*args, **kwargs)\n"
            "    group = proc.pid if kwargs.get('start_new_session') else os.getpgrp()\n"
            "    observer.write_text(json.dumps({'pid': proc.pid, 'group': group}))\n"
            "    command_process.append(proc)\n"
            "    if settings.get('interrupt'):\n"
            "        original_communicate = proc.communicate\n"
            "        interrupted = [False]\n"
            "        def interrupt_once(*call_args, **call_kwargs):\n"
            "            if not interrupted[0]:\n"
            "                interrupted[0] = True\n"
            "                ready = pathlib.Path(settings['ready'])\n"
            "                deadline = time.monotonic() + 3\n"
            "                while not ready.exists() and time.monotonic() < deadline:\n"
            "                    time.sleep(0.01)\n"
            "                if not ready.exists():\n"
            "                    raise RuntimeError('command fixture did not become ready')\n"
            "                raise KeyboardInterrupt\n"
            "            return original_communicate(*call_args, **call_kwargs)\n"
            "        proc.communicate = interrupt_once\n"
            "    elif settings.get('interrupt_during_cleanup'):\n"
            "        original_communicate = proc.communicate\n"
            "        calls = [0]\n"
            "        def interrupt_during_cleanup(*call_args, **call_kwargs):\n"
            "            calls[0] += 1\n"
            "            if calls[0] == 1:\n"
            "                ready = pathlib.Path(settings['ready'])\n"
            "                deadline = time.monotonic() + 3\n"
            "                while not ready.exists() and time.monotonic() < deadline:\n"
            "                    time.sleep(0.01)\n"
            "                if not ready.exists():\n"
            "                    raise RuntimeError('command fixture did not become ready')\n"
            "                raise subprocess.TimeoutExpired(proc.args, call_kwargs.get('timeout'), output='synthetic partial\\n')\n"
            "            if calls[0] == 2:\n"
            "                raise KeyboardInterrupt\n"
            "            return original_communicate(*call_args, **call_kwargs)\n"
            "        proc.communicate = interrupt_during_cleanup\n"
            "    return proc\n"
            "subprocess.Popen = observed_popen\n"
            "original_killpg = os.killpg\n"
            "if settings.get('fail_group_signal'):\n"
            "    def fail_owned_group(group, sig):\n"
            "        data = json.loads(observer.read_text()) if observer.exists() else {}\n"
            "        if group == data.get('group') and sig == signal.SIGKILL:\n"
            "            raise PermissionError('synthetic group signal failure')\n"
            "        return original_killpg(group, sig)\n"
            "    os.killpg = fail_owned_group\n"
            "started = time.monotonic()\n"
            "try:\n"
            "    status, output = redteam.run_cmd(settings['command'], pathlib.Path(settings['cwd']))\n"
            "    result = {'status': status, 'output': output}\n"
            "except KeyboardInterrupt:\n"
            "    result = {'interrupt': 'KeyboardInterrupt'}\n"
            "finally:\n"
            "    subprocess.Popen = original_popen\n"
            "    os.killpg = original_killpg\n"
            "result['elapsed'] = time.monotonic() - started\n"
            "print(json.dumps(result), flush=True)\n",
            encoding="utf-8",
        )
        return driver

    def _read_json(self, path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _kill_group(group):
        if os.name != "posix" or not group or group == os.getpgrp():
            return
        try:
            os.killpg(group, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            pass

    @staticmethod
    def _kill_pid(pid):
        if not pid or pid == os.getpid():
            return
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            pass

    def _process_state(self, pid):
        result = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        return result.stdout.strip()

    def _is_executing(self, pid):
        state = self._process_state(pid)
        return bool(state) and not state.startswith("Z")

    def _wait_until_stopped(self, pids, timeout=2.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            running = [pid for pid in pids if self._is_executing(pid)]
            if not running:
                return []
            time.sleep(0.02)
        return [pid for pid in pids if self._is_executing(pid)]

    def _cleanup_fixture(self, outer, observer_path, record_path, ready_path):
        observer = self._read_json(observer_path)
        record = self._read_json(record_path)
        ready = self._read_json(ready_path)
        groups = {
            outer.pid,
            observer.get("group"),
            record.get("group"),
            *record.get("detached_groups", []),
        }
        pids = {
            outer.pid,
            observer.get("pid"),
            record.get("leader"),
            *record.get("descendants", []),
            ready.get("pid"),
        }
        for group in groups:
            self._kill_group(group)
        for pid in pids:
            self._kill_pid(pid)
        if outer.poll() is None:
            try:
                outer.kill()
            except OSError:
                pass
        try:
            outer.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        running = self._wait_until_stopped([pid for pid in pids if pid])
        self.assertEqual(running, [], f"fixture processes remain active: {running}")

    def _run_owned_command(
        self, mode, *, fail_group_signal=False, interrupt=False, interrupt_during_cleanup=False
    ):
        command_script, child_code = self._write_fixture_scripts()
        driver = self._write_driver()
        record = self.root / f"{mode}.processes.json"
        ready = self.root / f"{mode}.ready.json"
        observer = self.root / f"{mode}.observer.json"
        command = [
            sys.executable,
            str(command_script),
            mode,
            str(record),
            str(ready),
            child_code,
        ]
        settings = {
            "command": command,
            "cwd": str(self.root),
            "timeout": 0.35,
            "cleanup": 0.2,
            "reap": 0.2,
            "record": str(record),
            "ready": str(ready),
            "fail_group_signal": fail_group_signal,
            "interrupt": interrupt,
            "interrupt_during_cleanup": interrupt_during_cleanup,
        }
        outer_kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True}
        if os.name == "posix":
            outer_kwargs["start_new_session"] = True
        outer = subprocess.Popen(
            [sys.executable, str(driver), str(self.runner), str(observer), json.dumps(settings)],
            **outer_kwargs,
        )
        self.addCleanup(self._cleanup_fixture, outer, observer, record, ready)
        started = time.monotonic()
        try:
            stdout, stderr = outer.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            self.fail("outer watchdog expired while waiting for run_cmd")
        self.assertEqual(outer.returncode, 0, f"driver failed: {stderr}\n{stdout}")
        payload = json.loads(stdout.strip().splitlines()[-1])
        payload["outer_elapsed"] = time.monotonic() - started
        return payload, self._read_json(record), self._read_json(ready)

    def test_normal_and_missing_commands_preserve_results(self):
        code, output = redteam.run_cmd(
            [sys.executable, "-c", "import os,sys; print(os.getcwd()); print('stderr',file=sys.stderr); sys.exit(7)"],
            self.root,
        )
        self.assertEqual(code, 7)
        self.assertEqual(output, f"{self.root.resolve()}\nstderr\n")
        self.assertEqual(redteam.run_cmd([str(self.root / "missing-tool")], self.root),
                         (127, f"command not found: {self.root / 'missing-tool'}"))

    @unittest.skipUnless(os.name == "posix", "process-group behavior requires POSIX")
    def test_timeout_kills_owned_descendants_and_keeps_streams_once(self):
        result, record, _ = self._run_owned_command("inherited")
        self.assertEqual(result["status"], 124)
        self.assertIn("leader stdout ready\n", result["output"])
        self.assertIn("leader stderr ready\n", result["output"])
        self.assertEqual(result["output"].count("leader stdout ready"), 1)
        self.assertEqual(result["output"].count("leader stderr ready"), 1)
        self.assertIn(f"timeout: {sys.executable}", result["output"])
        self.assertNotIn("cleanup incomplete", result["output"])
        self.assertLess(result["outer_elapsed"], 3)
        pids = [record["leader"], *record["descendants"]]
        self.assertEqual(self._wait_until_stopped(pids), [])

    @unittest.skipUnless(os.name == "posix", "process-group behavior requires POSIX")
    def test_timeout_kills_same_group_descendant_with_closed_pipes(self):
        result, record, _ = self._run_owned_command("closed")
        self.assertEqual(result["status"], 124)
        self.assertIn("leader stdout ready\n", result["output"])
        self.assertLess(result["outer_elapsed"], 3)
        pids = [record["leader"], *record["descendants"]]
        self.assertEqual(self._wait_until_stopped(pids), [])

    @unittest.skipUnless(os.name == "posix", "process-group behavior requires POSIX")
    def test_timeout_kills_group_when_leader_exited_but_descendant_holds_pipes(self):
        result, record, _ = self._run_owned_command("leader-exited")
        self.assertEqual(result["status"], 124)
        self.assertIn("leader stdout ready\n", result["output"])
        self.assertIn("leader stderr ready\n", result["output"])
        self.assertNotIn("cleanup incomplete", result["output"])
        self.assertFalse(self._is_executing(record["leader"]))
        self.assertEqual(self._wait_until_stopped(record["descendants"]), [])

    @unittest.skipUnless(os.name == "posix", "process-group behavior requires POSIX")
    def test_detached_descendant_is_bounded_reported_and_torn_down(self):
        result, record, ready = self._run_owned_command("detached")
        self.assertEqual(result["status"], 124)
        self.assertEqual(result["output"].count("detached stdout ready"), 1)
        self.assertEqual(result["output"].count("leader stdout ready"), 1)
        self.assertIn("timeout cleanup incomplete: child processes or output pipes may remain",
                      result["output"])
        self.assertLess(result["outer_elapsed"], 3)
        self.assertFalse(self._is_executing(record["leader"]))
        self.assertTrue(self._is_executing(ready["pid"]))

    @unittest.skipUnless(os.name == "posix", "process-group behavior requires POSIX")
    def test_group_signal_failure_is_reported_and_teardown_kills_descendant(self):
        result, record, _ = self._run_owned_command("signal-failure", fail_group_signal=True)
        self.assertEqual(result["status"], 124)
        self.assertIn("leader stdout ready\n", result["output"])
        self.assertIn("timeout cleanup incomplete: child processes or output pipes may remain",
                      result["output"])
        self.assertLess(result["outer_elapsed"], 3)
        self.assertTrue(self._is_executing(record["descendants"][0]))

    @unittest.skipUnless(os.name == "posix", "process-group behavior requires POSIX")
    def test_keyboard_interrupt_propagates_after_owned_group_cleanup(self):
        result, record, _ = self._run_owned_command("interrupt", interrupt=True)
        self.assertEqual(result.get("interrupt"), "KeyboardInterrupt")
        self.assertLess(result["outer_elapsed"], 3)
        pids = [record["leader"], *record["descendants"]]
        self.assertEqual(self._wait_until_stopped(pids), [])

    @unittest.skipUnless(os.name == "posix", "process-group behavior requires POSIX")
    def test_keyboard_interrupt_during_timeout_cleanup_is_not_swallowed(self):
        result, record, _ = self._run_owned_command(
            "interrupt-cleanup", interrupt_during_cleanup=True
        )
        self.assertEqual(result.get("interrupt"), "KeyboardInterrupt")
        self.assertLess(result["outer_elapsed"], 3)
        pids = [record["leader"], *record["descendants"]]
        self.assertEqual(self._wait_until_stopped(pids), [])

    def test_timeout_stream_normalization(self):
        self.assertEqual(redteam._timeout_text(None), "")
        self.assertEqual(redteam._timeout_text("captured text"), "captured text")
        self.assertEqual(redteam._timeout_text(b"captured bytes"), "captured bytes")
        self.assertEqual(redteam._timeout_text(b"bad utf8: \xff"), "bad utf8: \ufffd")

    def test_main_writes_timeout_output_through_existing_scrub(self):
        config = {
            "name": "synthetic-target",
            "type": "openai",
            "model": "synthetic-model",
            "endpoint": "",
            "key_env": "SYNTHETIC_KEY",
            "phases": ["2_prompt_injection"],
            "promptfoo_config": None,
        }
        output_base = self.root / "engagements"
        argv = ["redteam.py", "--config", "synthetic.yaml", "--out", str(output_base)]
        with patch.object(sys, "argv", argv), \
                patch.object(redteam, "load_config", return_value={}), \
                patch.object(redteam, "validate", return_value=config), \
                patch.object(redteam, "run_cmd", return_value=(
                    124,
                    "partial garak output sk-abcdefghijklmnopqrst\n"
                    "partial stderr\ntimeout: garak",
                )), \
                contextlib.redirect_stdout(io.StringIO()):
            try:
                main_status = redteam.main()
            except SystemExit as exc:
                main_status = exc.code

        # The upstream baseline has no execution status; the report PR returns nonzero.
        if main_status is not None:
            self.assertEqual(main_status, 1)
        logs = list(output_base.glob("*/2_prompt_injection.log"))
        self.assertEqual(len(logs), 1)
        log = logs[0].read_text(encoding="utf-8")
        self.assertIn("partial garak output", log)
        self.assertIn("partial stderr", log)
        self.assertIn("timeout: garak", log)
        self.assertIn("[REDACTED]", log)
        self.assertNotIn("sk-abcdefghijklmnopqrst", log)


if __name__ == "__main__":
    unittest.main()
