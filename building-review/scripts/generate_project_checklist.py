#!/usr/bin/env python3
"""Expand project facts and executable rules into v1.5/v1.6 professional checks."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from create_review_workspace import TEMPLATES, headers_for
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


def convert_v16_records(
    records: list[dict[str, str]],
    applicability_records: list[dict[str, str]],
    graphic_records: list[dict[str, str]],
) -> None:
    for record in records:
        record["completion_gate"] = record.pop("reviewer_gate", "")
        record.pop("independent_review_id", None)
    for record in [*applicability_records, *graphic_records]:
        record["completed_at"] = record.pop("reviewed_at", "")
        record.pop("reviewer_name", None)


def evidence_class(topic: str, calculation_required: bool) -> str:
    allowed = TOPIC_EVIDENCE_CLASSES.get(topic, set())
    if calculation_required and "numeric" in allowed:
        return "numeric"
    for candidate in ["relationship", "detail", "location", "performance", "graphic", "identity_text", "numeric", "absence_chain"]:
        if not allowed or candidate in allowed:
            return candidate
    return "relationship"


def expected_text(value) -> str:
    if isinstance(value, (dict, list, bool, int, float)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def build_rows(
    workspace: Path,
    catalog: dict,
    profile: dict,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    inventory = read_rows(workspace / "drawing_inventory.csv")
    report_type = str(profile.get("report_type", ""))
    records: list[dict[str, str]] = []
    applicability_records: list[dict[str, str]] = []
    graphic_records: list[dict[str, str]] = []
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
            applicability_ids: list[str] = []
            for condition in rule.get("applicability_conditions", []):
                decision_id = f"APP-{len(applicability_records) + 1:05d}"
                applicability_ids.append(decision_id)
                applicability_records.append(
                    {
                        "decision_id": decision_id,
                        "check_id": check_id,
                        "rule_id": rule["rule_id"],
                        "condition_id": condition["condition_id"],
                        "condition_description": condition["description"],
                        "expected_value": expected_text(condition.get("expected", "")),
                        "actual_value": "",
                        "result": "unknown",
                        "fact_ids": "",
                        "drawing_refs": refs,
                        "status": "unreviewed",
                        "reviewer_name": "",
                        "reviewed_at": "",
                        "notes": "",
                    }
                )
            graphic = rule.get("graphic_evidence_requirements", {})
            graphic_ids: list[str] = []
            for role in graphic.get("required_roles", []) if graphic.get("required") is True else []:
                chain_id = f"GFX-{len(graphic_records) + 1:05d}"
                graphic_ids.append(chain_id)
                graphic_records.append(
                    {
                        "chain_id": chain_id,
                        "check_id": check_id,
                        "evidence_role": role,
                        "source_file": "",
                        "page": "",
                        "drawing_ref": refs,
                        "location": "",
                        "graphic_element": "",
                        "observed_fact": "",
                        "interpretation": "",
                        "alternative_interpretation": "",
                        "elimination_basis": "",
                        "fact_ids": "",
                        "screenshot_path": "",
                        "source_quality": "",
                        "status": "unreviewed",
                        "reviewer_name": "",
                        "reviewed_at": "",
                        "notes": "",
                    }
                )
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
                    "graphic_claim_type": graphic.get("claim_type", "pending") if graphic.get("required") is True else "pending",
                    "graphic_chain_ids": ";".join(graphic_ids),
                    "graphic_gate_reason": "",
                    "applicability_decision_ids": ";".join(applicability_ids),
                    "independent_review_id": "",
                    "notes": "",
                }
            )
        drawing["review_status"] = "needs_review"
        drawing["review_check_ids"] = ";".join(linked)
        if not drawing.get("review_notes", "").strip():
            drawing["review_notes"] = "原子检查尚未全部关闭。"
    return records, inventory, applicability_records, graphic_records


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
    manifest_path = workspace / "review_manifest.json"
    if not profile_path.exists() or not inventory_path.exists() or not manifest_path.exists():
        print("FAIL: project_profile.json, drawing_inventory.csv, and review_manifest.json are required")
        return 1
    if target.exists() and read_rows(target) and not args.force:
        print(f"FAIL: refusing to replace non-empty checklist without --force: {target}")
        return 1
    try:
        catalog = load_catalog(args.catalog)
        profile = load_profile(profile_path)
        records, inventory, applicability_records, graphic_records = build_rows(workspace, catalog, profile)
    except Exception as error:
        print(f"FAIL: {error}")
        return 1
    if not records:
        print("FAIL: no rules were expanded; classify drawings and complete the project profile first")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema_version = str(manifest.get("schema_version", ""))
    if schema_version == "1.6":
        convert_v16_records(records, applicability_records, graphic_records)
    write_rows(target, headers_for(schema_version, "check_matrix.csv"), records)
    if target.resolve() == (workspace / "check_matrix.csv").resolve():
        write_rows(inventory_path, TEMPLATES["drawing_inventory.csv"], inventory)
        if schema_version in {"1.5", "1.6"}:
            write_rows(
                workspace / "applicability_decisions.csv",
                headers_for(schema_version, "applicability_decisions.csv"),
                applicability_records,
            )
            write_rows(
                workspace / "graphic_evidence_chain.csv",
                headers_for(schema_version, "graphic_evidence_chain.csv"),
                graphic_records,
            )
            if schema_version == "1.5":
                write_rows(
                    workspace / "independent_review_log.csv",
                    TEMPLATES["independent_review_log.csv"],
                    [],
                )
    print(
        f"PASS: generated {len(records)} unreviewed atomic checks, "
        f"{len(applicability_records)} applicability decisions, and "
        f"{len(graphic_records)} graphic evidence roles at {target}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
