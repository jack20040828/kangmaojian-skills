#!/usr/bin/env python3
"""Run AutoCAD/Core Console without leaking dialog settings into the user profile."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

AUTOCAD_REGISTRY_ROOT = r"Software\Autodesk\AutoCAD"
DIALOG_VALUE_NAMES = ("FileDialog", "CommandDialogs")
TIMEOUT_EXIT_CODE = 124


class UnsafeCadScriptError(ValueError):
    """Raised when a CAD script can leave dialog variables disabled."""


@dataclass(frozen=True)
class RegistryValueSnapshot:
    key_path: str
    name: str
    existed: bool
    value: Any = None
    value_type: int | None = None


def _normalize_command(line: str) -> str:
    return line.strip().upper().lstrip("._")


def _read_script_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "mbcs", "cp936", "latin-1"):
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    raise UnsafeCadScriptError(f"cannot decode CAD script: {path}")


def validate_cad_script(path: Path) -> None:
    """Reject scripts that set FILEDIA/CMDDIA to 0 without restoring before exit."""
    if not path.is_file():
        raise UnsafeCadScriptError(f"CAD script not found: {path}")

    lines = _read_script_text(path).splitlines()
    state: dict[str, int | None] = {"FILEDIA": None, "CMDDIA": None}
    disabled: set[str] = set()
    assignments: dict[int, tuple[str, int]] = {}

    for index, raw_line in enumerate(lines):
        command = _normalize_command(raw_line)
        if command not in state:
            continue
        value_index = index + 1
        while value_index < len(lines) and not lines[value_index].strip():
            value_index += 1
        if value_index >= len(lines):
            raise UnsafeCadScriptError(f"{path.name}: {command} has no value")
        value = lines[value_index].strip().strip('"')
        if value in {"0", "1"}:
            assignments[index] = (command, int(value))

    errors: list[str] = []
    for index, raw_line in enumerate(lines):
        if index in assignments:
            name, value = assignments[index]
            state[name] = value
            if value == 0:
                disabled.add(name)
        if _normalize_command(raw_line) == "QUIT":
            leaking = sorted(name for name in disabled if state[name] != 1)
            if leaking:
                errors.append(f"QUIT leaves {', '.join(leaking)} disabled")

    leaking_at_end = sorted(name for name in disabled if state[name] != 1)
    if leaking_at_end:
        errors.append(f"script end leaves {', '.join(leaking_at_end)} disabled")
    if errors:
        raise UnsafeCadScriptError(f"{path.name}: " + "; ".join(dict.fromkeys(errors)))


def _script_argument(command: Sequence[str]) -> Path | None:
    for index, value in enumerate(command[:-1]):
        if value.lower() in {"/s", "-s"}:
            return Path(command[index + 1])
    return None


def _preflight_command(command: Sequence[str]) -> None:
    if not command:
        raise ValueError("missing CAD command after --")
    script = _script_argument(command)
    if script is not None:
        validate_cad_script(script)


def _winreg_module():
    if os.name != "nt":
        raise RuntimeError("CAD dialog-state protection is supported only on Windows")
    import winreg

    return winreg


def _subkey_names(winreg, key) -> list[str]:
    count = winreg.QueryInfoKey(key)[0]
    return [winreg.EnumKey(key, index) for index in range(count)]


def _configuration_key_paths(winreg) -> list[str]:
    try:
        root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOCAD_REGISTRY_ROOT, 0, winreg.KEY_READ)
    except FileNotFoundError:
        return []

    paths: list[str] = []
    with root:
        releases = _subkey_names(winreg, root)
    for release in releases:
        release_path = f"{AUTOCAD_REGISTRY_ROOT}\\{release}"
        try:
            release_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, release_path, 0, winreg.KEY_READ)
        except OSError:
            continue
        with release_key:
            products = _subkey_names(winreg, release_key)
        for product in products:
            candidate = f"{release_path}\\{product}\\FixedProfile\\General Configuration"
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, candidate, 0, winreg.KEY_READ)
            except OSError:
                continue
            key.Close()
            paths.append(candidate)
    return paths


def _snapshot_dialog_settings() -> list[RegistryValueSnapshot]:
    winreg = _winreg_module()
    snapshots: list[RegistryValueSnapshot] = []
    for key_path in _configuration_key_paths(winreg):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            for name in DIALOG_VALUE_NAMES:
                try:
                    value, value_type = winreg.QueryValueEx(key, name)
                except FileNotFoundError:
                    snapshots.append(RegistryValueSnapshot(key_path, name, False))
                else:
                    snapshots.append(RegistryValueSnapshot(key_path, name, True, value, value_type))
    if not snapshots:
        raise RuntimeError("no AutoCAD dialog configuration keys found; refusing to run unguarded")
    return snapshots


def _restore_dialog_settings(snapshots: Sequence[RegistryValueSnapshot]) -> None:
    winreg = _winreg_module()
    errors: list[str] = []
    for snapshot in snapshots:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                snapshot.key_path,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                if snapshot.existed:
                    winreg.SetValueEx(key, snapshot.name, 0, snapshot.value_type, snapshot.value)
                else:
                    try:
                        winreg.DeleteValue(key, snapshot.name)
                    except FileNotFoundError:
                        pass
        except OSError as exc:
            errors.append(f"{snapshot.key_path}\\{snapshot.name}: {exc}")
    if errors:
        raise RuntimeError("failed to restore AutoCAD dialog settings: " + " | ".join(errors))


def _terminate_process_tree(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        process.kill()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _run_command(command: Sequence[str], timeout: float | None) -> int:
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    process = subprocess.Popen(list(command), creationflags=creationflags)
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process)
        print(f"CAD command timed out after {timeout:g} seconds", file=sys.stderr)
        return TIMEOUT_EXIT_CODE
    except BaseException:
        _terminate_process_tree(process)
        raise


def run_guarded(command: Sequence[str], timeout: float | None = None) -> int:
    _preflight_command(command)
    snapshots = _snapshot_dialog_settings()
    try:
        return _run_command(command, timeout)
    finally:
        _restore_dialog_settings(snapshots)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run AutoCAD/Core Console and restore per-user file-dialog settings afterward."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=0,
        help="Seconds before terminating the CAD process tree; 0 disables timeout.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="CAD command and arguments after --")
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("missing CAD command after --")
    if args.timeout < 0:
        parser.error("--timeout must be zero or positive")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run_guarded(args.command, args.timeout or None)
    except UnsafeCadScriptError as exc:
        print(f"UNSAFE CAD SCRIPT: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("CAD command interrupted; dialog settings restored", file=sys.stderr)
        return 130
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"CAD guard failed: {exc}", file=sys.stderr)
        return 70


if __name__ == "__main__":
    raise SystemExit(main())
