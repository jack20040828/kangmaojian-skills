#!/usr/bin/env python3
"""Expand v1.4 project facts and executable rules into unreviewed atomic checks."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from create_review_workspace import TEMPLATES
from review_rules import DEFAULT_RULE_CATALOG, applicable_rules, load_catalog, load_profile, trigger_summary
from validate_review_package import TOPIC_EVIDENCE_CLASSES


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fields: list[str], records: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def evidence_class(topic: str, calculation_required: bool) -> str:
    allowed = TOPIC_EVIDENCE_CLASSES.get(topic, set())
    if calculation_required and "numeric" in allowed:
        return "numeric"
    for candidate in ["relationship", "detail", "location", "performance", "graphic", "identity_text", "numeric", "absence_chain"]:
        if not allowed or candidate in allowed:
            return candidate
    return "relationship"


def build_rows(workspace: Path, catalog: dict, profile: dict) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    inventory = read_rows(workspace / "drawing_inventory.csv")
    report_type = str(profile.get("report_type", ""))
    records: list[dict[str, str]] = []
    for drawing_index, drawing in enumerate(inventory, start=1):
        family = drawing.get("review_family", "").strip()
        drawing_no = drawing.get("drawing_no", "").strip()
        drawing_name = drawing.get("drawing_name", "").strip()
        refs = " ".join(value for value in [drawing_no, drawing_name] if value)
        linked: list[str] = []
        for rule, trigger_state in applicable_rules(catalog, profile, family, report_type):
            check_id = f"CHK-{len(records) + 1:04d}"
            linked.append(check_id)
            basis = rule.get("basis", {})
            records.append(
                {
                    "check_id": check_id,
                    "specialty": rule["specialty"],
                    "review_item_id": rule["rule_id"],
                    "rule_id": rule["rule_id"],
                    "atomic_check_id": f"{rule['rule_id']}@S{drawing_index:03d}",
                    "coverage_topic": rule["coverage_topic"],
                    "evidence_class": evidence_class(rule["coverage_topic"], bool(rule["calculation_required"])),
                    "decision_state": "unreviewed",
                    "discovery_track": "technical_compliance" if rule["authority_mode"] == "normative" else "design_depth",
                    "source_review_item": rule["comparison_method"],
                    "applicability": "适用" if trigger_state == "active" else "需判断",
                    "applicability_basis": trigger_summary(rule, profile),
                    "required_fact": "；".join(rule["required_facts"]),
                    "actual_fact": "",
                    "fact_ids": "",
                    "drawing_refs": refs,
                    "standard_source": basis.get("relative_path", ""),
                    "standard_article": basis.get("article", ""),
                    "standard_requirement": basis.get("requirement", ""),
                    "comparison_method": rule["comparison_method"],
                    "comparison_record": "",
                    "calculation_record": "",
                    "conclusion": "需核验",
                    "forms_issue": "no",
                    "issue_id": "",
                    "not_forming_reason": "尚未判断是否形成意见。",
                    "open_reason": "规则触发条件尚未确认。" if trigger_state == "uncertain" else "尚未实施本项审查。",
                    "reviewer_gate": "",
                    "notes": "",
                }
            )
        drawing["review_status"] = "needs_review"
        drawing["review_check_ids"] = ";".join(linked)
        if not drawing.get("review_notes", "").strip():
            drawing["review_notes"] = "原子检查尚未全部关闭。"
    return records, inventory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_workspace", type=Path)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_RULE_CATALOG)
    parser.add_argument("--output", type=Path, help="default: project check_matrix.csv")
    parser.add_argument("--force", action="store_true", help="replace a non-empty output explicitly")
    args = parser.parse_args()
    workspace = args.project_workspace.resolve()
    profile_path = workspace / "project_profile.json"
    inventory_path = workspace / "drawing_inventory.csv"
    target = args.output or workspace / "check_matrix.csv"
    if not profile_path.exists() or not inventory_path.exists():
        print("FAIL: project_profile.json and drawing_inventory.csv are required")
        return 1
    if target.exists() and read_rows(target) and not args.force:
        print(f"FAIL: refusing to replace non-empty checklist without --force: {target}")
        return 1
    try:
        catalog = load_catalog(args.catalog)
        profile = load_profile(profile_path)
        records, inventory = build_rows(workspace, catalog, profile)
    except Exception as error:
        print(f"FAIL: {error}")
        return 1
    if not records:
        print("FAIL: no rules were expanded; classify drawings and complete the project profile first")
        return 1
    write_rows(target, TEMPLATES["check_matrix.csv"], records)
    if target.resolve() == (workspace / "check_matrix.csv").resolve():
        write_rows(inventory_path, TEMPLATES["drawing_inventory.csv"], inventory)
    print(f"PASS: generated {len(records)} unreviewed atomic checks at {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
