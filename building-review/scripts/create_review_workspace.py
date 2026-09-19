#!/usr/bin/env python3
"""Create a versioned building-review workspace and its required ledgers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

DEFAULT_PROJECT_ROOT = Path(
    os.environ.get("BUILDING_REVIEW_PROJECT_ROOT", str(Path.cwd() / "building-review-projects"))
).expanduser()
SCHEMA_VERSION = "1.7"
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
RULE_CATALOG = SKILL_DIR / "generated" / "review-rules.json"

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
        "review_item_id",
        "rule_id",
        "atomic_check_id",
        "coverage_topic",
        "evidence_class",
        "decision_state",
        "discovery_track",
        "source_review_item",
        "applicability",
        "applicability_basis",
        "required_fact",
        "actual_fact",
        "fact_ids",
        "drawing_refs",
        "standard_source",
        "standard_article",
        "standard_requirement",
        "comparison_method",
        "comparison_record",
        "calculation_record",
        "conclusion",
        "forms_issue",
        "issue_id",
        "not_forming_reason",
        "open_reason",
        "reviewer_gate",
        "graphic_claim_type",
        "graphic_chain_ids",
        "graphic_gate_reason",
        "applicability_decision_ids",
        "independent_review_id",
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
        "evidence_chain_check",
        "independent_review_check",
        "gate_origin",
        "reviewer_confirmation",
        "reviewer_name",
        "reviewed_at",
        "result",
        "notes",
    ],
    "graphic_evidence_chain.csv": [
        "chain_id",
        "check_id",
        "evidence_role",
        "source_file",
        "page",
        "drawing_ref",
        "location",
        "graphic_element",
        "observed_fact",
        "interpretation",
        "alternative_interpretation",
        "elimination_basis",
        "fact_ids",
        "screenshot_path",
        "source_quality",
        "status",
        "reviewer_name",
        "reviewed_at",
        "notes",
    ],
    "applicability_decisions.csv": [
        "decision_id",
        "check_id",
        "rule_id",
        "condition_id",
        "condition_description",
        "expected_value",
        "actual_value",
        "result",
        "fact_ids",
        "drawing_refs",
        "status",
        "reviewer_name",
        "reviewed_at",
        "notes",
    ],
    "independent_review_log.csv": [
        "review_id",
        "check_id",
        "primary_reviewer",
        "primary_reviewer_type",
        "primary_decision",
        "primary_reviewed_at",
        "secondary_reviewer",
        "secondary_reviewer_type",
        "secondary_decision",
        "secondary_reviewed_at",
        "blind_input_scope",
        "agreement",
        "adjudicator",
        "adjudicator_type",
        "adjudicated_decision",
        "adjudicated_at",
        "status",
        "notes",
    ],
}

V15_LEDGER_NAMES = {
    "graphic_evidence_chain.csv",
    "applicability_decisions.csv",
    "independent_review_log.csv",
}

V16_LEDGER_NAMES = {
    "graphic_evidence_chain.csv",
    "applicability_decisions.csv",
}

V16_TEMPLATES = {
    "check_matrix.csv": [
        field for field in TEMPLATES["check_matrix.csv"]
        if field not in {"reviewer_gate", "independent_review_id"}
    ] + ["completion_gate"],
    "validation_log.csv": [
        field for field in TEMPLATES["validation_log.csv"]
        if field not in {
            "independent_review_check", "reviewer_confirmation", "reviewer_name", "reviewed_at"
        }
    ] + ["stage_completion", "completed_at"],
    "graphic_evidence_chain.csv": [
        field for field in TEMPLATES["graphic_evidence_chain.csv"]
        if field not in {"reviewer_name", "reviewed_at"}
    ] + ["completed_at"],
    "applicability_decisions.csv": [
        field for field in TEMPLATES["applicability_decisions.csv"]
        if field not in {"reviewer_name", "reviewed_at"}
    ] + ["completed_at"],
}


def headers_for(schema_version: str, filename: str) -> list[str]:
    if schema_version in {"1.6", "1.7"} and filename in V16_TEMPLATES:
        return V16_TEMPLATES[filename]
    return TEMPLATES[filename]

PROFILE_FACT_KEYS = [
    "location_province", "location_city", "building_use", "industrial_building",
    "overnight_stay", "gross_floor_area_m2", "building_height_m", "floors_above",
    "floors_below", "fire_hazard_class", "fire_resistance_rating", "occupant_load",
    "sprinkler", "basement", "elevator", "accessible_requirement", "roof_accessible",
    "wet_rooms", "parking", "photovoltaic_or_solar", "food_service",
    "dormitory_or_hotel", "school", "office", "children_activity",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def initial_profile(report_type: str, schema_version: str) -> dict:
    if schema_version in {"1.6", "1.7"}:
        return {
            "schema_version": "1.1",
            "review_stage": "ai_initial",
            "ai_review_completed": False,
            "completed_at": "",
            "report_type": report_type,
            "facts": {
                key: {"status": "unknown", "value": "", "fact_ids": [], "notes": ""}
                for key in PROFILE_FACT_KEYS
            },
            "route_completion": {"status": "not_started", "completed_at": "", "notes": ""},
            "discovery_tracks": {
                "technical_compliance": {"status": "not_started", "notes": ""},
                "design_depth": {"status": "not_started", "notes": ""},
                "optimization": {"status": "not_started", "notes": ""},
            },
        }
    return {
        "schema_version": "1.0",
        "confirmed": False,
        "confirmed_by": "",
        "confirmed_at": "",
        "report_type": report_type,
        "facts": {
            key: {"status": "unknown", "value": "", "fact_ids": [], "notes": ""}
            for key in PROFILE_FACT_KEYS
        },
        "route_confirmation": {"confirmed": False, "confirmed_by": "", "confirmed_at": "", "notes": ""},
        "discovery_tracks": {
            "technical_compliance": {"status": "not_started", "notes": ""},
            "design_depth": {"status": "not_started", "notes": ""},
            "optimization": {"status": "not_started", "notes": ""},
        },
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
    parser.add_argument("--schema-version", choices=["1.4", "1.5", "1.6", "1.7"], default=SCHEMA_VERSION)
    args = parser.parse_args()

    if args.root.resolve() == DEFAULT_PROJECT_ROOT.resolve():
        print(
            "WARN: using the default project root. For an existing project, pass "
            "--root <项目>\\03_审图过程 explicitly.",
            file=sys.stderr,
        )

    folder = args.root / f"{date.today().isoformat()}-{slugify(args.project_name)}"
    existing_manifest = folder / "review_manifest.json"
    if existing_manifest.exists() and json.loads(existing_manifest.read_text(encoding="utf-8")).get("schema_version") != args.schema_version:
        parser.error("existing workspace uses another schema; do not migrate it in place")
    folder.mkdir(parents=True, exist_ok=True)
    for name in ["source", "screenshots", "output"]:
        (folder / name).mkdir(exist_ok=True)
    for filename, headers in TEMPLATES.items():
        allowed_ledgers = V15_LEDGER_NAMES if args.schema_version == "1.5" else (
            V16_LEDGER_NAMES if args.schema_version in {"1.6", "1.7"} else set()
        )
        if filename in V15_LEDGER_NAMES and filename not in allowed_ledgers:
            continue
        path = folder / filename
        if not path.exists():
            write_csv(path, headers_for(args.schema_version, filename))

    profile_path = folder / "project_profile.json"
    if not profile_path.exists():
        profile_path.write_text(
            json.dumps(initial_profile(args.report_type, args.schema_version), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    manifest_path = folder / "review_manifest.json"
    if not manifest_path.exists():
        manifest = {
            "schema_version": args.schema_version,
            "review_stage": "ai_initial" if args.schema_version in {"1.6", "1.7"} else "",
            "project_name": args.project_name,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "report_type": args.report_type,
            "source_integrity": [],
            "knowledge_snapshot": {
                "required_layers": ["A", "B", "C", "D"] if args.schema_version in {"1.6", "1.7"} else [],
                "layers": {},
            },
            "rule_catalog_snapshot": {
                "path": str(RULE_CATALOG.resolve()) if RULE_CATALOG.exists() else "",
                "sha256": sha256_file(RULE_CATALOG) if RULE_CATALOG.exists() else "",
            },
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.schema_version == "1.7":
        from judgment_evidence import LEDGER
        judgment_path = folder / LEDGER
        if not judgment_path.exists():
            judgment_path.write_text(json.dumps({"schema_version": "1.0", "checks": [], "issue_screening": []}), encoding="utf-8")
    print(folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
