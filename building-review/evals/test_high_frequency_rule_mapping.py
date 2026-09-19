#!/usr/bin/env python3
"""Anonymous regression tests for high-frequency source-to-rule governance."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from audit_high_frequency_rule_sources import validate_mapping  # noqa: E402


def fixture() -> tuple[dict, dict]:
    normative = {
        "rule_id": "TEST-NORM-1",
        "status": "active",
        "authority_mode": "normative",
        "basis": {
            "source_role": "B_核心规范",
            "relative_path": "001测试/B测试核心规范/test.pdf",
            "sha256": "a" * 64,
            "display_name": "《匿名测试规范》GB 00000-2026",
            "article": "第1.0.1条",
            "requirement": "匿名测试要求。",
        },
    }
    design_depth = {
        "rule_id": "TEST-DEPTH-1",
        "status": "active",
        "authority_mode": "design_depth",
        "basis": {},
    }
    catalog = {
        "schema_version": "1.1",
        "catalog_version": "test",
        "rule_count": 2,
        "rules": [normative, design_depth],
    }
    mapping = {
        "schema_version": "1.0",
        "catalog_version": "test",
        "mapping_date": "2026-08-24",
        "policy": {
            "frequency_role": "discovery_and_priority_only",
            "formal_authority": "active_local_B_source_only",
            "cross_period_counts_are_not_summed": True,
            "public_distribution": False,
        },
        "source_documents": [
            {
                "source_id": "HF-TEST",
                "file_name": "anonymous.pdf",
                "absolute_path": "X:/private/anonymous.pdf",
                "sha256": "b" * 64,
                "page_count": 1,
                "statistics_period": "匿名期间",
            }
        ],
        "frequency_entries": [
            {
                "frequency_id": "HF-TEST-F001",
                "source_id": "HF-TEST",
                "page": 1,
                "statistics_period": "匿名期间",
                "standard": "GB 00000-2026",
                "article": "1.0.1",
                "published_count": 3,
                "disposition": "merged",
                "target_rule_ids": ["TEST-NORM-1"],
                "reason_code": "current_b_rule_mapped",
                "reason": "匿名频次只用于发现和排序。",
            }
        ],
        "opinion_items": [
            {
                "item_id": "HF-TEST-P001-O01",
                "source_id": "HF-TEST",
                "source_sha256": "b" * 64,
                "page": 1,
                "page_opinion_index": 1,
                "marker": "【审查意见-1】",
                "statistics_period": "匿名期间",
                "raw_opinion": "【审查意见-1】匿名意见。",
                "cited_standards": ["GB 00000-2026"],
                "cited_articles": ["1.0.1"],
                "frequency_entry_ids": ["HF-TEST-F001"],
                "normalized_issue": "匿名规范化问题。",
                "dedupe_key": "TEST-NORM-1",
                "professional_boundary": "architecture",
                "disposition": "new_rule",
                "target_rule_ids": ["TEST-NORM-1"],
                "candidate_rule_ids": [],
                "reason_code": "mapped_to_atomic_rule",
                "reason": "匿名映射。",
                "current_basis": [
                    {
                        "rule_id": "TEST-NORM-1",
                        "relative_path": "001测试/B测试核心规范/test.pdf",
                        "sha256": "a" * 64,
                        "article": "第1.0.1条",
                    }
                ],
            }
        ],
        "supplemental_items": [
            {
                "item_id": "HF-TEST-P001-S01",
                "source_id": "HF-TEST",
                "page": 1,
                "description": "匿名图像案例。",
                "disposition": "merged",
                "target_rule_ids": ["TEST-DEPTH-1"],
                "reason_code": "visual_reference_mapped",
                "reason": "匿名归并。",
            }
        ],
        "summary": {
            "source_document_count": 1,
            "rendered_page_count": 1,
            "bracket_marker_count": 1,
            "supplemental_visual_item_count": 1,
            "frequency_entry_count": 1,
            "opinion_dispositions": {"new_rule": 1},
            "catalog_rule_count": 2,
            "catalog_normative_rule_count": 1,
            "catalog_design_depth_rule_count": 1,
        },
    }
    return mapping, catalog


def expect_error(mapping: dict, catalog: dict, fragment: str) -> None:
    errors = validate_mapping(mapping, catalog, verify_source_files=False)
    if not any(fragment in error for error in errors):
        raise AssertionError(f"expected error containing {fragment!r}, got {errors}")


def main() -> int:
    mapping, catalog = fixture()
    errors = validate_mapping(mapping, catalog, verify_source_files=False)
    if errors:
        raise AssertionError(f"valid anonymous fixture failed: {errors}")

    duplicate = copy.deepcopy(mapping)
    duplicate["opinion_items"].append(copy.deepcopy(duplicate["opinion_items"][0]))
    expect_error(duplicate, catalog, "duplicate item_id")

    dangling = copy.deepcopy(mapping)
    dangling["opinion_items"][0]["target_rule_ids"] = ["MISSING-RULE"]
    expect_error(dangling, catalog, "dangling target rule_id")

    unreasoned = copy.deepcopy(mapping)
    item = unreasoned["opinion_items"][0]
    item.update(disposition="held", target_rule_ids=[], reason_code="", reason="")
    unreasoned["summary"]["opinion_dispositions"] = {"held": 1}
    expect_error(unreasoned, catalog, "requires a standardized reason")

    non_b_catalog = copy.deepcopy(catalog)
    non_b_catalog["rules"][0]["basis"]["source_role"] = "A_审查要点"
    expect_error(mapping, non_b_catalog, "not backed by B_核心规范")

    frequency_authority = copy.deepcopy(catalog)
    frequency_authority["rules"][0]["published_count"] = 3
    expect_error(mapping, frequency_authority, "frequency data must not be embedded")

    summed_periods = copy.deepcopy(mapping)
    summed_periods["policy"]["cross_period_counts_are_not_summed"] = False
    expect_error(summed_periods, catalog, "must remain separate")

    print("PASS: 6 anonymous high-frequency mapping governance scenarios completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
