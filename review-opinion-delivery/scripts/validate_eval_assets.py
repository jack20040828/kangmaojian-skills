#!/usr/bin/env python3
"""Validate routing and regression evaluation assets without pretending to run a model router."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
ROUTING_PATH = SKILL_ROOT / "evals" / "routing-cases.json"
REGRESSION_PATH = SKILL_ROOT / "evals" / "regression-cases.json"
EXPECTED_ROUTING = {"invoke": 10, "building-review": 5, "documents": 3, "split": 4}
EXPECTED_COVERAGE = {
    "duplicate-source-numbering",
    "drawing-reference-conflict",
    "one-image-many-opinions",
    "many-sources-one-opinion",
    "empty-regulation",
    "missing-image",
    "order-change",
    "source-mutated",
    "qa-pending",
    "deterministic-type-correction",
    "ambiguous-type-block",
    "mandatory-suggested-preservation",
    "old-deletion-no-return",
    "no-regulation-no-backfill",
    "same-paragraph-fields",
    "automatic-section-numbering",
    "multiple-images-one-opinion",
    "no-process-trace",
    "compact-formal-evidence",
    "25-to-21-authoritative-mapping",
    "ambiguous-auto-mapping",
}


def load_array(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError(f"{path.name} must contain a non-empty JSON array")
    if not all(isinstance(row, dict) for row in data):
        raise ValueError(f"{path.name} entries must be objects")
    return data


def require_unique(rows: list[dict], field: str, label: str) -> None:
    values = [str(row.get(field, "")).strip() for row in rows]
    if not all(values) or len(values) != len(set(values)):
        raise ValueError(f"{label} {field} values must be non-empty and unique")


def main() -> int:
    routing = load_array(ROUTING_PATH)
    if len(routing) != 22:
        raise ValueError(f"Expected 22 routing cases, found {len(routing)}")
    required_routing_fields = {"id", "query", "expected", "reason"}
    for row in routing:
        if set(row) != required_routing_fields or not all(str(row[field]).strip() for field in required_routing_fields):
            raise ValueError(f"Invalid routing case: {row}")
    require_unique(routing, "id", "Routing")
    counts = Counter(str(row["expected"]) for row in routing)
    if dict(counts) != EXPECTED_ROUTING:
        raise ValueError(f"Routing distribution mismatch: {dict(counts)}")

    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    required_boundaries = [
        "Use only when the reviewer has already formed the opinions",
        "Do not use to inspect drawings for new issues",
        "If a request mixes new technical review with delivery work",
    ]
    missing = [text for text in required_boundaries if text not in skill_text]
    if missing:
        raise ValueError(f"SKILL.md is missing routing boundaries: {missing}")

    regression = load_array(REGRESSION_PATH)
    required_regression_fields = {"id", "scenario", "expected", "coverage"}
    allowed_results = {"pass", "fail", "manual-confirmation"}
    for row in regression:
        if set(row) != required_regression_fields or not all(str(row[field]).strip() for field in required_regression_fields):
            raise ValueError(f"Invalid regression case: {row}")
        if row["expected"] not in allowed_results:
            raise ValueError(f"Invalid regression expectation: {row}")
    require_unique(regression, "id", "Regression")
    coverage = {str(row["coverage"]) for row in regression}
    if coverage != EXPECTED_COVERAGE:
        raise ValueError(f"Regression coverage mismatch: {sorted(coverage)}")

    print("PASS: routing and regression evaluation assets are complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
