#!/usr/bin/env python3
"""Focused regression tests for the CAD dialog-state guard."""

from __future__ import annotations

import importlib.util
import os
import signal
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_cad_script_safely.py"
SPEC = importlib.util.spec_from_file_location("cad_guard", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {SCRIPT}")
cad_guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cad_guard
SPEC.loader.exec_module(cad_guard)


class CadAutomationGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_snapshot = cad_guard._snapshot_dialog_settings
        self.original_restore = cad_guard._restore_dialog_settings
        self.snapshot = [object()]
        self.restored: list[object] = []
        cad_guard._snapshot_dialog_settings = lambda: self.snapshot
        cad_guard._restore_dialog_settings = lambda values: self.restored.append(values)

    def tearDown(self) -> None:
        cad_guard._snapshot_dialog_settings = self.original_snapshot
        cad_guard._restore_dialog_settings = self.original_restore

    def assert_restored_once(self) -> None:
        self.assertEqual(self.restored, [self.snapshot])

    def test_success_restores_state(self) -> None:
        result = cad_guard.run_guarded([sys.executable, "-c", "raise SystemExit(0)"])
        self.assertEqual(result, 0)
        self.assert_restored_once()

    def test_nonzero_exit_restores_state(self) -> None:
        result = cad_guard.run_guarded([sys.executable, "-c", "raise SystemExit(7)"])
        self.assertEqual(result, 7)
        self.assert_restored_once()

    def test_timeout_terminates_child_and_restores_state(self) -> None:
        result = cad_guard.run_guarded(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            timeout=0.2,
        )
        self.assertEqual(result, cad_guard.TIMEOUT_EXIT_CODE)
        self.assert_restored_once()

    def test_external_child_termination_restores_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cad-guard-kill-") as temp:
            pid_path = Path(temp) / "pid.txt"
            code = (
                "import os,time,pathlib; "
                f"pathlib.Path({str(pid_path)!r}).write_text(str(os.getpid()), encoding='utf-8'); "
                "time.sleep(30)"
            )
            results: list[int] = []
            errors: list[BaseException] = []

            def run() -> None:
                try:
                    results.append(cad_guard.run_guarded([sys.executable, "-c", code]))
                except BaseException as exc:
                    errors.append(exc)

            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            deadline = time.time() + 10
            while not pid_path.exists() and time.time() < deadline:
                time.sleep(0.05)
            self.assertTrue(pid_path.exists(), "child did not publish its PID")
            os.kill(int(pid_path.read_text(encoding="utf-8")), signal.SIGTERM)
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive(), "guard did not observe child termination")
            self.assertFalse(errors)
            self.assertEqual(len(results), 1)
            self.assertNotEqual(results[0], 0)
            self.assert_restored_once()

    def test_unsafe_script_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cad-guard-script-") as temp:
            script = Path(temp) / "unsafe.scr"
            script.write_text("_.FILEDIA\n0\n_.CMDDIA\n0\n_.QUIT\n_N\n", encoding="utf-8")
            with self.assertRaises(cad_guard.UnsafeCadScriptError):
                cad_guard.validate_cad_script(script)

    def test_restored_script_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cad-guard-script-") as temp:
            script = Path(temp) / "safe.scr"
            script.write_text(
                "_.FILEDIA\n0\n_.CMDDIA\n0\n_.REGEN\n_.FILEDIA\n1\n_.CMDDIA\n1\n_.QUIT\n_N\n",
                encoding="utf-8",
            )
            cad_guard.validate_cad_script(script)


if __name__ == "__main__":
    unittest.main(verbosity=2)
