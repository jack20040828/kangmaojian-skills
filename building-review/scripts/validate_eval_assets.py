#!/usr/bin/env python3
"""Validate routing and regression asset structure without faking model routing."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

EXPECTED_COUNTS = {
    "invoke_building_review": 8,
    "route_review_opinion_delivery": 5,
    "route_documents": 3,
    "out_of_scope": 4,
    "split_request": 4,
}
REQUIRED_DESCRIPTION_TERMS = [
    "review-opinion-delivery",
    "generic Word editing",
    "administrative submission review",
    "structural",
    "plumbing",
    "electrical",
    "HVAC",
    "Split mixed",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def frontmatter_description(skill_path: Path) -> str:
    text = skill_path.read_text(encoding="utf-8-sig")
    match = re.match(r"^---\s*\n(.*?)\n---", text, flags=re.DOTALL)
    if not match:
        return ""
    for line in match.group(1).splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", nargs="?", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    skill_dir = args.skill_dir.resolve()
    errors: list[str] = []
    routing_path = skill_dir / "evals" / "routing-cases.json"
    regression_path = skill_dir / "evals" / "regression-cases.json"
    try:
        routing = load_json(routing_path)
    except Exception as error:
        routing = []
        errors.append(f"invalid routing-cases.json: {error}")
    if not isinstance(routing, list):
        errors.append("routing-cases.json must contain a list")
        routing = []
    ids: list[str] = []
    counts: Counter[str] = Counter()
    for index, case in enumerate(routing):
        if not isinstance(case, dict) or set(case) != {"id", "query", "expected", "reason"}:
            errors.append(f"routing case {index + 1} has invalid fields")
            continue
        if not all(isinstance(case[field], str) and case[field].strip() for field in case):
            errors.append(f"routing case {index + 1} has an empty value")
        ids.append(case["id"])
        counts[case["expected"]] += 1
    if len(ids) != len(set(ids)):
        errors.append("routing case IDs are not unique")
    if dict(counts) != EXPECTED_COUNTS:
        errors.append(f"routing category counts are {dict(counts)}, expected {EXPECTED_COUNTS}")
    description = frontmatter_description(skill_dir / "SKILL.md")
    for term in REQUIRED_DESCRIPTION_TERMS:
        if term not in description:
            errors.append(f"frontmatter description is missing boundary term: {term}")
    try:
        regression = load_json(regression_path)
        if not isinstance(regression, list) or not regression:
            errors.append("regression-cases.json must contain a non-empty list")
    except Exception as error:
        errors.append(f"invalid regression-cases.json: {error}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: {len(routing)} routing cases and regression metadata are structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
