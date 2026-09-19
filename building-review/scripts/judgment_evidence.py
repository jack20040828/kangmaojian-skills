"""v1.7 evidence checks. Validate submitted judgments; never manufacture them."""
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

LEDGER = "judgment_evidence.json"
UNITS = {"mm": ("length", Decimal("0.001")), "m": ("length", Decimal(1)),
         "%": ("ratio", Decimal("0.01")), "ratio": ("ratio", Decimal(1)),
         "dB": ("sound", Decimal(1)), "m2": ("area", Decimal(1)),
         "count": ("count", Decimal(1))}


def requirements(rule: dict) -> list[dict]:
    return rule.get("judgment_requirements", {}).get("obligations") or [
        {"id": f"F{i:02d}", "kind": "judgment", "requirement": text}
        for i, text in enumerate(rule.get("required_facts", []), 1)
    ]


def placeholders(checks: list[dict], rules: dict) -> dict:
    return {"schema_version": "1.0", "checks": [
        {"check_id": c["check_id"], "object_id": "", "obligations": [
            {"id": r["id"], "fact_ids": [], "observation": "", "result": "unknown", "reason": ""}
            for r in requirements(rules[c["rule_id"]])
        ], "object_links": [], "counterevidence": {"fact_ids": [], "finding": "unknown", "reason": ""}}
        for c in checks
    ], "issue_screening": []}


def ids(value) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    return [x.strip() for x in str(value or "").replace("；", ";").replace(",", ";").split(";") if x.strip()]


def quantity(value, unit):
    if unit not in UNITS:
        raise ValueError(f"unsupported unit: {unit}")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("actual/threshold must be numeric") from exc
    if not number.is_finite():
        raise ValueError("actual/threshold must be finite")
    dimension, scale = UNITS[unit]
    return dimension, number * scale


def numeric_result(fact: dict, requirement: dict) -> str:
    dimension, actual = quantity(fact.get("value"), fact.get("unit"))
    target_dimension, target = quantity(requirement.get("threshold"), requirement.get("unit"))
    if dimension != target_dimension:
        raise ValueError("incompatible units")
    op = requirement.get("operator")
    if op not in {">=", "<=", ">", "<", "=="}:
        raise ValueError("unsupported comparison operator")
    result = {">=": actual >= target, "<=": actual <= target, ">": actual > target,
              "<": actual < target, "==": actual == target}[op]
    return "pass" if result else "fail"


def validate_room_window(record: dict, facts: dict, chains: dict) -> list[str]:
    errors = []
    links = record.get("object_links", [])
    roles = ["room", "exterior_wall", "window_position", "window_mark", "schedule"]
    by_role = {x.get("role"): x for x in links if isinstance(x, dict)}
    if len(links) != len(by_role) or not set(roles).issubset(by_role):
        return ["room-window association requires unique room, exterior_wall, window_position, window_mark, schedule roles"]
    for role in roles:
        link = by_role[role]
        fact = facts.get(link.get("fact_id"), {})
        chain = chains.get(link.get("chain_id"), {})
        if not fact or not link.get("object_id") or fact.get("needs_verification", "").lower() in {"yes", "true", "是", "1"}:
            errors.append(f"{role}: missing or unresolved object fact")
        if chain.get("check_id") != record.get("check_id") or link.get("fact_id") not in ids(chain.get("fact_ids")):
            errors.append(f"{role}: graphic chain does not prove the object fact")
    room, wall, window, mark, schedule = [by_role[r] for r in roles]
    if room.get("object_id") != record.get("object_id") or wall.get("related_object_id") != room.get("object_id"):
        errors.append("exterior wall is not associated with the checked room")
    if window.get("related_object_id") != wall.get("object_id"):
        errors.append("window belongs to another wall or room")
    if mark.get("object_id") != window.get("object_id") or schedule.get("object_id") != window.get("object_id"):
        errors.append("window mark/schedule refers to another opening")
    if not mark.get("mark") or mark.get("mark") != schedule.get("mark"):
        errors.append("window mark differs from schedule")
    if not record.get("association_observation"):
        errors.append("room-window association requires a visual observation, not just IDs")
    return errors


