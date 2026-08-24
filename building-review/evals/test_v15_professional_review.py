#!/usr/bin/env python3
"""Exercise v1.5 graphic, applicability, and independent-review gates."""

from __future__ import annotations

import copy
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS))

from validate_review_package import validate_v15_professional_gates  # noqa: E402
from create_review_workspace import TEMPLATES  # noqa: E402


def verify_v15_expansion() -> None:
    required_ledgers = {
        "graphic_evidence_chain.csv",
        "applicability_decisions.csv",
        "independent_review_log.csv",
    }
    if not required_ledgers.issubset(TEMPLATES):
        raise AssertionError("v1.5 workspace templates are incomplete")
    with tempfile.TemporaryDirectory(prefix="building-review-v15-expand-") as temp_value:
        temp = Path(temp_value)
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        created = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "create_review_workspace.py"),
                "匿名v1.5项目",
                "--root",
                str(temp / "reviews"),
                "--schema-version",
                "1.5",
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
        )
        if created.returncode != 0:
            raise AssertionError(f"v1.5 workspace creation failed: {created.stdout}{created.stderr}")
        workspace = Path(created.stdout.strip().splitlines()[-1])
        manifest = json.loads((workspace / "review_manifest.json").read_text(encoding="utf-8"))
        if manifest.get("schema_version") != "1.5":
            raise AssertionError("explicit v1.5 compatibility workspace was not created")
        if any(not (workspace / name).exists() for name in required_ledgers):
            raise AssertionError("new v1.5 workspace is missing a professional ledger")
        inventory_path = workspace / "drawing_inventory.csv"
        with inventory_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=TEMPLATES["drawing_inventory.csv"])
            writer.writeheader()
            writer.writerow({
                "source_file": "source/synthetic.svg",
                "page": "1",
                "sheet_no": "1",
                "drawing_no": "SYN-01",
                "drawing_name": "合成平面图",
                "discipline": "建筑",
                "content_type": "平面图",
                "scale": "1:100",
                "title_block_status": "已核对",
                "review_family": "平面图",
                "review_status": "needs_review",
                "review_check_ids": "",
                "review_notes": "待审",
                "notes": "",
            })
        catalog = {"schema_version": "1.1", "rules": [{
            "rule_id": "SYN-EXPAND-001",
            "status": "active",
            "authority_mode": "normative",
            "specialty": "合成专项",
            "coverage_topic": "function_layout",
            "review_families": ["平面图"],
            "report_types": ["single"],
            "trigger": {"always": True},
            "required_facts": ["合成事实"],
            "comparison_method": "核对合成事实。",
            "calculation_required": False,
            "basis": {},
            "applicability_conditions": [{
                "condition_id": "SCOPE-01",
                "description": "合成范围条件",
                "expected": True,
                "outcome_when_false": "not_applicable",
            }],
            "graphic_evidence_requirements": {
                "required": True,
                "claim_type": "cross_sheet",
                "required_roles": ["plan", "section"],
                "sensitive_to_ambiguity": True,
            },
            "independent_review_required": True,
        }]}
        catalog_path = temp / "synthetic-catalog.json"
        catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        generated = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "generate_project_checklist.py"),
                str(workspace),
                "--catalog",
                str(catalog_path),
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
        )
        if generated.returncode != 0:
            raise AssertionError(f"v1.5 checklist expansion failed: {generated.stdout}{generated.stderr}")
        def read_csv(name: str):
            with (workspace / name).open(encoding="utf-8-sig", newline="") as handle:
                return list(csv.DictReader(handle))
        checks = read_csv("check_matrix.csv")
        inventory = read_csv("drawing_inventory.csv")
        applicability = read_csv("applicability_decisions.csv")
        graphics = read_csv("graphic_evidence_chain.csv")
        if len(checks) != 1 or len(applicability) != 1 or len(graphics) != 2:
            raise AssertionError("v1.5 checklist expansion did not create required professional rows")
        if checks[0]["graphic_claim_type"] != "cross_sheet" or not checks[0]["applicability_decision_ids"]:
            raise AssertionError("v1.5 checklist did not link professional ledgers")
        if inventory[0]["review_status"] != "needs_review":
            raise AssertionError("v1.5 generator must not pre-close a drawing")


