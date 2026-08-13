#!/usr/bin/env python3
"""Validate reviewer-approved gold cases and score blind review result mappings."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_CASES = SKILL_DIR / "evals" / "gold-cases.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_cases(payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "1.0":
        errors.append("gold cases require schema_version 1.0")
    thresholds = payload.get("thresholds", {})
    required_thresholds = {
        "high_risk_safety_recall", "overall_issue_recall", "verified_issue_precision",
        "citation_accuracy", "max_mixed_root_count", "max_unsupported_verified_count",
    }
    if not isinstance(thresholds, dict) or required_thresholds - set(thresholds):
        errors.append("gold thresholds are incomplete")
    ids: set[str] = set()
    for case in payload.get("cases", []):
        case_id = str(case.get("id", "")).strip()
        if not case_id or case_id in ids:
            errors.append(f"duplicate or blank gold case id: {case_id}")
        ids.add(case_id)
        if case.get("status") not in {"pending_reviewer_confirmation", "approved", "holdout"}:
            errors.append(f"{case_id}: invalid status")
        for source in case.get("source_paths", []):
            if not Path(source).exists():
                errors.append(f"{case_id}: source path missing: {source}")
        if case.get("status") in {"approved", "holdout"}:
            gold_path = Path(str(case.get("approved_gold_path", "")))
            if not gold_path.exists():
                errors.append(f"{case_id}: approved gold file is missing")
            elif sha256_file(gold_path) != case.get("approved_gold_sha256"):
                errors.append(f"{case_id}: approved gold hash changed")
            issues = case.get("expected_issues", [])
            if not isinstance(issues, list) or not issues:
                errors.append(f"{case_id}: approved case requires expected_issues")
            issue_ids = [str(item.get("id", "")).strip() for item in issues]
            if any(not value for value in issue_ids) or len(issue_ids) != len(set(issue_ids)):
                errors.append(f"{case_id}: expected issue IDs must be non-empty and unique")
            for issue in issues:
                if issue.get("risk") not in {"high", "normal"}:
                    errors.append(f"{case_id}/{issue.get('id', '')}: invalid risk")
                for field in ["drawing_ref", "root_cause", "category"]:
                    if not str(issue.get(field, "")).strip():
                        errors.append(f"{case_id}/{issue.get('id', '')}: missing {field}")
    return errors


def score(payload: dict, results: dict) -> tuple[dict, list[str]]:
    errors: list[str] = []
    approved = [case for case in payload.get("cases", []) if case.get("status") in {"approved", "holdout"}]
    if not approved:
        return {}, ["no reviewer-approved gold cases; release evaluation is blocked"]
    result_map = {item.get("case_id"): item for item in results.get("cases", [])}
    expected_total = 0
    found_total = 0
    high_total = 0
    high_safe = 0
    verified_matches = 0
    false_positives = 0
    cited_verified = 0
    correct_citations = 0
    mixed_root_count = 0
    unsupported_verified_count = 0
    for case in approved:
        case_id = case["id"]
        result = result_map.get(case_id)
        if not result:
            errors.append(f"missing blind-review result for {case_id}")
            continue
        outcomes = {item.get("expected_issue_id"): item for item in result.get("findings", [])}
        for issue in case.get("expected_issues", []):
            expected_total += 1
            if issue.get("risk") == "high":
                high_total += 1
            finding = outcomes.get(issue["id"], {})
            outcome = finding.get("outcome", "missed")
            if outcome not in {"found", "needs_review", "missed"}:
                errors.append(f"{case_id}/{issue['id']}: invalid outcome")
                outcome = "missed"
            if outcome == "found":
                found_total += 1
            if issue.get("risk") == "high" and outcome in {"found", "needs_review"}:
                high_safe += 1
            if outcome == "found" and finding.get("verified") is True:
                verified_matches += 1
                cited_verified += 1
                if finding.get("citation_correct") is True:
                    correct_citations += 1
        false_positives += int(result.get("false_positive_count", 0))
        mixed_root_count += int(result.get("mixed_root_count", 0))
        unsupported_verified_count += int(result.get("unsupported_verified_count", 0))
    metrics = {
        "high_risk_safety_recall": high_safe / high_total if high_total else 1.0,
        "overall_issue_recall": found_total / expected_total if expected_total else 0.0,
        "verified_issue_precision": verified_matches / (verified_matches + false_positives) if verified_matches + false_positives else 0.0,
        "citation_accuracy": correct_citations / cited_verified if cited_verified else 0.0,
        "mixed_root_count": mixed_root_count,
        "unsupported_verified_count": unsupported_verified_count,
        "approved_case_count": len(approved),
        "expected_issue_count": expected_total,
    }
    thresholds = payload["thresholds"]
    failures = []
    for metric in ["high_risk_safety_recall", "overall_issue_recall", "verified_issue_precision", "citation_accuracy"]:
        if metrics[metric] < thresholds[metric]:
            failures.append(f"{metric}={metrics[metric]:.3f} below {thresholds[metric]:.3f}")
    if mixed_root_count > thresholds["max_mixed_root_count"]:
        failures.append("mixed_root_count exceeds threshold")
    if unsupported_verified_count > thresholds["max_unsupported_verified_count"]:
        failures.append("unsupported_verified_count exceeds threshold")
    return metrics, errors + failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    try:
        payload = load(args.cases)
    except Exception as error:
        print(f"FAIL: invalid gold cases: {error}")
        return 1
    errors = validate_cases(payload)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    if args.validate_only:
        print(f"PASS: {len(payload.get('cases', []))} gold-case candidates are structurally valid")
        return 0
    if not args.results:
        print("FAIL: --results is required for release evaluation")
        return 2
    try:
        metrics, failures = score(payload, load(args.results))
    except Exception as error:
        print(f"FAIL: invalid evaluation results: {error}")
        return 1
    output = {"status": "pass" if not failures else "fail", "metrics": metrics, "failures": failures}
    if args.json_output:
        args.json_output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 2
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
