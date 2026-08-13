#!/usr/bin/env python3
"""Deterministic tests for cross-sheet fact comparison."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_cross_sheet_consistency import compare, normalize_value  # noqa: E402


def row(fact_id: str, drawing_no: str, value: str, unit: str = "m") -> dict[str, str]:
    return {
        "fact_id": fact_id,
        "drawing_no": drawing_no,
        "drawing_name": drawing_no,
        "location": "",
        "fact_type": "建筑高度",
        "raw_text_or_measure": value,
        "value": value,
        "unit": unit,
    }


def main() -> int:
    assert normalize_value("12.00", "m") == normalize_value("12", " m ")
    consistent = compare([row("F1", "建施-01", "12"), row("F2", "建施-02", "12.00")], set())
    assert consistent["compared_group_count"] == 1
    assert consistent["conflict_count"] == 0
    conflict = compare([row("F1", "建施-01", "12"), row("F2", "建施-02", "12.1")], set())
    assert conflict["conflict_count"] == 1
    single_sheet = compare([row("F1", "建施-01", "12"), row("F2", "建施-01", "12.1")], set())
    assert single_sheet["compared_group_count"] == 0
    print("PASS: 4 cross-sheet consistency cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
