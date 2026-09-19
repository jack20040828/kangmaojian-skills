#!/usr/bin/env python3
"""Validate the eight GB 55031-2022 civil-building rule additions."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS))

from review_rules import evaluate_trigger  # noqa: E402


EXPECTED_ARTICLES = {
    "CIVIL-4.3.3-GARAGE-EXIT-BUFFER": "第4.3.3条",
    "CIVIL-4.3.5-SITE-ROAD-SAFETY": "第4.3.5条",
    "CIVIL-4.5.1-EXHAUST-OUTLET-SEPARATION": "第4.5.1条",
    "CIVIL-5.3.5-STAIR-PLATFORM-WIDTH": "第5.3.5条",
    "CIVIL-5.3.11-CHILD-STAIR-WELL-GUARD": "第5.3.11条",
    "CIVIL-5.6.2-PUBLIC-TOILET-LAYOUT": "第5.6.2条",
    "CIVIL-6.5.4-WINDOW-SAFETY": "第6.5.4条",
    "CIVIL-6.8.5-DOOR-DEFORMATION-JOINT": "第6.8.5条",
}
SOURCE_PATH = "004民用建筑专项/B民用建筑核心规范/GB55031-2022民用建筑通用规范.pdf"
SOURCE_SHA256 = "53e5f7ccfb5641aa3c9dd94ccf7d34174a65e3c030874021ccc22df92cbd0e54"
NUMERIC_RULES = {
    "CIVIL-4.3.3-GARAGE-EXIT-BUFFER",
    "CIVIL-4.5.1-EXHAUST-OUTLET-SEPARATION",
    "CIVIL-5.3.5-STAIR-PLATFORM-WIDTH",
    "CIVIL-5.3.11-CHILD-STAIR-WELL-GUARD",
    "CIVIL-6.5.4-WINDOW-SAFETY",
}


def profile(*, industrial: bool, children: bool | None = None) -> dict:
    facts = {
        "industrial_building": {
            "status": "confirmed",
            "value": industrial,
            "fact_ids": ["F001"],
        }
    }
    if children is not None:
        facts["children_activity"] = {
            "status": "confirmed",
            "value": children,
            "fact_ids": ["F002"],
        }
    return {"facts": facts}


def main() -> int:
    catalog = json.loads((SKILL_DIR / "generated" / "review-rules.json").read_text(encoding="utf-8"))
    rules = catalog["rules"]
    rules_by_id = {rule["rule_id"]: rule for rule in rules}

    if catalog.get("catalog_version") != "2026-09-19-r3" or catalog.get("rule_count") != 162:
        raise AssertionError("CIVIL-01: catalog version or total count is incorrect")
    modes = Counter(rule["authority_mode"] for rule in rules)
    if modes != {"normative": 110, "design_depth": 52}:
        raise AssertionError(f"CIVIL-01: authority-mode counts are incorrect: {dict(modes)}")
    civil_rules = [rule for rule in rules if rule.get("specialty") == "004民用建筑专项"]
    if len(civil_rules) != 22:
        raise AssertionError("CIVIL-01: civil-building specialty does not contain 22 rules")
    if len(rules_by_id) != len(rules) or not EXPECTED_ARTICLES.keys() <= rules_by_id.keys():
        raise AssertionError("CIVIL-02: one or more stable rule IDs are missing or duplicated")

    civil_profile = profile(industrial=False, children=True)
    industrial_profile = profile(industrial=True, children=True)
    non_child_profile = profile(industrial=False, children=False)
    for rule_id, article in EXPECTED_ARTICLES.items():
        rule = rules_by_id[rule_id]
        basis = rule["basis"]
        if rule.get("authority_mode") != "normative" or rule.get("status") != "active":
            raise AssertionError(f"CIVIL-03: {rule_id} is not an active normative rule")
        if basis.get("source_role") != "B_核心规范" or basis.get("relative_path") != SOURCE_PATH:
            raise AssertionError(f"CIVIL-03: {rule_id} does not resolve to the civil-building B source")
        if basis.get("sha256") != SOURCE_SHA256 or basis.get("article") != article:
            raise AssertionError(f"CIVIL-03: {rule_id} has an incorrect source hash or article")
        evidence = rule.get("graphic_evidence_requirements", {})
        if evidence.get("required") is not True or not evidence.get("required_roles"):
            raise AssertionError(f"CIVIL-04: {rule_id} lacks explicit graphic evidence requirements")
        if rule.get("calculation_required") is not (rule_id in NUMERIC_RULES):
            raise AssertionError(f"CIVIL-04: {rule_id} has an incorrect calculation flag")
        if evaluate_trigger(rule["trigger"], civil_profile) != "active":
            raise AssertionError(f"CIVIL-05: {rule_id} did not activate for a civil building")
        if evaluate_trigger(rule["trigger"], industrial_profile) != "inactive":
            raise AssertionError(f"CIVIL-05: {rule_id} activated for an industrial building")

    child_rule = rules_by_id["CIVIL-5.3.11-CHILD-STAIR-WELL-GUARD"]
    if evaluate_trigger(child_rule["trigger"], non_child_profile) != "inactive":
        raise AssertionError("CIVIL-06: the child stair-well rule activated without child activities")
    if "10m" not in rules_by_id["CIVIL-4.5.1-EXHAUST-OUTLET-SEPARATION"]["comparison_method"]:
        raise AssertionError("CIVIL-07: exhaust outlet distance comparison is missing")
    if "不得作为强制数值阈值" not in rules_by_id["CIVIL-5.6.2-PUBLIC-TOILET-LAYOUT"]["comparison_method"]:
        raise AssertionError("CIVIL-07: the advisory toilet service radius is not explicitly excluded")

    print("PASS: 8 civil-building rule additions and catalog counts validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
