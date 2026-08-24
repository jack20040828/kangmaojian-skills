#!/usr/bin/env python3
"""Exercise v1.4 false-completion, routing, atomic-rule, audit, and gold gates."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS))

from route_specialties import routes  # noqa: E402
from validate_review_package import valid_coverage_topics  # noqa: E402


def run(args: list[str], expected: int, contains: str = "") -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(args, text=True, encoding="utf-8", errors="replace", capture_output=True, env=env)
    output = result.stdout + result.stderr
    if result.returncode != expected or (contains and contains not in output):
        raise AssertionError(
            f"command failed expectation ({expected}, {contains!r}): {' '.join(args)}\n"
            f"exit={result.returncode}\n{output}"
        )
    return result


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, records: list[dict[str, str]]) -> None:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        fields = list(csv.DictReader(handle).fieldnames or [])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def confirmed_profile(path: Path) -> None:
    profile = json.loads(path.read_text(encoding="utf-8"))
    boolean_fields = {
        "industrial_building", "overnight_stay", "sprinkler", "basement", "elevator",
        "accessible_requirement", "roof_accessible", "wet_rooms", "parking",
        "photovoltaic_or_solar", "food_service", "dormitory_or_hotel", "school",
        "office", "children_activity",
    }
    values = {
        "location_province": "湖南省",
        "location_city": "永州市",
        "building_use": "生产值班办公用房",
        "gross_floor_area_m2": 1000,
        "building_height_m": 8.4,
        "floors_above": 2,
        "floors_below": 0,
        "fire_hazard_class": "戊类",
        "fire_resistance_rating": "二级",
        "occupant_load": 20,
    }
    for key, record in profile["facts"].items():
        record["status"] = "confirmed"
        record["value"] = False if key in boolean_fields else values.get(key, "已确认")
        record["fact_ids"] = ["F001"]
        record["notes"] = "由匿名图纸事实确认。"
    profile.update(confirmed=True, confirmed_by="匿名审查人", confirmed_at="2026-08-12T10:00:00")
    profile["route_confirmation"] = {
        "confirmed": True,
        "confirmed_by": "匿名审查人",
        "confirmed_at": "2026-08-12T10:10:00",
        "notes": "已核对项目功能和所在地。",
    }
    profile["discovery_tracks"] = {
        "technical_compliance": {"status": "completed", "notes": "已完成技术条文逐项检查。"},
        "design_depth": {"status": "completed", "notes": "已完成内部一致性和设计深度检查。"},
        "optimization": {"status": "completed", "notes": "已完成优化建议独立扫描。"},
    }
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    python = sys.executable
    with tempfile.TemporaryDirectory(prefix="building-review-v14-") as temp_value:
        temp = Path(temp_value)
        created = run(
            [
                python,
                str(SCRIPTS / "create_review_workspace.py"),
                "匿名v1.4项目",
                "--root",
                str(temp / "reviews"),
                "--schema-version",
                "1.4",
            ],
            0,
        )
        workspace = Path(created.stdout.strip().splitlines()[-1])
        manifest = json.loads((workspace / "review_manifest.json").read_text(encoding="utf-8"))
        if manifest.get("schema_version") != "1.4" or not (workspace / "project_profile.json").exists():
            raise AssertionError("REG-39: new workspace is not v1.4 with a project profile")

        drawing = workspace / "source" / "drawing.txt"
        drawing.write_text("anonymous v1.4 drawing\n", encoding="utf-8")
        inventory = {
            "source_file": "source/drawing.txt",
            "page": "1",
            "sheet_no": "1",
            "drawing_no": "A-01",
            "drawing_name": "一层平面图",
            "discipline": "建筑",
            "content_type": "平面图",
            "scale": "1:100",
            "title_block_status": "已核对",
            "review_family": "平面图",
            "review_status": "needs_review",
            "review_check_ids": "",
            "review_notes": "原子检查尚未完成。",
            "notes": "",
        }
        fact = {
            "fact_id": "F001",
            "source_file": "source/drawing.txt",
            "page": "1",
            "drawing_no": "A-01",
            "drawing_name": "一层平面图",
            "location": "平面及说明",
            "fact_type": "综合事实",
            "raw_text_or_measure": "A-01一层平面图标注2个出口，最小净宽1.20m，建筑高度8.40m。",
            "value": "",
            "unit": "",
            "confidence": "高",
            "needs_verification": "否",
            "notes": "",
        }
        write_rows(workspace / "drawing_inventory.csv", [inventory])
        write_rows(workspace / "fact_ledger.csv", [fact])
        confirmed_profile(workspace / "project_profile.json")
        wet_profile = json.loads((workspace / "project_profile.json").read_text(encoding="utf-8"))
        wet_profile["facts"]["wet_rooms"].update(
            status="confirmed",
            value=True,
            fact_ids=["F001"],
            notes="匿名平面包含湿房间。",
        )
        (workspace / "project_profile.json").write_text(
            json.dumps(wet_profile, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        routed = run([python, str(SCRIPTS / "route_specialties.py"), str(workspace), "--json"], 0)
        routed_payload = json.loads(routed.stdout)
        specialties = {item["specialty"] for item in routed_payload["candidates"]}
        if "018湖南省政策规定专项" not in specialties or "019长沙市政策规定专项" in specialties:
            raise AssertionError("REG-40: jurisdiction routing enabled the wrong local policy")
        if any(item["specialty"] == "012宿舍、旅馆建筑专项" for item in routes("本项目未设置宿舍。")):
            raise AssertionError("REG-41: negative dormitory wording triggered the dormitory specialty")

        run([python, str(SCRIPTS / "generate_project_checklist.py"), str(workspace)], 0, "unreviewed atomic checks")
        validate = [python, str(SCRIPTS / "validate_review_package.py"), str(workspace)]
        run(validate, 1, "unreviewed atomic check blocks report generation")

        checks = read_rows(workspace / "check_matrix.csv")
        catalog = json.loads((SKILL_DIR / "generated" / "review-rules.json").read_text(encoding="utf-8"))
        rules_by_id = {rule["rule_id"]: rule for rule in catalog["rules"]}
        catalog_waterproofing_topics = {
            "wet_room_waterproofing",
            "exterior_wall_waterproofing",
            "roof_waterproofing",
        }
        if not catalog_waterproofing_topics.issubset(valid_coverage_topics(catalog)):
            raise AssertionError("REG-42: catalog-defined waterproofing topics are not valid v1.4 topics")
        if not any(check["coverage_topic"] == "wet_room_waterproofing" for check in checks):
            raise AssertionError("REG-43: wet-room profile did not expand its catalog-defined topic")
        for check in checks:
            rule = rules_by_id[check["rule_id"]]
            check.update(
                decision_state="resolved",
                applicability="适用",
                actual_fact="A-01一层平面图记录2个出口，最小净宽1.20m，位置及相邻关系明确。",
                fact_ids="F001",
                comparison_record="已将A-01图纸事实与本规则要求逐项比较，结果符合。",
                calculation_record="输入：出口2个、净宽1.20m；方法：按规则逐项计算和比较；结果：符合。" if rule["calculation_required"] else "",
                conclusion="符合",
                forms_issue="no",
                issue_id="",
                not_forming_reason="图纸事实与本规则要求比较后符合。",
                open_reason="",
                reviewer_gate="已复核",
            )
        inventory_rows = read_rows(workspace / "drawing_inventory.csv")
        inventory_rows[0]["review_status"] = "reviewed"
        inventory_rows[0]["review_notes"] = "全部已触发原子检查已关闭。"
        write_rows(workspace / "drawing_inventory.csv", inventory_rows)
        write_rows(workspace / "issue_candidates.csv", [])
        write_rows(workspace / "validation_log.csv", [])

        missing_comparison = [dict(item) for item in checks]
        missing_comparison[0]["comparison_record"] = ""
        write_rows(workspace / "check_matrix.csv", missing_comparison)
        run(validate, 1, "resolved check requires comparison_record")

        calculation_index = next(index for index, item in enumerate(checks) if rules_by_id[item["rule_id"]]["calculation_required"])
        missing_calculation = [dict(item) for item in checks]
        missing_calculation[calculation_index]["calculation_record"] = ""
        write_rows(workspace / "check_matrix.csv", missing_calculation)
        run(validate, 1, "requires calculation_record")

        missing_rule = checks[1:]
        missing_inventory = [dict(inventory_rows[0])]
        missing_inventory[0]["review_check_ids"] = ";".join(item["check_id"] for item in missing_rule)
        write_rows(workspace / "check_matrix.csv", missing_rule)
        write_rows(workspace / "drawing_inventory.csv", missing_inventory)
        run(validate, 1, "triggered atomic rules are missing")

        write_rows(workspace / "check_matrix.csv", checks)
        write_rows(workspace / "drawing_inventory.csv", inventory_rows)
        mismatched_topic = [dict(item) for item in checks]
        mismatch_index = next(
            index for index, item in enumerate(mismatched_topic)
            if item["coverage_topic"] == "wet_room_waterproofing"
        )
        mismatched_topic[mismatch_index]["coverage_topic"] = "fire_egress"
        write_rows(workspace / "check_matrix.csv", mismatched_topic)
        run(validate, 1, "does not match executable rule")
        write_rows(workspace / "check_matrix.csv", checks)
        anonymous_standards = temp / "anonymous-standards"
        anonymous_standards.mkdir()
        index_files = []
        for index, standard_source in enumerate(
            sorted({check["standard_source"] for check in checks if check.get("standard_source")}), start=1
        ):
            standard_path = anonymous_standards / f"standard-{index:03d}.txt"
            standard_path.write_text(
                f"Anonymous regression source for {standard_source}\n", encoding="utf-8"
            )
            index_files.append(
                {
                    "name": Path(standard_source).name,
                    "relative_path": standard_source,
                    "absolute_path": str(standard_path.resolve()),
                    "size_bytes": standard_path.stat().st_size,
                    "sha256": sha256(standard_path),
                }
            )
        anonymous_index = temp / "knowledge-index.json"
        anonymous_index.write_text(
            json.dumps(
                {
                    "schema_version": "1.1",
                    "generated_at": "2026-08-12T00:00:00Z",
                    "corpus_sha256": hashlib.sha256(
                        b"anonymous-regression-corpus"
                    ).hexdigest(),
                    "total_files": len(index_files),
                    "specialty_count": 0,
                    "files": index_files,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        snapshot = [
            python,
            str(SCRIPTS / "snapshot_review_integrity.py"),
            str(workspace),
            "--index",
            str(anonymous_index),
        ]
        run(snapshot, 0)
        audit = [python, str(SCRIPTS / "audit_review_completeness.py"), str(workspace)]
        run(audit, 0, "PASS:")
        run(validate, 0, "PASS:")

        stale_checks = [dict(item) for item in checks]
        stale_checks[0]["notes"] = "changed after audit"
        write_rows(workspace / "check_matrix.csv", stale_checks)
        run(validate, 1, "completion audit is stale")

        oil_workspace = temp / "legacy-v13-workspace"
        if oil_workspace.exists():
            run(
                [python, str(SCRIPTS / "validate_review_package.py"), str(oil_workspace)],
                1,
                "v1.3 technical closure requires standard_source",
            )

        run(
            [python, str(SCRIPTS / "run_gold_evals.py"), "--cases", str(SKILL_DIR / "evals" / "gold-cases.json"), "--validate-only"],
            0,
        )
        empty_results = temp / "empty-results.json"
        empty_results.write_text('{"cases": []}\n', encoding="utf-8")
        pending_only_cases = temp / "pending-only-gold.json"
        pending_payload = json.loads((SKILL_DIR / "evals" / "gold-cases.json").read_text(encoding="utf-8"))
        pending_payload["cases"] = [
            case for case in pending_payload["cases"]
            if case.get("status") == "pending_reviewer_confirmation"
        ]
        pending_only_cases.write_text(
            json.dumps(pending_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        run(
            [
                python,
                str(SCRIPTS / "run_gold_evals.py"),
                "--cases",
                str(pending_only_cases),
                "--results",
                str(empty_results),
            ],
            2,
            "no reviewer-approved gold cases",
        )

        source = temp / "gold-source.pdf"
        gold_doc = temp / "gold.docx"
        source.write_bytes(b"source")
        gold_doc.write_bytes(b"gold")
        synthetic_cases = {
            "schema_version": "1.0",
            "thresholds": {
                "high_risk_safety_recall": 1.0,
                "overall_issue_recall": 0.85,
                "verified_issue_precision": 0.9,
                "citation_accuracy": 1.0,
                "max_mixed_root_count": 0,
                "max_unsupported_verified_count": 0,
            },
            "cases": [{
                "id": "ANON-GOLD",
                "status": "approved",
                "report_type": "single",
                "source_paths": [str(source)],
                "gold_opinion_candidates": [],
                "approved_gold_path": str(gold_doc),
                "approved_gold_sha256": sha256(gold_doc),
                "expected_issues": [
                    {"id": "E1", "risk": "high", "drawing_ref": "A-01", "root_cause": "匿名根因1", "category": "消防"},
                    {"id": "E2", "risk": "normal", "drawing_ref": "A-02", "root_cause": "匿名根因2", "category": "设计深度"},
                ],
            }],
        }
        synthetic_results = {
            "cases": [{
                "case_id": "ANON-GOLD",
                "false_positive_count": 0,
                "mixed_root_count": 0,
                "unsupported_verified_count": 0,
                "findings": [
                    {"expected_issue_id": "E1", "outcome": "found", "verified": True, "citation_correct": True},
                    {"expected_issue_id": "E2", "outcome": "found", "verified": True, "citation_correct": True},
                ],
            }],
        }
        cases_path = temp / "synthetic-gold.json"
        results_path = temp / "synthetic-results.json"
        cases_path.write_text(json.dumps(synthetic_cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        results_path.write_text(json.dumps(synthetic_results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run(
            [python, str(SCRIPTS / "run_gold_evals.py"), "--cases", str(cases_path), "--results", str(results_path)],
            0,
            '"status": "pass"',
        )

    print("PASS: 14 v1.4 workflow and release-gate scenarios completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