def base_records(fixture: str):
    rule = {
        "rule_id": "SYN-GRAPHIC-001",
        "applicability_conditions": [{
            "condition_id": "SCOPE-01",
            "description": "项目属于本合成规则范围",
            "expected": True,
            "outcome_when_false": "not_applicable",
        }],
        "graphic_evidence_requirements": {
            "required": True,
            "claim_type": "cross_sheet",
            "required_roles": ["plan", "section"],
            "sensitive_to_ambiguity": True,
        },
        "independent_review_required": True,
    }
    check = {
        "check_id": "C-V15-001",
        "rule_id": rule["rule_id"],
        "decision_state": "resolved",
        "applicability": "适用",
        "conclusion": "符合",
        "graphic_claim_type": "cross_sheet",
        "graphic_chain_ids": "G-PLAN;G-SECTION",
        "graphic_gate_reason": "",
        "applicability_decision_ids": "APP-001",
        "independent_review_id": "IR-001",
    }
    graphic_template = {
        "check_id": check["check_id"],
        "source_file": fixture,
        "page": "1",
        "drawing_ref": "SYN-01 合成图",
        "location": "合成图中心",
        "graphic_element": "线、符号与对应关系",
        "observed_fact": "平面与剖面的标记可对应。",
        "interpretation": "两种表达指向同一控制对象。",
        "alternative_interpretation": "标记也可能只表示索引，不表示同一对象。",
        "elimination_basis": "图例、编号和定位尺寸共同排除该替代解释。",
        "fact_ids": "F001",
        "screenshot_path": fixture,
        "source_quality": "raster_high",
        "status": "resolved",
        "reviewer_name": "复核人甲",
        "reviewed_at": "2026-08-18T10:00:00",
        "notes": "合成回归证据。",
    }
    graphics = [
        dict(graphic_template, chain_id="G-PLAN", evidence_role="plan"),
        dict(graphic_template, chain_id="G-SECTION", evidence_role="section"),
    ]
    applicability = [{
        "decision_id": "APP-001",
        "check_id": check["check_id"],
        "rule_id": rule["rule_id"],
        "condition_id": "SCOPE-01",
        "condition_description": "项目属于本合成规则范围",
        "expected_value": "true",
        "actual_value": "true",
        "result": "met",
        "fact_ids": "F001",
        "drawing_refs": "SYN-01 合成图",
        "status": "resolved",
        "reviewer_name": "复核人甲",
        "reviewed_at": "2026-08-18T10:05:00",
        "notes": "合成适用条件。",
    }]
    independent = [{
        "review_id": "IR-001",
        "check_id": check["check_id"],
        "primary_reviewer": "审查智能体甲",
        "primary_reviewer_type": "agent",
        "primary_decision": "符合",
        "primary_reviewed_at": "2026-08-18T10:10:00",
        "secondary_reviewer": "人工复核人乙",
        "secondary_reviewer_type": "human",
        "secondary_decision": "符合",
        "secondary_reviewed_at": "2026-08-18T10:20:00",
        "blind_input_scope": "source_rule_only",
        "agreement": "yes",
        "adjudicator": "",
        "adjudicator_type": "",
        "adjudicated_decision": "",
        "adjudicated_at": "",
        "status": "agreed",
        "notes": "第二复核者仅接收原始证据和规则。",
    }]
    return [check], {rule["rule_id"]: rule}, graphics, applicability, independent


def mutate(name: str, check, graphics, applicability, independent) -> None:
    if name == "closed_chain":
        return
    if name == "missing_required_role":
        graphics.pop()
    elif name == "missing_screenshot":
        graphics[0]["screenshot_path"] = ""
    elif name == "raster_only":
        for row in graphics:
            row["source_quality"] = "raster_limited"
    elif name == "ambiguity_unresolved":
        for row in graphics:
            row["alternative_interpretation"] = ""
            row["elimination_basis"] = ""
    elif name == "pending_claim":
        check[0]["graphic_claim_type"] = "pending"
    elif name == "applicability_unknown":
        applicability[0]["result"] = "unknown"
    elif name == "not_applicable_without_exclusion":
        check[0]["applicability"] = "不适用"
        check[0]["conclusion"] = "不适用"
    elif name == "condition_unresolved":
        applicability[0]["status"] = "needs_review"
    elif name == "same_reviewer":
        independent[0]["secondary_reviewer"] = independent[0]["primary_reviewer"]
    elif name == "no_human_reviewer":
        independent[0]["secondary_reviewer_type"] = "agent"
    elif name == "disagreement_unadjudicated":
        independent[0]["secondary_decision"] = "不符合"
        independent[0]["agreement"] = "no"
        independent[0]["status"] = "needs_review"
    else:
        raise AssertionError(f"unknown mutation: {name}")


def main() -> int:
    verify_v15_expansion()
    metadata_path = SKILL_DIR / "evals" / "graphic-ambiguity-cases.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    cases = metadata.get("cases", [])
    if len(cases) != 12 or len({case.get("id") for case in cases}) != 12:
        raise AssertionError("v1.5 graphic ambiguity metadata must contain 12 unique cases")
    for case in cases:
        fixture = "evals/" + case["fixture"]
        fixture_path = SKILL_DIR / fixture
        if not fixture_path.exists() or fixture_path.stat().st_size == 0:
            raise AssertionError(f"{case['id']}: missing synthetic fixture {fixture}")
        records = copy.deepcopy(base_records(fixture))
        checks, rules, graphics, applicability, independent = records
        mutate(case["mutation"], checks, graphics, applicability, independent)
        errors = validate_v15_professional_gates(
            SKILL_DIR,
            checks,
            rules,
            {"F001"},
            graphics,
            applicability,
            independent,
        )
        if case["expected"] == "pass":
            if errors:
                raise AssertionError(f"{case['id']}: expected pass, got {errors}")
        elif case["expected_fragment"] not in "\n".join(errors):
            raise AssertionError(
                f"{case['id']}: missing expected failure {case['expected_fragment']!r}; got {errors}"
            )
    print("PASS: 12 v1.5 graphic, applicability, and independent-review scenarios completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
