#!/usr/bin/env python3
"""Create a versioned building-review workspace and its required ledgers."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

DEFAULT_PROJECT_ROOT = Path(
    os.environ.get("BUILDING_REVIEW_PROJECT_ROOT", str(Path.cwd() / "building-review-projects"))
).expanduser()
SCHEMA_VERSION = "1.2"

TEMPLATES = {
    "drawing_inventory.csv": [
        "source_file",
        "page",
        "sheet_no",
        "drawing_no",
        "drawing_name",
        "discipline",
        "content_type",
        "scale",
        "title_block_status",
        "review_family",
        "review_status",
        "review_check_ids",
        "review_notes",
        "notes",
    ],
    "fact_ledger.csv": [
        "fact_id",
        "source_file",
        "page",
        "drawing_no",
        "drawing_name",
        "location",
        "fact_type",
        "raw_text_or_measure",
        "value",
        "unit",
        "confidence",
        "needs_verification",
        "notes",
    ],
    "check_matrix.csv": [
        "check_id",
        "specialty",
        "source_review_item",
        "applicability",
        "required_fact",
        "actual_fact",
        "fact_ids",
        "drawing_refs",
        "standard_source",
        "standard_article",
        "standard_requirement",
        "conclusion",
        "forms_issue",
        "issue_id",
        "not_forming_reason",
        "notes",
    ],
    "issue_candidates.csv": [
        "issue_id",
        "status",
        "display_order",
        "report_section",
        "specialty",
        "check_id",
        "fact_ids",
        "drawing_refs",
        "problem",
        "citation_mode",
        "standard_source",
        "standard_display_name",
        "standard_article",
        "standard_requirement",
        "citation_none_reason",
        "judgment",
        "case_refs",
        "needs_screenshot",
        "screenshot_path",
        "screenshot_location",
        "screenshot_strategy",
        "screenshot_reason",
        "screenshot_count",
        "evidence_point",
        "red_box_target",
        "context_required",
        "screenshot_quality",
        "opinion_type",
        "validation_status",
        "notes",
    ],
    "validation_log.csv": [
        "issue_id",
        "fact_check",
        "standard_check",
        "specialty_check",
        "case_check",
        "screenshot_check",
        "professional_filter_check",
        "screenshot_strategy_check",
        "red_box_precision_check",
        "graphical_interpretation_check",
        "opinion_wording_check",
        "layout_check",
        "opinion_type_check",
        "result",
        "notes",
    ],
}


def slugify(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[\\/:*?\"<>|]+", "-", value)
    value = re.sub(r"\s+", "-", value)
    return value or "未命名项目"


def write_csv(path: Path, headers: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle).writerow(headers)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_name")
    parser.add_argument("--root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--report-type", choices=["single", "site"], default="single")
    args = parser.parse_args()

    if args.root.resolve() == DEFAULT_PROJECT_ROOT.resolve():
        print(
            "WARN: using the default project root. For an existing project, pass "
            "--root <项目>\\03_审图过程 explicitly.",
            file=sys.stderr,
        )

    folder = args.root / f"{date.today().isoformat()}-{slugify(args.project_name)}"
    folder.mkdir(parents=True, exist_ok=True)
    for name in ["source", "screenshots", "output"]:
        (folder / name).mkdir(exist_ok=True)
    for filename, headers in TEMPLATES.items():
        path = folder / filename
        if not path.exists():
            write_csv(path, headers)

    manifest_path = folder / "review_manifest.json"
    if not manifest_path.exists():
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "project_name": args.project_name,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "report_type": args.report_type,
            "source_integrity": [],
            "knowledge_snapshot": {},
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
