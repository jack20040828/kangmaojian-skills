#!/usr/bin/env python3
"""Shared v1.4-v1.6 project-profile and executable-rule helpers."""

from __future__ import annotations

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_RULE_CATALOG = SKILL_DIR / "generated" / "review-rules.json"

REQUIRED_RULE_PACKS = {
    "residential_core_v1": {
        "RES-4.1.2-STOREY-HEIGHT",
        "RES-4.1.2-CLEAR-HEIGHT",
        "ACCESS-3.4-ACCESSIBLE-DWELLING",
        "ENERGY-5.2.1-SOLAR-SYSTEM",
        "FIRE-2.2.3-RESCUE-OPENINGS",
        "WATER-4.4.1-ROOF-LAYER-COUNT",
        "WATER-4.6.1-INTERIOR-FLOOR-LAYERS",
        "WATER-4.5.2-EXTERIOR-WALL-LAYERS",
        "RES-4.1.12-WET-AREA-LEVEL",
        "RES-4.1.10-BATHROOM-COF",
        "RES-4.2.9-PUBLIC-AREA-COF",
        "RES-4.1.15-BALCONY-GUARD",
        "RES-4.2.8-PUBLIC-GUARD",
        "RES-4.2.2-STAIR-HORIZONTAL-HANDRAIL",
    }
}


def load_catalog(path: Path = DEFAULT_RULE_CATALOG) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_profile(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def profile_record(profile: dict, field: str) -> dict:
    value = profile.get("facts", {}).get(field, {})
    return value if isinstance(value, dict) else {}


def profile_state(profile: dict, field: str) -> str:
    return str(profile_record(profile, field).get("status", "unknown")).strip()


def profile_value(profile: dict, field: str):
    return profile_record(profile, field).get("value", "")


def normalized(value):
    if isinstance(value, bool):
        return value
    text = str(value).strip().casefold()
    if text in {"true", "yes", "y", "是", "有", "设置", "required"}:
        return True
    if text in {"false", "no", "n", "否", "无", "未设置", "not_applicable"}:
        return False
    return text


def condition_state(profile: dict, condition: dict) -> str:
    field = str(condition.get("field", "")).strip()
    if not field or profile_state(profile, field) == "unknown":
        return "uncertain"
    actual = normalized(profile_value(profile, field))
    comparisons: list[bool] = []
    if "values" in condition:
        allowed = {normalized(value) for value in condition.get("values", [])}
        comparisons.append(actual in allowed)
    if "contains" in condition:
        actual_text = str(actual).casefold()
        tokens = [str(normalized(value)).casefold() for value in condition.get("contains", [])]
        comparisons.append(any(token and token in actual_text for token in tokens))
    for key, operator in (("minimum", lambda value, limit: value >= limit), ("maximum", lambda value, limit: value <= limit)):
        if key not in condition:
            continue
        try:
            comparisons.append(operator(float(profile_value(profile, field)), float(condition[key])))
        except (TypeError, ValueError):
            return "uncertain"
    if not comparisons:
        return "uncertain"
    return "active" if all(comparisons) else "inactive"


def evaluate_trigger(trigger: dict, profile: dict) -> str:
    if trigger.get("always") is True:
        return "active"
    all_conditions = trigger.get("all", [])
    if all_conditions:
        states = [condition_state(profile, condition) for condition in all_conditions]
        if "inactive" in states:
            return "inactive"
        return "uncertain" if "uncertain" in states else "active"
    any_conditions = trigger.get("any", [])
    if any_conditions:
        states = [condition_state(profile, condition) for condition in any_conditions]
        if "active" in states:
            return "active"
        return "uncertain" if "uncertain" in states else "inactive"
    return "uncertain"


def applicable_rules(catalog: dict, profile: dict, family: str, report_type: str) -> list[tuple[dict, str]]:
    result: list[tuple[dict, str]] = []
    for rule in catalog.get("rules", []):
        if rule.get("status") != "active":
            continue
        if family not in rule.get("review_families", []):
            continue
        if report_type not in rule.get("report_types", []):
            continue
        state = evaluate_trigger(rule.get("trigger", {}), profile)
        if state != "inactive":
            result.append((rule, state))
    return result


def trigger_summary(rule: dict, profile: dict) -> str:
    trigger = rule.get("trigger", {})
    if trigger.get("always") is True:
        return "基础必审规则。"
    conditions = trigger.get("all") or trigger.get("any") or []
    parts = []
    for condition in conditions:
        field = condition.get("field", "")
        record = profile_record(profile, field)
        parts.append(f"{field}={record.get('value', '') or '[unknown]'}({record.get('status', 'unknown')})")
    return "；".join(parts) + "。"