def validate_data(data: dict, checks: list[dict], rules: dict, facts: dict,
                  issues: list[dict], chains: dict) -> list[str]:
    errors = []
    if data.get("schema_version") != "1.0":
        errors.append("judgment evidence schema must be 1.0")
    records = data.get("checks", [])
    records_by_id = {r.get("check_id"): r for r in records if isinstance(r, dict)}
    check_ids = {c["check_id"] for c in checks}
    if len(records_by_id) != len(records) or set(records_by_id) != check_ids:
        errors.append("judgment evidence must map every check exactly once; no dangling or duplicate checks")
    for check in checks:
        cid = check["check_id"]
        record = records_by_id.get(cid, {})
        if check.get("decision_state") != "resolved":
            continue
        rule = rules.get(check.get("rule_id"), {})
        if not record.get("object_id"):
            errors.append(f"{cid}: missing checked object")
        expected = {r["id"]: r for r in requirements(rule)}
        actual = record.get("obligations", [])
        by_id = {r.get("id"): r for r in actual if isinstance(r, dict)}
        if not expected or set(expected) != set(by_id) or len(by_id) != len(actual):
            errors.append(f"{cid}: incomplete or duplicate obligations")
        outcomes = []
        for oid, requirement in expected.items():
            proof = by_id.get(oid, {})
            refs = ids(proof.get("fact_ids"))
            if not refs or not set(refs).issubset(facts) or not set(refs).issubset(ids(check.get("fact_ids"))):
                errors.append(f"{cid}/{oid}: missing check-specific facts")
                continue
            if any(facts[f].get("needs_verification", "").lower() in {"yes", "true", "是", "1"} for f in refs):
                errors.append(f"{cid}/{oid}: unresolved fact")
            if not proof.get("observation") or not proof.get("reason"):
                errors.append(f"{cid}/{oid}: observation and comparison reason required")
            result = proof.get("result")
            if result not in {"pass", "fail", "not_applicable"}:
                errors.append(f"{cid}/{oid}: obligation remains unresolved")
            if result == "not_applicable" and check.get("applicability") != "不适用":
                if requirement.get("conditional") is not True or not proof.get("scope_reason"):
                    errors.append(f"{cid}/{oid}: applicable obligation cannot be waived")
            if requirement.get("kind") == "numeric" and result != "not_applicable":
                try:
                    if len(refs) != 1:
                        raise ValueError("numeric obligation requires one explicit measured fact")
                    computed = numeric_result(facts[refs[0]], requirement)
                    if computed != result:
                        errors.append(f"{cid}/{oid}: numeric comparison conflicts with submitted result")
                except ValueError as exc:
                    errors.append(f"{cid}/{oid}: {exc}")
            outcomes.append(result)
        expected_conclusion = "不适用" if outcomes and all(x == "not_applicable" for x in outcomes) else "不符合" if "fail" in outcomes else "符合"
        if check.get("conclusion") != expected_conclusion:
            errors.append(f"{cid}: conclusion conflicts with obligation results")
        counter = record.get("counterevidence", {})
        refs = ids(counter.get("fact_ids"))
        if not refs or not set(refs).issubset(facts) or not counter.get("reason"):
            errors.append(f"{cid}: counterevidence search requires source facts and observation")
        if counter.get("finding") not in {"consistent", "none_found"}:
            errors.append(f"{cid}: unresolved counterevidence conflict")
        if record.get("assertion") == "absent" and counter.get("observed") == "present":
            errors.append(f"{cid}: requested missing expression already present")
        if rule.get("judgment_requirements", {}).get("object_linkage") == "room_window" and check.get("applicability") != "不适用":
            errors.extend(f"{cid}: {message}" for message in validate_room_window(record, facts, chains))
    screening = data.get("issue_screening", [])
    by_issue = {r.get("issue_id"): r for r in screening if isinstance(r, dict)}
    if len(by_issue) != len(screening) or set(by_issue) != {i["issue_id"] for i in issues}:
        errors.append("issue screening must map each candidate exactly once")
    for issue in issues:
        iid = issue["issue_id"]
        decision = by_issue.get(iid, {})
        if decision.get("responsibility") not in {"design", "client_data", "coordination", "undetermined"} or not decision.get("reason"):
            errors.append(f"{iid}: responsibility and value screening required")
        if issue.get("status") == "ai_ready":
            if decision.get("responsibility") not in {"design", "coordination"} or decision.get("delivery_decision") != "include" or not decision.get("design_action"):
                errors.append(f"{iid}: formal issue requires a supported design action and delivery responsibility")
            if decision.get("value_basis") == "index_difficulty_only":
                errors.append(f"{iid}: indexing difficulty alone is not a design defect")
        elif decision.get("delivery_decision") == "include":
            errors.append(f"{iid}: non-ready candidate cannot be included")
    return errors


def validate(root: Path, checks, rules, facts, issues, chains) -> list[str]:
    try:
        data = json.loads((root / LEDGER).read_text(encoding="utf-8"))
        return validate_data(data, checks, rules, facts, issues, chains)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return [f"invalid {LEDGER}: {exc}"]
