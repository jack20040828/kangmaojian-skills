#!/usr/bin/env python3
"""Correct deterministic opinion-type errors in a delivery manifest and record the edit."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

from opinion_types import classify, with_original_label


EDIT_HEADERS = ["item_id", "item_no", "field", "before", "after", "reason", "result"]


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", delete=False, dir=path.parent)
    try:
        with handle:
            handle.write(text)
        os.replace(handle.name, path)
    except Exception:
        Path(handle.name).unlink(missing_ok=True)
        raise


def append_edits(path: Path, rows: list[dict[str, object]]) -> None:
    existing: list[dict[str, str]] = []
    if path.exists() and path.stat().st_size:
        with path.open(encoding="utf-8", newline="") as handle:
            existing = list(csv.DictReader(handle))
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", delete=False, dir=path.parent)
    try:
        with handle:
            writer = csv.DictWriter(handle, fieldnames=EDIT_HEADERS)
            writer.writeheader()
            writer.writerows(existing)
            writer.writerows(rows)
        os.replace(handle.name, path)
    except Exception:
        Path(handle.name).unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--check", action="store_true", help="Report required corrections without writing files")
    args = parser.parse_args()
    root = args.workspace.resolve()
    manifest_path = root / "delivery_manifest.json"
    edit_log = root / "edit_log.csv"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    corrections: list[dict[str, object]] = []
    invalid: list[str] = []

    for item in manifest.get("items", []):
        before = str(item.get("opinion_type", ""))
        status, normalized = classify(before)
        label = item.get("item_id") or item.get("item_no")
        if status == "invalid":
            invalid.append(f"{label}: {before!r}")
            continue
        after = with_original_label(before, normalized)
        if after != before:
            corrections.append(
                {
                    "item_id": item.get("item_id", ""),
                    "item_no": item.get("item_no", ""),
                    "field": "opinion_type",
                    "before": before,
                    "after": after,
                    "reason": "确定性错字、标点或已知意见类型别名纠正",
                    "result": "已修改",
                }
            )
            item["opinion_type"] = after
            if item.get("approved_content", {}).get("opinion_type") == before:
                item["approved_content"]["opinion_type"] = after
            note = str(item.get("editorial_change_note", "")).strip()
            correction_note = f"意见类型由“{before}”纠正为“{after}”"
            item["editorial_change_note"] = f"{note}；{correction_note}" if note else correction_note

    if args.check:
        for row in corrections:
            print(f"NEEDS_CORRECTION: {row['item_id'] or row['item_no']}: {row['before']} -> {row['after']}")
        if invalid:
            for value in invalid:
                print(f"FAIL: ambiguous or invalid opinion type requires reviewer confirmation: {value}")
            return 1
        print(f"PASS: {len(corrections)} deterministic opinion-type correction(s) identified")
        return 0
    if corrections:
        atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        append_edits(edit_log, corrections)
    if invalid:
        for value in invalid:
            print(f"FAIL: ambiguous or invalid opinion type requires reviewer confirmation: {value}")
        return 1
    print(f"PASS: normalized {len(corrections)} opinion type(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
