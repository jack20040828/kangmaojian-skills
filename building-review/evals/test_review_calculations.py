#!/usr/bin/env python3
"""Regression fixtures for deterministic review calculations."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "review_calculations.py"


def run(args: list[str], expected: int = 0) -> dict:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run([sys.executable, str(SCRIPT), *args], text=True, encoding="utf-8", capture_output=True, env=env)
    if result.returncode != expected:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(result.stdout) if expected == 0 else {}


def main() -> int:
    if run(["compare-minimum", "--name", "门净宽", "--actual", "0.9", "--minimum", "0.8", "--unit", "m"])["result"] != "compliant":
        raise AssertionError("minimum comparison failed")
    width = run(["egress-width", "--occupants", "250", "--width-per-100", "0.65", "--provided", "1.5"])
    if width["required_width_m"] != "1.625" or width["result"] != "noncompliant":
        raise AssertionError("egress width calculation failed")
    if run(["slope", "--rise-mm", "150", "--run-mm", "1800", "--max-ratio", "12"])["result"] != "compliant":
        raise AssertionError("slope comparison failed")
    if run(["count-range", "--name", "梯段踏步", "--actual", "19", "--minimum", "2", "--maximum", "18"])["result"] != "noncompliant":
        raise AssertionError("count range comparison failed")
    run(["egress-width", "--occupants", "", "--width-per-100", "0.65", "--provided", "1.5"], expected=2)
    print("PASS: 5 deterministic calculation fixtures completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
