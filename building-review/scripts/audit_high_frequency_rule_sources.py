#!/usr/bin/env python3
"""Audit private high-frequency review sources against the public rule catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

OPINION_MARKER = re.compile(r"【\s*审查意见[^】]*】")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
DISPOSITIONS = {"new_rule", "merged", "held", "excluded"}
FORMAL_DISPOSITIONS = {"new_rule", "merged"}
NONFORMAL_DISPOSITIONS = {"held", "excluded"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def validate_catalog(catalog: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    rules = catalog.get("rules")
    if not isinstance(rules, list):
        return {}, ["catalog.rules must be a list"]
    rules_by_id: dict[str, dict[str, Any]] = {}
    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule, dict):
            errors.append(f"catalog rule {index} must be an object")
            continue
        rule_id = text(rule.get("rule_id"))
        if not rule_id:
            errors.append(f"catalog rule {index} has a blank rule_id")
            continue
        if rule_id in rules_by_id:
            errors.append(f"duplicate catalog rule_id: {rule_id}")
            continue
        rules_by_id[rule_id] = rule
        if rule.get("status") != "active":
            errors.append(f"{rule_id}: mapped catalogs may contain active rules only")
        mode = rule.get("authority_mode")
        basis = rule.get("basis")
        if mode == "normative":
            if not isinstance(basis, dict):
                errors.append(f"{rule_id}: normative rule basis must be an object")
                continue
            if basis.get("source_role") != "B_核心规范":
                errors.append(f"{rule_id}: normative rule is not backed by B_核心规范")
            for field in ("relative_path", "display_name", "article", "requirement"):
                if not text(basis.get(field)):
                    errors.append(f"{rule_id}: normative basis.{field} is blank")
            basis_hash = text(basis.get("sha256")).lower()
            if not SHA256.fullmatch(basis_hash):
                errors.append(f"{rule_id}: normative basis.sha256 is invalid")
            article = text(basis.get("article"))
            if "条" not in article:
                errors.append(f"{rule_id}: normative basis.article is not a precise clause")
        elif mode == "design_depth":
            if basis not in ({}, None):
                errors.append(f"{rule_id}: design-depth rule must not carry a technical basis")
        else:
            errors.append(f"{rule_id}: invalid authority_mode {mode!r}")
        forbidden = {"frequency", "frequency_count", "published_count"} & set(rule)
        if forbidden:
            errors.append(f"{rule_id}: frequency data must not be embedded in formal rules: {sorted(forbidden)}")
    declared = catalog.get("rule_count")
    if declared != len(rules):
        errors.append(f"catalog.rule_count is {declared}, actual count is {len(rules)}")
    return rules_by_id, errors


def validate_mapping(
    mapping: dict[str, Any],
    catalog: dict[str, Any],
    *,
    verify_source_files: bool = True,
) -> list[str]:
    errors: list[str] = []
    rules_by_id, catalog_errors = validate_catalog(catalog)
    errors.extend(catalog_errors)

    if mapping.get("schema_version") != "1.0":
        errors.append("mapping.schema_version must be 1.0")
    policy = mapping.get("policy")
    if not isinstance(policy, dict):
        errors.append("mapping.policy must be an object")
        policy = {}
    if policy.get("frequency_role") != "discovery_and_priority_only":
        errors.append("frequency_role must be discovery_and_priority_only")
    if policy.get("formal_authority") != "active_local_B_source_only":
        errors.append("formal_authority must be active_local_B_source_only")
    if policy.get("cross_period_counts_are_not_summed") is not True:
        errors.append("cross-period frequency counts must remain separate")
    if policy.get("public_distribution") is not False:
        errors.append("private source mapping must have public_distribution=false")

    sources = mapping.get("source_documents")
    if not isinstance(sources, list) or not sources:
        errors.append("source_documents must be a non-empty list")
        sources = []
    source_by_id: dict[str, dict[str, Any]] = {}
    source_marker_counts: dict[str, int] = {}
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            errors.append(f"source document {index} must be an object")
            continue
        source_id = text(source.get("source_id"))
        if not source_id or source_id in source_by_id:
            errors.append(f"source document {index} has a blank or duplicate source_id")
            continue
        source_by_id[source_id] = source
        for field in ("file_name", "absolute_path", "statistics_period"):
            if not text(source.get(field)):
                errors.append(f"{source_id}: source {field} is blank")
        source_hash = text(source.get("sha256")).lower()
        if not SHA256.fullmatch(source_hash):
            errors.append(f"{source_id}: source sha256 is invalid")
        page_count = source.get("page_count")
        if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count <= 0:
            errors.append(f"{source_id}: page_count must be a positive integer")
        if not verify_source_files:
            continue
        source_path = Path(text(source.get("absolute_path")))
        if not source_path.is_file():
            errors.append(f"{source_id}: source file is missing: {source_path}")
            continue
        if source_path.name != source.get("file_name"):
            errors.append(f"{source_id}: file_name does not match absolute_path")
        actual_hash = file_sha256(source_path)
        if actual_hash != source_hash:
            errors.append(f"{source_id}: sha256 mismatch: {actual_hash}")
        try:
            from pypdf import PdfReader

            reader = PdfReader(source_path)
            if len(reader.pages) != page_count:
                errors.append(f"{source_id}: page count is {len(reader.pages)}, expected {page_count}")
            source_marker_counts[source_id] = sum(
                len(OPINION_MARKER.findall(page.extract_text() or "")) for page in reader.pages
            )
        except Exception as error:
            errors.append(f"{source_id}: PDF inspection failed: {error}")

    frequency_entries = mapping.get("frequency_entries")
    if not isinstance(frequency_entries, list):
        errors.append("frequency_entries must be a list")
        frequency_entries = []
    frequency_ids: set[str] = set()
    frequency_keys: set[tuple[Any, ...]] = set()
    for index, entry in enumerate(frequency_entries, start=1):
        if not isinstance(entry, dict):
            errors.append(f"frequency entry {index} must be an object")
            continue
        frequency_id = text(entry.get("frequency_id"))
        if not frequency_id or frequency_id in frequency_ids:
            errors.append(f"frequency entry {index} has a blank or duplicate frequency_id")
        frequency_ids.add(frequency_id)
        source_id = text(entry.get("source_id"))
        source = source_by_id.get(source_id)
        if source is None:
            errors.append(f"{frequency_id}: unknown source_id {source_id}")
            continue
        page = entry.get("page")
        if not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= source["page_count"]:
            errors.append(f"{frequency_id}: page is outside the source document")
        if entry.get("statistics_period") != source.get("statistics_period"):
            errors.append(f"{frequency_id}: statistics_period differs from its source")
        count = entry.get("published_count")
        if count is not None and (
            not isinstance(count, int) or isinstance(count, bool) or count <= 0
        ):
            errors.append(f"{frequency_id}: published_count must be null or a positive integer")
        key = (
            source_id,
            page,
            entry.get("statistics_period"),
            text(entry.get("standard")),
            text(entry.get("article")),
        )
        if key in frequency_keys:
            errors.append(f"{frequency_id}: duplicate frequency row {key}")
        frequency_keys.add(key)
        disposition = entry.get("disposition")
        targets = entry.get("target_rule_ids")
        if disposition not in DISPOSITIONS:
            errors.append(f"{frequency_id}: invalid disposition {disposition!r}")
        if not isinstance(targets, list):
            errors.append(f"{frequency_id}: target_rule_ids must be a list")
            targets = []
        if disposition in FORMAL_DISPOSITIONS and not targets:
            errors.append(f"{frequency_id}: formal disposition requires target_rule_ids")
        for rule_id in targets:
            if rule_id not in rules_by_id:
                errors.append(f"{frequency_id}: dangling target rule_id {rule_id}")
        if disposition in NONFORMAL_DISPOSITIONS:
            if not text(entry.get("reason_code")) or not text(entry.get("reason")):
                errors.append(f"{frequency_id}: held/excluded entry requires a standardized reason")

    opinion_items = mapping.get("opinion_items")
    if not isinstance(opinion_items, list):
        errors.append("opinion_items must be a list")
        opinion_items = []
    item_ids: set[str] = set()
    item_locations: set[tuple[str, int, int]] = set()
    page_indexes: defaultdict[tuple[str, int], list[int]] = defaultdict(list)
    dispositions: Counter[str] = Counter()
    opinions_by_source: Counter[str] = Counter()
    for index, item in enumerate(opinion_items, start=1):
        if not isinstance(item, dict):
            errors.append(f"opinion item {index} must be an object")
            continue
        item_id = text(item.get("item_id"))
        if not item_id or item_id in item_ids:
            errors.append(f"opinion item {index} has a blank or duplicate item_id")
        item_ids.add(item_id)
        source_id = text(item.get("source_id"))
        source = source_by_id.get(source_id)
        if source is None:
            errors.append(f"{item_id}: unknown source_id {source_id}")
            continue
        opinions_by_source[source_id] += 1
        if text(item.get("source_sha256")).lower() != text(source.get("sha256")).lower():
            errors.append(f"{item_id}: source_sha256 differs from the source document")
        page = item.get("page")
        page_index = item.get("page_opinion_index")
        if not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= source["page_count"]:
            errors.append(f"{item_id}: page is outside the source document")
        if not isinstance(page_index, int) or isinstance(page_index, bool) or page_index <= 0:
            errors.append(f"{item_id}: page_opinion_index must be a positive integer")
        else:
            location = (source_id, page, page_index)
            if location in item_locations:
                errors.append(f"{item_id}: duplicate page opinion location {location}")
            item_locations.add(location)
            page_indexes[(source_id, page)].append(page_index)
        if item.get("statistics_period") != source.get("statistics_period"):
            errors.append(f"{item_id}: statistics_period differs from its source")
        for field in ("raw_opinion", "normalized_issue", "dedupe_key", "professional_boundary"):
            if not text(item.get(field)):
                errors.append(f"{item_id}: {field} is blank")
        if "【" not in text(item.get("marker")) or "审查意见" not in text(item.get("marker")):
            errors.append(f"{item_id}: marker is invalid")
        for frequency_id in item.get("frequency_entry_ids", []):
            if frequency_id not in frequency_ids:
                errors.append(f"{item_id}: unknown frequency_entry_id {frequency_id}")
        disposition = item.get("disposition")
        dispositions[str(disposition)] += 1
        if disposition not in DISPOSITIONS:
            errors.append(f"{item_id}: invalid disposition {disposition!r}")
        targets = item.get("target_rule_ids")
        if not isinstance(targets, list):
            errors.append(f"{item_id}: target_rule_ids must be a list")
            targets = []
        if disposition in FORMAL_DISPOSITIONS and not targets:
            errors.append(f"{item_id}: formal disposition requires target_rule_ids")
        if disposition in NONFORMAL_DISPOSITIONS:
            if targets:
                errors.append(f"{item_id}: held/excluded item must not have formal target_rule_ids")
            if not text(item.get("reason_code")) or not text(item.get("reason")):
                errors.append(f"{item_id}: held/excluded item requires a standardized reason")
        for rule_id in targets:
            rule = rules_by_id.get(rule_id)
            if rule is None:
                errors.append(f"{item_id}: dangling target rule_id {rule_id}")
                continue
            if rule.get("authority_mode") != "normative":
                continue
            basis = rule.get("basis", {})
            matches = [
                record
                for record in item.get("current_basis", [])
                if isinstance(record, dict) and record.get("rule_id") == rule_id
            ]
            if len(matches) != 1:
                errors.append(f"{item_id}: normative target {rule_id} needs one current_basis record")
                continue
            record = matches[0]
            for field in ("relative_path", "sha256", "article"):
                if text(record.get(field)).lower() != text(basis.get(field)).lower():
                    errors.append(f"{item_id}: current_basis {field} differs from catalog rule {rule_id}")
    for location, indexes in page_indexes.items():
        if sorted(indexes) != list(range(1, len(indexes) + 1)):
            errors.append(f"{location}: page_opinion_index values are not continuous")
    for source_id, marker_count in source_marker_counts.items():
        if marker_count != opinions_by_source[source_id]:
            errors.append(
                f"{source_id}: PDF has {marker_count} opinion markers, mapping has {opinions_by_source[source_id]}"
            )

    supplemental = mapping.get("supplemental_items")
    if not isinstance(supplemental, list):
        errors.append("supplemental_items must be a list")
        supplemental = []
    supplemental_ids: set[str] = set()
    for index, item in enumerate(supplemental, start=1):
        item_id = text(item.get("item_id")) if isinstance(item, dict) else ""
        if not item_id or item_id in supplemental_ids or item_id in item_ids:
            errors.append(f"supplemental item {index} has a blank or duplicate item_id")
        supplemental_ids.add(item_id)
        source_id = text(item.get("source_id")) if isinstance(item, dict) else ""
        source = source_by_id.get(source_id)
        if source is None:
            errors.append(f"{item_id}: supplemental item has unknown source_id {source_id}")
            continue
        page = item.get("page")
        if not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= source["page_count"]:
            errors.append(f"{item_id}: supplemental page is outside the source document")
        disposition = item.get("disposition")
        targets = item.get("target_rule_ids", [])
        if disposition not in DISPOSITIONS:
            errors.append(f"{item_id}: invalid supplemental disposition {disposition!r}")
        if disposition in FORMAL_DISPOSITIONS and not targets:
            errors.append(f"{item_id}: formal supplemental disposition requires target_rule_ids")
        if disposition in NONFORMAL_DISPOSITIONS and (
            not text(item.get("reason_code")) or not text(item.get("reason"))
        ):
            errors.append(f"{item_id}: held/excluded supplemental item requires a standardized reason")
        for rule_id in targets:
            if rule_id not in rules_by_id:
                errors.append(f"{item_id}: dangling supplemental target rule_id {rule_id}")

    summary = mapping.get("summary")
    if not isinstance(summary, dict):
        errors.append("mapping.summary must be an object")
        summary = {}
    expected_summary = {
        "source_document_count": len(sources),
        "rendered_page_count": sum(
            source.get("page_count", 0) for source in sources if isinstance(source, dict)
        ),
        "bracket_marker_count": len(opinion_items),
        "supplemental_visual_item_count": len(supplemental),
        "frequency_entry_count": len(frequency_entries),
        "opinion_dispositions": dict(sorted(dispositions.items())),
        "catalog_rule_count": len(rules_by_id),
        "catalog_normative_rule_count": sum(
            rule.get("authority_mode") == "normative" for rule in rules_by_id.values()
        ),
        "catalog_design_depth_rule_count": sum(
            rule.get("authority_mode") == "design_depth" for rule in rules_by_id.values()
        ),
    }
    for field, expected in expected_summary.items():
        if summary.get(field) != expected:
            errors.append(f"summary.{field} is {summary.get(field)!r}, expected {expected!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, required=True, help="Private source-to-rule mapping JSON")
    parser.add_argument("--catalog", type=Path, required=True, help="Generated review-rules.json")
    args = parser.parse_args()
    try:
        mapping = load_json(args.mapping)
        catalog = load_json(args.catalog)
    except Exception as error:
        print(f"FAIL: unable to read input JSON: {error}")
        return 1
    errors = validate_mapping(mapping, catalog, verify_source_files=True)
    if errors:
        print("FAIL: high-frequency source audit found errors")
        for error in errors:
            print(f"- {error}")
        return 1
    summary = mapping["summary"]
    print(
        "PASS: "
        f"{summary['source_document_count']} sources, "
        f"{summary['rendered_page_count']} pages, "
        f"{summary['bracket_marker_count']} opinion markers, "
        f"{summary['frequency_entry_count']} frequency rows, "
        f"{summary['catalog_rule_count']} catalog rules"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
