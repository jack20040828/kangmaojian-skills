#!/usr/bin/env python3
"""Compare repeated facts across drawing sheets without inventing missing values."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


def normalize_value(value: str, unit: str) -> str:
    value = re.sub(r"\s+", "", value or "").replace(",", "")
    unit = re.sub(r"\s+", "", unit or "").casefold()
    try:
        number = Decimal(value)
    except InvalidOperation:
        return f"{value.casefold()}|{unit}"
    return f"{number.normalize()}|{unit}"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def compare(rows: list[dict[str, str]], selected_types: set[str]) -> dict[str, object]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        fact_type = (row.get("fact_type") or "").strip()
        if not fact_type or (selected_types and fact_type not in selected_types):
            continue
        value = (row.get("value") or row.get("raw_text_or_measure") or "").strip()
        if not value:
            continue
        groups[fact_type].append(
            {
                "fact_id": (row.get("fact_id") or "").strip(),
                "drawing_no": (row.get("drawing_no") or "").strip(),
                "drawing_name": (row.get("drawing_name") or "").strip(),
                "location": (row.get("location") or "").strip(),
                "value": value,
                "unit": (row.get("unit") or "").strip(),
                "normalized": normalize_value(value, row.get("unit") or ""),
            }
        )

    compared: list[dict[str, object]] = []
    conflicts: list[dict[str, object]] = []
    for fact_type, facts in sorted(groups.items()):
        sheet_refs = {(item["drawing_no"], item["drawing_name"]) for item in facts}
        if len(sheet_refs) < 2:
            continue
        distinct = sorted({item["normalized"] for item in facts})
        record = {
            "fact_type": fact_type,
            "status": "consistent" if len(distinct) == 1 else "conflict",
            "distinct_value_count": len(distinct),
            "facts": facts,
        }
        compared.append(record)
        if len(distinct) > 1:
            conflicts.append(record)
    return {
        "schema_version": "1.0",
        "compared_group_count": len(compared),
        "conflict_count": len(conflicts),
        "groups": compared,
        "conflicts": conflicts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_workspace", type=Path)
    parser.add_argument(
        "--fact-type",
        action="append",
        default=[],
        help="Exact fact_type to compare; repeat as needed. Without it, compare every repeated type.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    ledger = args.project_workspace.resolve() / "fact_ledger.csv"
    if not ledger.exists():
        print(f"ERROR: fact ledger not found: {ledger}")
        return 2
    result = compare(load_rows(ledger), set(args.fact_type))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if result["conflict_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
