#!/usr/bin/env python3
"""Exercise the global residential packet, false-completion gate, and holdout assets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS))

from review_rules import REQUIRED_RULE_PACKS, condition_state, evaluate_trigger  # noqa: E402
from validate_review_package import (  # noqa: E402
    invalid_absence_not_applicable,
    validate_required_rule_packs,
)


def profile(building_use: str) -> dict:
    return {
        "facts": {
            "building_use": {
                "status": "confirmed",
                "value": building_use,
                "fact_ids": ["F001"],
            }
        }
    }


def main() -> int:
    catalog = json.loads((SKILL_DIR / "generated" / "review-rules.json").read_text(encoding="utf-8"))
    rules_by_id = {rule["rule_id"]: rule for rule in catalog["rules"]}
    required = REQUIRED_RULE_PACKS["residential_core_v1"]
    residential = profile("二类高层住宅及配套门厅")
    non_residential = profile("办公建筑")

    if condition_state(residential, {"field": "building_use", "contains": ["住宅"]}) != "active":
        raise AssertionError("REG-51: compound residential use did not trigger contains condition")
    if condition_state(non_residential, {"field": "building_use", "contains": ["住宅"]}) != "inactive":
        raise AssertionError("REG-51: non-residential use triggered residential packet")

    if len(required) != 14 or not required.issubset(rules_by_id):
        raise AssertionError("REG-52: global residential packet is incomplete")
    for rule_id in required:
        rule = rules_by_id[rule_id]
        if rule.get("rule_pack") != "residential_core_v1" or rule.get("absence_is_noncompliant") is not True:
            raise AssertionError(f"REG-52: {rule_id} lacks residential packet safeguards")
        if evaluate_trigger(rule["trigger"], residential) != "active":
            raise AssertionError(f"REG-52: {rule_id} did not activate for a residential project")
    exterior = rules_by_id["WATER-4.5.2-EXTERIOR-WALL-LAYERS"]["basis"]
    if exterior["display_name"] != "《建筑与市政工程防水通用规范》GB 55030-2022" or exterior["article"] != "第4.5.2条":
        raise AssertionError("REG-52: exterior-wall waterproof rule still cites the wrong source")

    missing_errors = validate_required_rule_packs(catalog, residential, [], "single")
    if not any("has no atomic check" in error for error in missing_errors):
        raise AssertionError("REG-53: a residential packet with no checks was accepted")

    checks = [{"rule_id": rule_id, "decision_state": "resolved"} for rule_id in sorted(required)]
    if validate_required_rule_packs(catalog, residential, checks, "single"):
        raise AssertionError("REG-54: a fully resolved residential packet was rejected")
    checks[0]["decision_state"] = "needs_review"
    unresolved_errors = validate_required_rule_packs(catalog, residential, checks, "single")
    if not any("remains unresolved" in error for error in unresolved_errors):
        raise AssertionError("REG-54: an unresolved residential packet was accepted")

    solar = rules_by_id["ENERGY-5.2.1-SOLAR-SYSTEM"]
    absence_na = {
        "applicability": "不适用",
        "conclusion": "不适用",
        "applicability_basis": "目录、节能说明和屋面图均未设置太阳能系统。",
    }
    if not invalid_absence_not_applicable(absence_na, solar):
        raise AssertionError("REG-55: absence of a required measure was accepted as not applicable")
    scoped_na = dict(absence_na, applicability_basis="既有建筑改造，非新建建筑，条文适用范围不成立。")
    if invalid_absence_not_applicable(scoped_na, solar):
        raise AssertionError("REG-55: positive project-scope fact did not support not applicable")

    holdout_input = json.loads((SKILL_DIR / "evals" / "gold" / "residential-holdout-input.json").read_text(encoding="utf-8"))
    holdout_gold = json.loads((SKILL_DIR / "evals" / "gold" / "residential-holdout-approved.json").read_text(encoding="utf-8"))
    if holdout_input.get("case_id") != holdout_gold.get("case_id"):
        raise AssertionError("REG-56: holdout input and gold IDs differ")
    if len(holdout_gold.get("expected_issues", [])) != 4 or len(holdout_gold.get("prohibited_findings", [])) != 6:
        raise AssertionError("REG-56: independent residential holdout coverage is incomplete")

    print("PASS: 6 residential rule-pack and holdout scenarios completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
