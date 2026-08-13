#!/usr/bin/env python3
"""Build and validate the executable v1.4 review-rule catalog."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from validate_review_package import FAMILY_REQUIRED_TOPICS, FUNCTION_TRIGGER_TOPICS

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_SOURCE = SKILL_DIR / "references" / "review-rules-core.json"
DEFAULT_OUTPUT = SKILL_DIR / "generated" / "review-rules.json"
DEFAULT_KNOWLEDGE_INDEX = SKILL_DIR / "generated" / "knowledge-index.json"

FUNCTION_TOPIC_FAMILIES = {
    "dormitory_refuse": ["平面图"],
    "dormitory_acoustics": ["平面图", "材料做法表"],
    "accessible_room": ["平面图"],
    "accessible_room_detail": ["其他大样"],
    "site_assembly_space": ["总平面图"],
    "food_wet_room_vertical": ["平面图", "剖面图"],
    "accessible_elevator": ["平面图", "其他大样"],
}
FUNCTION_TOPIC_TRIGGERS = {
    "dormitory_refuse": {"all": [{"field": "dormitory_or_hotel", "values": [True, "是", "true"]}]},
    "dormitory_acoustics": {"all": [{"field": "dormitory_or_hotel", "values": [True, "是", "true"]}]},
    "accessible_room": {"all": [{"field": "dormitory_or_hotel", "values": [True, "是", "true"]}]},
    "accessible_room_detail": {"all": [{"field": "dormitory_or_hotel", "values": [True, "是", "true"]}]},
    "site_assembly_space": {"all": [{"field": "dormitory_or_hotel", "values": [True, "是", "true"]}]},
    "food_wet_room_vertical": {"all": [{"field": "food_service", "values": [True, "是", "true"]}]},
    "accessible_elevator": {
        "all": [
            {"field": "accessible_requirement", "values": [True, "是", "required", "true"]},
            {"field": "elevator", "values": [True, "是", "true"]},
        ]
    },
}


def coverage_shells() -> list[dict]:
    families_by_topic: dict[str, set[str]] = defaultdict(set)
    for family, topics in FAMILY_REQUIRED_TOPICS.items():
        for topic in topics:
            families_by_topic[topic].add(family)
    for _terms, report_topics in FUNCTION_TRIGGER_TOPICS:
        for topics in report_topics.values():
            for topic in topics:
                families_by_topic[topic].update(FUNCTION_TOPIC_FAMILIES.get(topic, []))
    rules = []
    for topic, families in sorted(families_by_topic.items()):
        rules.append(
            {
                "rule_id": f"DEPTH-COVERAGE-{topic.upper().replace('_', '-')}",
                "status": "active",
                "authority_mode": "design_depth",
                "specialty": "001建筑设计文件编制深度专项",
                "coverage_topic": topic,
                "review_families": sorted(families),
                "report_types": ["single", "site"],
                "trigger": FUNCTION_TOPIC_TRIGGERS.get(topic, {"always": True}),
                "required_facts": [f"本张图纸与 {topic} 相关的尺寸、数量、位置、关系、性能或明确不适用事实"],
                "comparison_method": "核对图纸表达是否完整、内部一致、与相关视图及索引闭合；不得以图纸存在代替实质核对。",
                "calculation_required": False,
                "risk_level": "medium",
                "basis": {},
            }
        )
    return rules


def validate_rule(rule: dict, seen: set[str]) -> list[str]:
    errors: list[str] = []
    required = {
        "rule_id", "status", "authority_mode", "specialty", "coverage_topic",
        "review_families", "report_types", "trigger", "required_facts",
        "comparison_method", "calculation_required", "risk_level", "basis",
    }
    missing = sorted(required - set(rule))
    if missing:
        errors.append(f"{rule.get('rule_id', '[missing]')}: missing fields: {', '.join(missing)}")
        return errors
    rule_id = str(rule["rule_id"]).strip()
    if not rule_id or rule_id in seen:
        errors.append(f"duplicate or blank rule_id: {rule_id}")
    seen.add(rule_id)
    if rule["status"] != "active":
        errors.append(f"{rule_id}: only active source rules are allowed")
    if rule["authority_mode"] not in {"normative", "design_depth"}:
        errors.append(f"{rule_id}: invalid authority_mode")
    if rule["risk_level"] not in {"high", "medium", "normal"}:
        errors.append(f"{rule_id}: invalid risk_level")
    if not rule["review_families"] or not rule["report_types"] or not rule["required_facts"]:
        errors.append(f"{rule_id}: families, report types, and required facts must be non-empty")
    if rule["authority_mode"] == "normative":
        basis = rule["basis"]
        for field in ["source_role", "relative_path", "sha256", "display_name", "article", "requirement"]:
            if not str(basis.get(field, "")).strip():
                errors.append(f"{rule_id}: normative basis missing {field}")
        if basis.get("source_role") != "B_核心规范":
            errors.append(f"{rule_id}: normative rules must use B_核心规范")
    elif rule["basis"]:
        errors.append(f"{rule_id}: design-depth rule must not carry a normative basis")
    return errors


def build(source: Path, knowledge_index: Path) -> dict:
    payload = json.loads(source.read_text(encoding="utf-8"))
    index = json.loads(knowledge_index.read_text(encoding="utf-8"))
    index_entries = {item.get("relative_path", ""): item for item in index.get("files", [])}
    rules = coverage_shells() + list(payload.get("rules", []))
    seen: set[str] = set()
    errors = [error for rule in rules for error in validate_rule(rule, seen)]
    for rule in rules:
        if rule.get("authority_mode") != "normative":
            continue
        basis = rule.get("basis", {})
        path = basis.get("relative_path", "")
        entry = index_entries.get(path)
        if not entry:
            errors.append(f"{rule['rule_id']}: B-source path is absent from the knowledge index: {path}")
            continue
        if entry.get("role") != "B_核心规范":
            errors.append(f"{rule['rule_id']}: indexed source role is not B_核心规范")
        if entry.get("sha256") != basis.get("sha256"):
            errors.append(f"{rule['rule_id']}: B-source hash differs from the knowledge index")
    if errors:
        raise ValueError("\n".join(errors))
    return {
        "schema_version": "1.0",
        "catalog_version": payload.get("catalog_version", ""),
        "rule_count": len(rules),
        "rules": sorted(rules, key=lambda item: item["rule_id"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--knowledge-index", type=Path, default=DEFAULT_KNOWLEDGE_INDEX)
    parser.add_argument("--check", action="store_true", help="verify output is current without rewriting")
    args = parser.parse_args()
    try:
        payload = build(args.source, args.knowledge_index)
    except Exception as error:
        print(f"FAIL: {error}")
        return 1
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            print("FAIL: generated review-rule catalog is missing or stale")
            return 1
        print(f"PASS: {payload['rule_count']} executable review rules are current")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"PASS: wrote {payload['rule_count']} executable review rules to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
