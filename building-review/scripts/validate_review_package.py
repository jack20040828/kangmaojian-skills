#!/usr/bin/env python3
"""Validate building-review evidence, integrity, and ledgers before Word generation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from struct import unpack

from review_rules import (
    REQUIRED_RULE_PACKS,
    applicable_rules,
    condition_state,
    evaluate_trigger,
    load_catalog,
    load_profile,
)

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_RULE_CATALOG = SKILL_DIR / "generated" / "review-rules.json"

REQUIRED_FILES = [
    "drawing_inventory.csv",
    "fact_ledger.csv",
    "check_matrix.csv",
    "issue_candidates.csv",
    "validation_log.csv",
]
V15_REQUIRED_FILES = [
    "graphic_evidence_chain.csv",
    "applicability_decisions.csv",
    "independent_review_log.csv",
]
V16_REQUIRED_FILES = [
    "graphic_evidence_chain.csv",
    "applicability_decisions.csv",
]

VALID_OPINION_TYPES = {
    "消防安全强制性条文，必须修改（消防安全）",
    "一般性条文，必须修改（消防安全）",
    "政策规定，必须修改（消防安全）",
    "设计深度，必须修改（消防安全）",
    "其它强制性条文，必须修改（其它）",
    "其它强制性条文，建议修改（其它）",
    "一般性条文，必须修改（其它）",
    "一般性条文，建议修改（其它）",
    "政策规定，必须修改（其它）",
    "政策规定，建议修改（其它）",
    "设计深度，必须修改（其它）",
    "设计深度，建议修改（其它）",
}

VALID_ISSUE_STATUSES = {"verified", "ai_ready", "needs_review", "rejected", "delete"}
VALID_APPLICABILITY = {"适用", "不适用", "需判断"}
VALID_CONCLUSIONS = {"符合", "不符合", "需核验", "不适用"}
VALID_SCREENSHOT_STRATEGIES = {"none", "single", "multiple", "shared"}
SCREENSHOT_REQUIRED_STRATEGIES = {"single", "multiple", "shared"}
SUPPORTED_SCHEMA_VERSIONS = {"1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7"}
VALID_REVIEW_FAMILIES = {
    "设计说明",
    "目录索引",
    "平面图",
    "屋面图",
    "立面图",
    "剖面图",
    "楼梯大样",
    "墙身大样",
    "其他大样",
    "门窗表",
    "材料做法表",
    "总图设计说明",
    "总平面图",
    "竖向设计图",
    "交通消防图",
    "其他总图",
    "其他",
}
VALID_REVIEW_STATUSES = {"reviewed", "not_applicable", "needs_review"}
VALID_CITATION_MODES = {"cited", "none"}
VALID_EVIDENCE_CLASSES = {
    "identity_text",
    "numeric",
    "location",
    "relationship",
    "graphic",
    "detail",
    "performance",
    "absence_chain",
    "not_applicable",
}
GENERIC_CLOSURE_PATTERNS = (
    "已提供",
    "均已提供",
    "可识别",
    "覆盖完整",
    "大样覆盖",
    "图纸齐全",
    "列有",
    "可对应",
    "表达完整",
    "均已核对",
)
NON_APPLICABILITY_FACT_MARKERS = (
    "既有建筑",
    "改造项目",
    "非新建建筑",
    "地上1层",
    "地上2层",
    "少于3层",
    "不足3层",
    "无第三层",
    "坡屋面",
    "防水等级为二级",
    "非一级防水",
    "现浇混凝土外墙",
    "非砌体外墙",
    "非填充墙外墙",
    "不设阳台",
    "无临空部位",
    "不含卧室",
    "不含起居室",
    "不属于住宅层",
    "条文适用范围",
)
DESIGN_DEPTH_OPINION_TYPES = {
    "设计深度，必须修改（消防安全）",
    "设计深度，必须修改（其它）",
    "设计深度，建议修改（其它）",
}
V11_ISSUE_FIELDS = {
    "display_order",
    "report_section",
    "screenshot_strategy",
    "screenshot_reason",
    "screenshot_count",
    "evidence_point",
    "red_box_target",
    "context_required",
    "screenshot_quality",
}
LEGACY_NEW_ISSUE_FIELDS = V11_ISSUE_FIELDS - {"display_order", "report_section"}
V11_GATE_FIELDS = {
    "professional_filter_check",
    "screenshot_strategy_check",
    "red_box_precision_check",
}
V12_INVENTORY_FIELDS = {"review_family", "review_status", "review_check_ids", "review_notes"}
V13_CHECK_FIELDS = {"review_item_id", "coverage_topic", "evidence_class"}
V14_CHECK_FIELDS = V13_CHECK_FIELDS | {
    "rule_id",
    "atomic_check_id",
    "decision_state",
    "discovery_track",
    "applicability_basis",
    "comparison_method",
    "comparison_record",
    "calculation_record",
    "open_reason",
    "reviewer_gate",
}
V15_CHECK_FIELDS = V14_CHECK_FIELDS | {
    "graphic_claim_type",
    "graphic_chain_ids",
    "graphic_gate_reason",
    "applicability_decision_ids",
    "independent_review_id",
}
V16_CHECK_FIELDS = (V15_CHECK_FIELDS - {"independent_review_id", "reviewer_gate"}) | {"completion_gate"}
V15_GRAPHIC_FIELDS = {
    "chain_id", "check_id", "evidence_role", "source_file", "page", "drawing_ref",
    "location", "graphic_element", "observed_fact", "interpretation",
    "alternative_interpretation", "elimination_basis", "fact_ids", "screenshot_path",
    "source_quality", "status", "reviewer_name", "reviewed_at", "notes",
}
V15_APPLICABILITY_FIELDS = {
    "decision_id", "check_id", "rule_id", "condition_id", "condition_description",
    "expected_value", "actual_value", "result", "fact_ids", "drawing_refs", "status",
    "reviewer_name", "reviewed_at", "notes",
}
V16_GRAPHIC_FIELDS = (V15_GRAPHIC_FIELDS - {"reviewer_name", "reviewed_at"}) | {"completed_at"}
V16_APPLICABILITY_FIELDS = (V15_APPLICABILITY_FIELDS - {"reviewer_name", "reviewed_at"}) | {"completed_at"}
V15_INDEPENDENT_FIELDS = {
    "review_id", "check_id", "primary_reviewer", "primary_reviewer_type",
    "primary_decision", "primary_reviewed_at", "secondary_reviewer",
    "secondary_reviewer_type", "secondary_decision", "secondary_reviewed_at",
    "blind_input_scope", "agreement", "adjudicator", "adjudicator_type",
    "adjudicated_decision", "adjudicated_at", "status", "notes",
}
VALID_GRAPHIC_CLAIM_TYPES = {
    "pending", "none", "dimension", "direction", "symbol", "absence",
    "cross_sheet", "detail", "location",
}
AMBIGUITY_SENSITIVE_CLAIMS = {"direction", "symbol", "absence", "cross_sheet"}
VALID_GRAPHIC_SOURCE_QUALITY = {"vector", "raster_high", "raster_limited"}
VALID_GRAPHIC_STATUSES = {"unreviewed", "resolved", "needs_review"}
VALID_APPLICABILITY_RESULTS = {"met", "not_met", "unknown"}
VALID_APPLICABILITY_STATUSES = {"unreviewed", "resolved", "needs_review"}
VALID_REVIEWER_TYPES = {"human", "agent"}
VALID_INDEPENDENT_STATUSES = {"agreed", "adjudicated", "needs_review"}
V12_ISSUE_FIELDS = V11_ISSUE_FIELDS | {
    "citation_mode",
    "standard_display_name",
    "citation_none_reason",
}
V12_GATE_FIELDS = V11_GATE_FIELDS | {
    "graphical_interpretation_check",
    "opinion_wording_check",
}
V14_GATE_FIELDS = V12_GATE_FIELDS | {"evidence_chain_check", "independent_review_check"}
V16_GATE_FIELDS = V12_GATE_FIELDS | {"evidence_chain_check"}
LEGACY_GATE_FIELDS = V11_GATE_FIELDS | {"layout_check"}
VALID_SECTIONS = {
    "single": {"设计说明", "平面图", "立面剖面图", "大样图"},
    "site": {"总图设计说明", "总图设计图纸"},
}

FAMILY_REQUIRED_TOPICS = {
    "目录索引": {"document_traceability"},
    "设计说明": {"project_identity_function", "project_scope_consistency", "code_basis_consistency"},
    "平面图": {"function_layout", "fire_egress", "accessibility", "wet_room_hygiene", "safety_coordination"},
    "屋面图": {"roof_drainage", "roof_fall_protection", "roof_access", "renewable_energy_safety"},
    "立面图": {"height_elevation", "openings_rescue", "facade_safety_weather"},
    "剖面图": {"height_clearance", "vertical_relationship", "roof_guard"},
    "楼梯大样": {"stair_geometry", "stair_guard", "roof_exit"},
    "墙身大样": {"detail_traceability", "window_sill_drainage", "parapet_flashing", "waterproofing_detail"},
    "其他大样": {"detail_traceability", "wet_room_drainage", "accessibility_detail", "detail_implementability"},
    "门窗表": {"door_window_identity", "fire_rescue_openings", "door_window_safety"},
    "材料做法表": {"project_applicability", "material_performance", "cross_drawing_consistency"},
    "总图设计说明": {"project_identity_function", "project_scope_consistency", "code_basis_consistency", "site_design_parameters"},
    "总平面图": {"site_accessible_route", "parking_special_spaces", "site_fire_access", "site_function_space"},
    "竖向设计图": {"site_vertical_drainage", "accessible_route_gradient", "site_elevation_relationship"},
    "交通消防图": {"site_fire_access", "parking_special_spaces", "pedestrian_vehicle_relationship"},
    "其他总图": {"site_function_space", "site_accessible_route"},
    "其他": {"document_traceability"},
}

FUNCTION_TRIGGER_TOPICS = [
    (("宿舍", "旅馆", "酒店"), {"single": {"dormitory_refuse", "dormitory_acoustics", "accessible_room", "accessible_room_detail"}, "site": {"site_assembly_space"}}),
    (("食堂", "餐厅", "厨房", "备餐", "洗消"), {"single": {"food_wet_room_vertical"}}),
    (("电梯",), {"single": {"accessible_elevator"}}),
    (("光伏", "太阳能"), {"single": {"renewable_energy_safety"}}),
    (("停车", "车位"), {"site": {"parking_special_spaces"}}),
]

TOPIC_EVIDENCE_CLASSES = {
    "document_traceability": {"identity_text", "relationship", "absence_chain"},
    "project_identity_function": {"identity_text", "relationship", "absence_chain"},
    "project_scope_consistency": {"identity_text", "relationship", "absence_chain"},
    "code_basis_consistency": {"identity_text", "relationship", "absence_chain"},
    "function_layout": {"location", "relationship", "numeric", "absence_chain"},
    "fire_egress": {"numeric", "location", "relationship", "graphic", "absence_chain"},
    "accessibility": {"numeric", "location", "relationship", "detail", "absence_chain"},
    "wet_room_hygiene": {"location", "relationship", "detail", "absence_chain"},
    "safety_coordination": {"numeric", "location", "relationship", "graphic", "detail", "absence_chain"},
    "roof_fall_protection": {"numeric", "location", "detail", "absence_chain"},
    "roof_access": {"location", "relationship", "detail", "absence_chain"},
    "height_elevation": {"numeric", "relationship", "absence_chain"},
    "openings_rescue": {"numeric", "location", "relationship", "detail", "absence_chain"},
    "facade_safety_weather": {"detail", "performance", "relationship", "absence_chain"},
    "height_clearance": {"numeric", "relationship", "absence_chain"},
    "vertical_relationship": {"numeric", "relationship", "absence_chain"},
    "roof_guard": {"numeric", "detail", "relationship", "absence_chain"},
    "stair_geometry": {"numeric", "detail", "relationship", "absence_chain"},
    "stair_guard": {"numeric", "detail", "relationship", "absence_chain"},
    "roof_exit": {"location", "relationship", "detail", "absence_chain"},
    "detail_traceability": {"identity_text", "relationship", "detail", "absence_chain"},
    "food_wet_room_vertical": {"relationship"},
    "dormitory_refuse": {"location", "absence_chain"},
    "dormitory_acoustics": {"relationship", "performance", "absence_chain"},
    "accessible_room": {"location", "numeric", "absence_chain"},
    "accessible_room_detail": {"detail", "absence_chain"},
    "accessible_elevator": {"detail", "performance", "absence_chain"},
    "site_assembly_space": {"location", "numeric", "absence_chain"},
    "site_accessible_route": {"location", "relationship", "absence_chain"},
    "parking_special_spaces": {"location", "numeric", "absence_chain"},
    "roof_drainage": {"location", "relationship", "detail", "absence_chain"},
    "renewable_energy_safety": {"location", "relationship", "detail", "absence_chain"},
    "window_sill_drainage": {"detail", "relationship", "absence_chain"},
    "parapet_flashing": {"detail", "relationship", "absence_chain"},
    "waterproofing_detail": {"detail", "performance", "absence_chain"},
    "wet_room_waterproofing": {"numeric", "detail", "performance", "relationship", "absence_chain"},
    "exterior_wall_waterproofing": {"numeric", "detail", "performance", "relationship", "absence_chain"},
    "roof_waterproofing": {"numeric", "location", "detail", "performance", "relationship", "absence_chain"},
    "wet_room_drainage": {"location", "detail", "absence_chain"},
    "accessibility_detail": {"numeric", "detail", "relationship", "absence_chain"},
    "detail_implementability": {"numeric", "detail", "performance", "relationship", "absence_chain"},
    "door_window_identity": {"identity_text", "relationship", "absence_chain"},
    "fire_rescue_openings": {"numeric", "location", "detail", "absence_chain"},
    "door_window_safety": {"numeric", "detail", "performance", "relationship", "absence_chain"},
    "project_applicability": {"identity_text", "relationship", "performance", "absence_chain"},
    "material_performance": {"identity_text", "performance", "detail", "absence_chain"},
    "cross_drawing_consistency": {"identity_text", "relationship", "absence_chain"},
    "site_design_parameters": {"numeric", "identity_text", "relationship", "absence_chain"},
    "site_fire_access": {"numeric", "location", "relationship", "graphic", "absence_chain"},
    "site_function_space": {"numeric", "location", "relationship", "absence_chain"},
    "site_vertical_drainage": {"numeric", "location", "relationship", "detail", "absence_chain"},
    "accessible_route_gradient": {"numeric", "location", "relationship", "absence_chain"},
    "site_elevation_relationship": {"numeric", "relationship", "absence_chain"},
    "pedestrian_vehicle_relationship": {"location", "relationship", "graphic", "absence_chain"},
}
VALID_DECISION_STATES = {"unreviewed", "resolved", "needs_review"}
VALID_DISCOVERY_TRACKS = {"technical_compliance", "design_depth", "optimization"}
PROFILE_FACT_KEYS = {
    "location_province", "location_city", "building_use", "industrial_building",
    "overnight_stay", "gross_floor_area_m2", "building_height_m", "floors_above",
    "floors_below", "fire_hazard_class", "fire_resistance_rating", "occupant_load",
    "sprinkler", "basement", "elevator", "accessible_requirement", "roof_accessible",
    "wet_rooms", "parking", "photovoltaic_or_solar", "food_service",
    "dormitory_or_hotel", "school", "office", "children_activity",
}
IGNORED_NAMES = {".DS_Store", "Thumbs.db"}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fieldnames(path: Path) -> set[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return set(csv.DictReader(handle).fieldnames or [])


def present(value: str | None) -> bool:
    return bool((value or "").strip())


def split_values(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").replace(";", ",").split(",") if item.strip()]


def resolve_paths(root: Path, value: str | None) -> list[Path]:
    resolved: list[Path] = []
    for item in split_values(value):
        path = Path(item)
        resolved.append(path if path.is_absolute() else root / path)
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ignored(path: Path) -> bool:
    return path.name in IGNORED_NAMES or path.name.startswith("~$")


def image_size(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()[:32]
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        with path.open("rb") as handle:
            handle.read(2)
            while True:
                marker_start = handle.read(1)
                if not marker_start:
                    return None
                if marker_start != b"\xff":
                    continue
                marker = handle.read(1)
                while marker == b"\xff":
                    marker = handle.read(1)
                if marker in {b"\xc0", b"\xc1", b"\xc2", b"\xc3"}:
                    length = unpack(">H", handle.read(2))[0]
                    segment = handle.read(length - 2)
                    if len(segment) >= 5:
                        height, width = unpack(">HH", segment[1:5])
                        return width, height
                    return None
                if marker in {b"\xd8", b"\xd9"}:
                    continue
                length_bytes = handle.read(2)
                if len(length_bytes) != 2:
                    return None
                length = unpack(">H", length_bytes)[0]
                handle.seek(length - 2, 1)
    return None


def duplicate_ids(items: list[dict[str, str]], field: str) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        value = item.get(field, "").strip()
        if not value:
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def path_key(value: str) -> str:
    return str(Path(value)).replace("/", "\\").casefold()


def resolve_index_entry(source: str, entries: list[dict]) -> tuple[dict | None, str | None]:
    source_key = path_key(source)
    absolute = [item for item in entries if path_key(item.get("absolute_path", "")) == source_key]
    if len(absolute) == 1:
        return absolute[0], None
    relative = [item for item in entries if path_key(item.get("relative_path", "")) == source_key]
    if len(relative) == 1:
        return relative[0], None
    name = Path(source).name.casefold()
    by_name = [item for item in entries if item.get("name", "").casefold() == name]
    if len(by_name) == 1:
        return by_name[0], None
    if len(by_name) > 1:
        return None, f"standard source is ambiguous: {source}"
    return None, f"standard source not found in knowledge index: {source}"


def load_manifest(root: Path) -> tuple[str, dict]:
    path = root / "review_manifest.json"
    if not path.exists():
        return "", {}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "", {"_invalid": True}
    version = str(manifest.get("schema_version", ""))
    return version if version in SUPPORTED_SCHEMA_VERSIONS else "", manifest


def validate_integrity(
    root: Path,
    manifest: dict,
    verified: list[dict[str, str]],
    checks: list[dict[str, str]],
    schema_version: str,
) -> list[str]:
    errors: list[str] = []
    expected_records = manifest.get("source_integrity")
    if not isinstance(expected_records, list) or not expected_records:
        errors.append("source_integrity is empty; run snapshot_review_integrity.py")
        expected_records = []
    expected = {item.get("path", ""): item for item in expected_records if item.get("path")}
    source_dir = root / "source"
    actual_paths = {
        path.relative_to(root).as_posix(): path
        for path in source_dir.rglob("*")
        if path.is_file() and not ignored(path)
    } if source_dir.exists() else {}
    for relative in sorted(expected.keys() - actual_paths.keys()):
        errors.append(f"registered source is missing: {relative}")
    for relative in sorted(actual_paths.keys() - expected.keys()):
        errors.append(f"unregistered source file: {relative}")
    for relative in sorted(expected.keys() & actual_paths.keys()):
        path = actual_paths[relative]
        record = expected[relative]
        if path.stat().st_size != record.get("size_bytes") or sha256_file(path) != record.get("sha256"):
            errors.append(f"source file changed after snapshot: {relative}")

    snapshot = manifest.get("knowledge_snapshot")
    if not isinstance(snapshot, dict) or not snapshot.get("corpus_sha256"):
        errors.append("knowledge_snapshot is missing; run snapshot_review_integrity.py")
        return errors
    if schema_version in {"1.6", "1.7"}:
        required_layers = snapshot.get("required_layers")
        if required_layers != ["A", "B", "C", "D"]:
            errors.append("v1.6 knowledge_snapshot.required_layers must be A, B, C, D")
        layers = snapshot.get("layers")
        if not isinstance(layers, dict):
            errors.append("v1.6 knowledge_snapshot.layers must record A/B/C/D usage")
        else:
            for layer in ["A", "B", "C", "D"]:
                record = layers.get(layer, {})
                if not isinstance(record, dict) or record.get("status") != "used":
                    errors.append(f"v1.6 knowledge layer {layer} is not marked used")
                    continue
                if not isinstance(record.get("sources"), list) or not record.get("sources"):
                    errors.append(f"v1.6 knowledge layer {layer} requires source records")
                if not str(record.get("notes", "")).strip():
                    errors.append(f"v1.6 knowledge layer {layer} requires usage notes")
    index_path = Path(snapshot.get("index_path", ""))
    if not index_path.exists():
        errors.append(f"snapshotted knowledge index is missing: {index_path}")
        return errors
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        errors.append(f"knowledge index is invalid JSON: {index_path}")
        return errors
    if index.get("corpus_sha256") != snapshot.get("corpus_sha256"):
        errors.append("knowledge corpus changed after snapshot")
    if sha256_file(index_path) != snapshot.get("index_sha256"):
        if index.get("corpus_sha256") == snapshot.get("corpus_sha256"):
            pass
        else:
            errors.append("knowledge index changed after snapshot")
    index_entries = index.get("files", [])
    entries = {item.get("relative_path", ""): item for item in index_entries}
    used = snapshot.get("used_standards", [])
    used_map = {item.get("relative_path", ""): item for item in used if item.get("relative_path")}
    cited_records = [
        (
            issue.get("issue_id", "").strip() or "[missing issue_id]",
            issue.get("standard_source", "").strip(),
        )
        for issue in verified
        if schema_version not in {"1.2", "1.3", "1.4", "1.5", "1.6", "1.7"}
        or issue.get("citation_mode", "").strip().lower() == "cited"
    ]
    if schema_version in {"1.4", "1.5", "1.6", "1.7"}:
        cited_records.extend(
            (
                check.get("check_id", "").strip() or "[missing check_id]",
                check.get("standard_source", "").strip(),
            )
            for check in checks
            if check.get("decision_state", "").strip() == "resolved"
            and check.get("discovery_track", "").strip() in {"technical_compliance", "optimization"}
            and check.get("conclusion", "").strip() in {"符合", "不符合"}
        )
    cited_records = [(label, source) for label, source in cited_records if source]
    if cited_records and not used_map:
        errors.append("knowledge_snapshot has no standards for verified issues or resolved technical checks")
    for label, source in cited_records:
        entry, error = resolve_index_entry(source, index_entries)
        if error:
            errors.append(f"{label}: {error}")
            continue
        assert entry is not None
        if entry.get("relative_path", "") not in used_map:
            errors.append(f"{label}: standard_source is not present in knowledge_snapshot.used_standards")
    for relative, record in used_map.items():
        entry = entries.get(relative)
        if not entry:
            errors.append(f"used standard is absent from current index: {relative}")
            continue
        path = Path(entry.get("absolute_path", ""))
        if not path.exists():
            errors.append(f"used standard file is missing: {relative}")
            continue
        if path.stat().st_size != record.get("size_bytes") or sha256_file(path) != record.get("sha256"):
            errors.append(f"used standard changed after snapshot: {relative}")
    return errors


def fact_matches_inventory(fact: dict[str, str], inventory: list[dict[str, str]]) -> bool:
    source = fact.get("source_file", "").strip().casefold()
    candidates = [row for row in inventory if row.get("source_file", "").strip().casefold() == source]
    if not candidates:
        return False
    drawing_no = fact.get("drawing_no", "").strip().casefold()
    if drawing_no and any(row.get("drawing_no", "").strip() for row in candidates):
        candidates = [row for row in candidates if row.get("drawing_no", "").strip().casefold() == drawing_no]
    page = fact.get("page", "").strip().casefold()
    if page and candidates and any(row.get("page", "").strip() for row in candidates):
        candidates = [row for row in candidates if row.get("page", "").strip().casefold() == page]
    return bool(candidates)


def fact_matches_drawing(fact: dict[str, str], drawing: dict[str, str]) -> bool:
    drawing_no = drawing.get("drawing_no", "").strip().casefold()
    if drawing_no and fact.get("drawing_no", "").strip().casefold() == drawing_no:
        return True
    drawing_name = drawing.get("drawing_name", "").strip().casefold()
    if drawing_name and fact.get("drawing_name", "").strip().casefold() == drawing_name:
        return True
    source = drawing.get("source_file", "").strip().casefold()
    page = drawing.get("page", "").strip().casefold()
    return bool(
        source
        and page
        and fact.get("source_file", "").strip().casefold() == source
        and fact.get("page", "").strip().casefold() == page
    )


def check_references_drawing(check: dict[str, str], drawing: dict[str, str]) -> bool:
    refs = check.get("drawing_refs", "").strip().casefold()
    return any(
        value and value.casefold() in refs
        for value in (drawing.get("drawing_no", "").strip(), drawing.get("drawing_name", "").strip())
    )


def generic_presence_only(check: dict[str, str], facts_by_id: dict[str, dict[str, str]]) -> bool:
    if check.get("conclusion", "").strip() != "符合":
        return False
    linked_facts = [facts_by_id.get(fact_id) for fact_id in split_values(check.get("fact_ids"))]
    evidence = " ".join(
        [
            check.get("actual_fact", ""),
            check.get("not_forming_reason", ""),
            *(fact.get("raw_text_or_measure", "") for fact in linked_facts if fact),
        ]
    )
    if not any(pattern in evidence for pattern in GENERIC_CLOSURE_PATTERNS):
        return False
    substantive = re.search(r"\d", evidence) or any(
        marker in evidence
        for marker in ("净宽", "净高", "坡度", "数量", "位置", "标高", "图号", "房间", "防火分区", "相邻", "上层", "下层")
    )
    return not substantive


def invalid_absence_not_applicable(check: dict[str, str], rule: dict) -> bool:
    if rule.get("absence_is_noncompliant") is not True:
        return False
    if check.get("applicability", "").strip() != "不适用" or check.get("conclusion", "").strip() != "不适用":
        return False
    basis = check.get("applicability_basis", "").strip()
    if any(marker in basis for marker in NON_APPLICABILITY_FACT_MARKERS):
        return False
    return True


def validate_required_rule_packs(
    catalog: dict,
    profile: dict,
    checks: list[dict[str, str]],
    report_type: str,
) -> list[str]:
    if report_type != "single":
        return []
    residential_state = condition_state(profile, {"field": "building_use", "contains": ["住宅"]})
    if residential_state == "inactive":
        return []
    errors: list[str] = []
    rules_by_id = {
        str(rule.get("rule_id", "")).strip(): rule
        for rule in catalog.get("rules", [])
        if str(rule.get("rule_id", "")).strip()
    }
    checks_by_rule: dict[str, list[dict[str, str]]] = {}
    for check in checks:
        checks_by_rule.setdefault(check.get("rule_id", "").strip(), []).append(check)
    for pack_id, required_ids in REQUIRED_RULE_PACKS.items():
        missing_catalog = sorted(required_ids - set(rules_by_id))
        if missing_catalog:
            errors.append(
                f"required rule pack {pack_id} is incomplete in the snapshotted catalog: "
                f"{', '.join(missing_catalog)}"
            )
        expected_ids = {
            rule_id
            for rule_id in required_ids & set(rules_by_id)
            if report_type in rules_by_id[rule_id].get("report_types", [])
            and evaluate_trigger(rules_by_id[rule_id].get("trigger", {}), profile) != "inactive"
        }
        missing_checks = sorted(rule_id for rule_id in expected_ids if not checks_by_rule.get(rule_id))
        if missing_checks:
            errors.append(
                f"required rule pack {pack_id} has no atomic check for: {', '.join(missing_checks)}"
            )
        unresolved = sorted(
            rule_id
            for rule_id in expected_ids
            if checks_by_rule.get(rule_id)
            and any(check.get("decision_state", "").strip() != "resolved" for check in checks_by_rule[rule_id])
        )
        if unresolved:
            errors.append(
                f"required rule pack {pack_id} remains unresolved: {', '.join(unresolved)}"
            )
    return errors


def valid_iso_datetime(value: str | None) -> bool:
    try:
        datetime.fromisoformat((value or "").strip())
        return True
    except ValueError:
        return False


def rule_expected_text(value) -> str:
    if isinstance(value, (dict, list, bool, int, float)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def validate_v15_professional_gates(
    root: Path,
    checks: list[dict[str, str]],
    rules_by_id: dict[str, dict],
    fact_ids: set[str],
    graphic_rows: list[dict[str, str]],
    applicability_rows: list[dict[str, str]],
    independent_rows: list[dict[str, str]],
    ai_initial: bool = False,
) -> list[str]:
    errors: list[str] = []
    check_ids = {row.get("check_id", "").strip() for row in checks if present(row.get("check_id"))}
    graphics_by_id = {
        row.get("chain_id", "").strip(): row
        for row in graphic_rows
        if present(row.get("chain_id"))
    }
    applicability_by_id = {
        row.get("decision_id", "").strip(): row
        for row in applicability_rows
        if present(row.get("decision_id"))
    }
    independent_by_id = {
        row.get("review_id", "").strip(): row
        for row in independent_rows
        if present(row.get("review_id"))
    }

    for row in graphic_rows:
        chain_id = row.get("chain_id", "").strip() or "[missing chain_id]"
        if row.get("check_id", "").strip() not in check_ids:
            errors.append(f"{chain_id}: graphic evidence check_id not found")
        status = row.get("status", "").strip()
        if status not in VALID_GRAPHIC_STATUSES:
            errors.append(f"{chain_id}: invalid graphic evidence status: {status}")
        quality = row.get("source_quality", "").strip()
        if quality and quality not in VALID_GRAPHIC_SOURCE_QUALITY:
            errors.append(f"{chain_id}: invalid graphic source_quality: {quality}")

    for row in applicability_rows:
        decision_id = row.get("decision_id", "").strip() or "[missing decision_id]"
        if row.get("check_id", "").strip() not in check_ids:
            errors.append(f"{decision_id}: applicability check_id not found")
        status = row.get("status", "").strip()
        if status not in VALID_APPLICABILITY_STATUSES:
            errors.append(f"{decision_id}: invalid applicability status: {status}")
        result = row.get("result", "").strip()
        if result not in VALID_APPLICABILITY_RESULTS:
            errors.append(f"{decision_id}: invalid applicability result: {result}")

    for row in independent_rows:
        review_id = row.get("review_id", "").strip() or "[missing review_id]"
        if row.get("check_id", "").strip() not in check_ids:
            errors.append(f"{review_id}: independent review check_id not found")

    for check in checks:
        check_id = check.get("check_id", "").strip() or "[missing check_id]"
        if check.get("decision_state", "").strip() != "resolved":
            continue
        rule_id = check.get("rule_id", "").strip()
        rule = rules_by_id.get(rule_id)
        if not rule:
            continue

        condition_by_id = {
            str(item.get("condition_id", "")).strip(): item
            for item in rule.get("applicability_conditions", [])
            if str(item.get("condition_id", "")).strip()
        }
        decision_ids = split_values(check.get("applicability_decision_ids"))
        linked_decisions = [applicability_by_id[value] for value in decision_ids if value in applicability_by_id]
        missing_decisions = sorted(set(condition_by_id) - {row.get("condition_id", "").strip() for row in linked_decisions})
        if not decision_ids:
            errors.append(f"{check_id}: resolved professional check requires applicability_decision_ids")
        for value in decision_ids:
            if value not in applicability_by_id:
                errors.append(f"{check_id}: applicability decision not found: {value}")
        if missing_decisions:
            errors.append(f"{check_id}: applicability conditions are missing: {', '.join(missing_decisions)}")
        for row in linked_decisions:
            decision_id = row.get("decision_id", "").strip()
            condition_id = row.get("condition_id", "").strip()
            condition = condition_by_id.get(condition_id)
            if row.get("check_id", "").strip() != check_id or row.get("rule_id", "").strip() != rule_id:
                errors.append(f"{decision_id}: applicability decision does not match {check_id}/{rule_id}")
            if not condition:
                errors.append(f"{decision_id}: condition_id not found in executable rule")
                continue
            if row.get("condition_description", "").strip() != str(condition.get("description", "")).strip():
                errors.append(f"{decision_id}: condition_description does not match executable rule")
            if row.get("expected_value", "").strip() != rule_expected_text(condition.get("expected", "")).strip():
                errors.append(f"{decision_id}: expected_value does not match executable rule")
            if row.get("status", "").strip() != "resolved":
                errors.append(f"{decision_id}: applicability decision is unresolved")
            required_fields = ["actual_value", "fact_ids", "drawing_refs"]
            if not ai_initial:
                required_fields.append("reviewer_name")
            for field in required_fields:
                if not present(row.get(field)):
                    errors.append(f"{decision_id}: resolved applicability decision requires {field}")
            completion_field = "completed_at" if ai_initial else "reviewed_at"
            if not valid_iso_datetime(row.get(completion_field)):
                errors.append(f"{decision_id}: {completion_field} must be an ISO date/time")
            if ai_initial and present(row.get("reviewer_name")):
                errors.append(f"{decision_id}: v1.6 must not record a reviewer_name")
            for fact_id in split_values(row.get("fact_ids")):
                if fact_id not in fact_ids:
                    errors.append(f"{decision_id}: fact_id not found: {fact_id}")
            result = row.get("result", "").strip()
            if result == "unknown":
                errors.append(f"{decision_id}: unknown applicability result blocks resolution")
            if result == "not_met" and condition.get("outcome_when_false") == "needs_review":
                errors.append(f"{decision_id}: failed condition requires needs_review")
        results = {row.get("condition_id", "").strip(): row.get("result", "").strip() for row in linked_decisions}
        applicability = check.get("applicability", "").strip()
        if applicability == "适用" and any(results.get(condition_id) != "met" for condition_id in condition_by_id):
            errors.append(f"{check_id}: applicability 适用 requires every condition to be met")
        if applicability == "不适用":
            positive_exclusions = [
                condition_id
                for condition_id, condition in condition_by_id.items()
                if results.get(condition_id) == "not_met"
                and condition.get("outcome_when_false") == "not_applicable"
            ]
            if not positive_exclusions:
                errors.append(f"{check_id}: 不适用 requires a fact-backed failed exclusion condition")

        graphic = rule.get("graphic_evidence_requirements", {})
        claim_type = check.get("graphic_claim_type", "").strip()
        if claim_type not in VALID_GRAPHIC_CLAIM_TYPES:
            errors.append(f"{check_id}: invalid graphic_claim_type: {claim_type}")
        if claim_type == "pending":
            errors.append(f"{check_id}: pending graphic claim classification blocks resolution")
        required_graphic = graphic.get("required") is True or claim_type not in {"", "none", "pending"}
        if claim_type == "none" and not present(check.get("graphic_gate_reason")):
            errors.append(f"{check_id}: graphic_claim_type none requires graphic_gate_reason")
        if graphic.get("required") is True and claim_type == "none":
            errors.append(f"{check_id}: executable rule requires a graphic evidence chain")
        chain_ids = split_values(check.get("graphic_chain_ids"))
        linked_graphics = [graphics_by_id[value] for value in chain_ids if value in graphics_by_id]
        if required_graphic and not chain_ids:
            errors.append(f"{check_id}: resolved graphic claim requires graphic_chain_ids")
        for value in chain_ids:
            if value not in graphics_by_id:
                errors.append(f"{check_id}: graphic evidence chain not found: {value}")
        for row in linked_graphics:
            chain_id = row.get("chain_id", "").strip()
            if row.get("check_id", "").strip() != check_id:
                errors.append(f"{chain_id}: graphic evidence does not match {check_id}")
            if row.get("status", "").strip() != "resolved":
                errors.append(f"{chain_id}: graphic evidence remains unresolved")
            for field in [
                "evidence_role", "source_file", "page", "drawing_ref", "location",
                "graphic_element", "observed_fact", "interpretation", "fact_ids",
                "screenshot_path", "source_quality",
            ]:
                if not present(row.get(field)):
                    errors.append(f"{chain_id}: resolved graphic evidence requires {field}")
            if not ai_initial and not present(row.get("reviewer_name")):
                errors.append(f"{chain_id}: resolved graphic evidence requires reviewer_name")
            completion_field = "completed_at" if ai_initial else "reviewed_at"
            if not valid_iso_datetime(row.get(completion_field)):
                errors.append(f"{chain_id}: {completion_field} must be an ISO date/time")
            if ai_initial and present(row.get("reviewer_name")):
                errors.append(f"{chain_id}: v1.6 must not record a reviewer_name")
            for fact_id in split_values(row.get("fact_ids")):
                if fact_id not in fact_ids:
                    errors.append(f"{chain_id}: fact_id not found: {fact_id}")
            screenshots = resolve_paths(root, row.get("screenshot_path"))
            if not screenshots:
                errors.append(f"{chain_id}: resolved graphic evidence requires a screenshot")
            for screenshot in screenshots:
                if not screenshot.exists() or screenshot.stat().st_size == 0:
                    errors.append(f"{chain_id}: graphic screenshot is missing or empty: {screenshot}")
        if required_graphic:
            roles = {row.get("evidence_role", "").strip() for row in linked_graphics if row.get("status", "").strip() == "resolved"}
            missing_roles = sorted(set(graphic.get("required_roles", [])) - roles)
            if missing_roles:
                errors.append(f"{check_id}: required graphic evidence roles are missing: {', '.join(missing_roles)}")
            if linked_graphics and all(row.get("source_quality", "").strip() == "raster_limited" for row in linked_graphics):
                errors.append(f"{check_id}: raster_limited evidence alone cannot close a graphic claim")
            sensitive = graphic.get("sensitive_to_ambiguity") is True or claim_type in AMBIGUITY_SENSITIVE_CLAIMS
            if sensitive and not any(
                present(row.get("alternative_interpretation")) and present(row.get("elimination_basis"))
                for row in linked_graphics
            ):
                errors.append(f"{check_id}: ambiguity-sensitive graphic claim requires an alternative interpretation and elimination basis")

        if ai_initial:
            if present(check.get("independent_review_id")):
                errors.append(f"{check_id}: v1.6 must not record independent_review_id")
            continue

        review_required = rule.get("independent_review_required") is True
        review_id = check.get("independent_review_id", "").strip()
        if review_required and not review_id:
            errors.append(f"{check_id}: high-risk rule requires independent_review_id")
        if review_id:
            review = independent_by_id.get(review_id)
            if not review:
                errors.append(f"{check_id}: independent review not found: {review_id}")
                continue
            if review.get("check_id", "").strip() != check_id:
                errors.append(f"{review_id}: independent review does not match {check_id}")
            primary = review.get("primary_reviewer", "").strip()
            secondary = review.get("secondary_reviewer", "").strip()
            if not primary or not secondary:
                errors.append(f"{review_id}: both reviewers are required")
            elif primary.casefold() == secondary.casefold():
                errors.append(f"{review_id}: primary and secondary reviewers must differ")
            reviewer_types = {
                review.get("primary_reviewer_type", "").strip(),
                review.get("secondary_reviewer_type", "").strip(),
            }
            if not reviewer_types.issubset(VALID_REVIEWER_TYPES):
                errors.append(f"{review_id}: reviewer types must be human or agent")
            if "human" not in reviewer_types:
                errors.append(f"{review_id}: at least one independent reviewer must be human")
            if review.get("blind_input_scope", "").strip() != "source_rule_only":
                errors.append(f"{review_id}: secondary review must use blind_input_scope source_rule_only")
            for field in ["primary_reviewed_at", "secondary_reviewed_at"]:
                if not valid_iso_datetime(review.get(field)):
                    errors.append(f"{review_id}: {field} must be an ISO date/time")
            primary_decision = review.get("primary_decision", "").strip()
            secondary_decision = review.get("secondary_decision", "").strip()
            if primary_decision not in {"符合", "不符合", "不适用"} or secondary_decision not in {"符合", "不符合", "不适用"}:
                errors.append(f"{review_id}: independent decisions must be resolved conclusions")
            status = review.get("status", "").strip()
            if status not in VALID_INDEPENDENT_STATUSES:
                errors.append(f"{review_id}: invalid independent review status: {status}")
            if primary_decision == secondary_decision:
                if status != "agreed" or review.get("agreement", "").strip().lower() not in {"yes", "true", "1", "是"}:
                    errors.append(f"{review_id}: matching decisions require status agreed")
                if check.get("conclusion", "").strip() != primary_decision:
                    errors.append(f"{review_id}: agreed decision does not match check conclusion")
            else:
                if status != "adjudicated" or review.get("agreement", "").strip().lower() not in {"no", "false", "0", "否"}:
                    errors.append(f"{review_id}: disagreement requires human adjudication")
                if review.get("adjudicator_type", "").strip() != "human" or not present(review.get("adjudicator")):
                    errors.append(f"{review_id}: disagreement requires a named human adjudicator")
                if review.get("adjudicated_decision", "").strip() != check.get("conclusion", "").strip():
                    errors.append(f"{review_id}: adjudicated decision does not match check conclusion")
                if not valid_iso_datetime(review.get("adjudicated_at")):
                    errors.append(f"{review_id}: adjudicated_at must be an ISO date/time")
    return errors


def load_v14_profile(root: Path) -> tuple[dict, list[str]]:
    path = root / "project_profile.json"
    if not path.exists():
        return {}, ["v1.4 requires project_profile.json"]
    try:
        profile = load_profile(path)
    except Exception as error:
        return {}, [f"project_profile.json is invalid: {error}"]
    return profile, []


def validate_v14_profile(profile: dict, manifest: dict, fact_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if profile.get("schema_version") != "1.0":
        errors.append("project_profile.json requires schema_version 1.0")
    if profile.get("report_type") != manifest.get("report_type"):
        errors.append("project_profile report_type conflicts with review_manifest")
    if profile.get("confirmed") is not True:
        errors.append("project_profile is not reviewer-confirmed")
    if not str(profile.get("confirmed_by", "")).strip():
        errors.append("project_profile confirmed_by is required")
    if not valid_iso_datetime(str(profile.get("confirmed_at", ""))):
        errors.append("project_profile confirmed_at must be an ISO date/time")
    facts = profile.get("facts", {})
    if not isinstance(facts, dict):
        return errors + ["project_profile facts must be an object"]
    missing = sorted(PROFILE_FACT_KEYS - set(facts))
    if missing:
        errors.append(f"project_profile is missing facts: {', '.join(missing)}")
    for key in sorted(PROFILE_FACT_KEYS & set(facts)):
        record = facts.get(key, {})
        if not isinstance(record, dict):
            errors.append(f"project_profile {key} must be an object")
            continue
        status = str(record.get("status", "")).strip()
        if status not in {"confirmed", "not_applicable", "unknown"}:
            errors.append(f"project_profile {key} has invalid status: {status}")
            continue
        if status == "unknown":
            errors.append(f"project_profile {key} remains unknown")
        elif status == "confirmed":
            if record.get("value", "") == "":
                errors.append(f"project_profile {key} confirmed value is blank")
            ids = record.get("fact_ids", [])
            if not isinstance(ids, list) or not ids:
                errors.append(f"project_profile {key} confirmed fact_ids are required")
            else:
                for fact_id in ids:
                    if str(fact_id) not in fact_ids:
                        errors.append(f"project_profile {key} fact_id not found: {fact_id}")
        elif not str(record.get("notes", "")).strip():
            errors.append(f"project_profile {key} not_applicable requires notes")
    route = profile.get("route_confirmation", {})
    if not isinstance(route, dict) or route.get("confirmed") is not True:
        errors.append("specialty route has not been reviewer-confirmed")
    else:
        if not str(route.get("confirmed_by", "")).strip():
            errors.append("route_confirmation confirmed_by is required")
        if not valid_iso_datetime(str(route.get("confirmed_at", ""))):
            errors.append("route_confirmation confirmed_at must be an ISO date/time")
    tracks = profile.get("discovery_tracks", {})
    for track in sorted(VALID_DISCOVERY_TRACKS):
        record = tracks.get(track, {}) if isinstance(tracks, dict) else {}
        if record.get("status") != "completed":
            errors.append(f"discovery track is not completed: {track}")
        if not str(record.get("notes", "")).strip():
            errors.append(f"discovery track requires notes: {track}")
    return errors


def validate_v16_profile(profile: dict, manifest: dict, fact_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if profile.get("schema_version") != "1.1":
        errors.append("v1.6 project_profile.json requires schema_version 1.1")
    if profile.get("review_stage") != "ai_initial":
        errors.append("v1.6 project_profile review_stage must be ai_initial")
    if profile.get("report_type") != manifest.get("report_type"):
        errors.append("project_profile report_type conflicts with review_manifest")
    for forbidden in ["confirmed", "confirmed_by", "confirmed_at", "route_confirmation"]:
        if forbidden in profile:
            errors.append(f"v1.6 project_profile must not contain legacy human field: {forbidden}")
    if profile.get("ai_review_completed") is not True:
        errors.append("v1.6 project_profile AI review is not completed")
    if not valid_iso_datetime(str(profile.get("completed_at", ""))):
        errors.append("v1.6 project_profile completed_at must be an ISO date/time")
    facts = profile.get("facts", {})
    if not isinstance(facts, dict):
        return errors + ["project_profile facts must be an object"]
    missing = sorted(PROFILE_FACT_KEYS - set(facts))
    if missing:
        errors.append(f"project_profile is missing facts: {', '.join(missing)}")
    for key in sorted(PROFILE_FACT_KEYS & set(facts)):
        record = facts.get(key, {})
        if not isinstance(record, dict):
            errors.append(f"project_profile {key} must be an object")
            continue
        status = str(record.get("status", "")).strip()
        if status not in {"ai_completed", "not_applicable", "unknown"}:
            errors.append(f"project_profile {key} has invalid v1.6 status: {status}")
            continue
        if status == "unknown":
            errors.append(f"project_profile {key} remains unknown")
        elif status == "ai_completed":
            if record.get("value", "") == "":
                errors.append(f"project_profile {key} AI-completed value is blank")
            ids = record.get("fact_ids", [])
            if not isinstance(ids, list) or not ids:
                errors.append(f"project_profile {key} AI-completed fact_ids are required")
            else:
                for fact_id in ids:
                    if str(fact_id) not in fact_ids:
                        errors.append(f"project_profile {key} fact_id not found: {fact_id}")
        elif not str(record.get("notes", "")).strip():
            errors.append(f"project_profile {key} not_applicable requires notes")
    route = profile.get("route_completion", {})
    if not isinstance(route, dict) or route.get("status") != "AI初审完成":
        errors.append("v1.6 specialty route status must be AI初审完成")
    elif not valid_iso_datetime(str(route.get("completed_at", ""))):
        errors.append("v1.6 route_completion completed_at must be an ISO date/time")
    tracks = profile.get("discovery_tracks", {})
    for track in sorted(VALID_DISCOVERY_TRACKS):
        record = tracks.get(track, {}) if isinstance(tracks, dict) else {}
        if record.get("status") != "completed":
            errors.append(f"discovery track is not completed: {track}")
        if not str(record.get("notes", "")).strip():
            errors.append(f"discovery track requires notes: {track}")
    return errors


def load_v14_catalog(root: Path, manifest: dict) -> tuple[dict, list[str], str]:
    errors: list[str] = []
    snapshot = manifest.get("rule_catalog_snapshot", {})
    if not isinstance(snapshot, dict):
        return {}, ["rule_catalog_snapshot is missing"], ""
    path_value = str(snapshot.get("path", "")).strip()
    catalog_path = Path(path_value) if path_value else DEFAULT_RULE_CATALOG
    if not catalog_path.is_absolute():
        catalog_path = root / catalog_path
    if not catalog_path.exists():
        return {}, [f"rule catalog is missing: {catalog_path}"], ""
    current_hash = sha256_file(catalog_path)
    if current_hash != str(snapshot.get("sha256", "")).strip():
        errors.append("rule catalog changed after workspace creation; re-route and regenerate the checklist")
    try:
        catalog = load_catalog(catalog_path)
    except Exception as error:
        return {}, errors + [f"rule catalog is invalid: {error}"], current_hash
    if catalog.get("schema_version") not in {"1.0", "1.1"} or not catalog.get("rules"):
        errors.append("rule catalog requires schema_version 1.0/1.1 and non-empty rules")
    return catalog, errors, current_hash


def workspace_input_hashes(root: Path) -> dict[str, str]:
    names = ["review_manifest.json", "project_profile.json", *REQUIRED_FILES]
    schema_version, _manifest = load_manifest(root)
    if schema_version == "1.7":
        names.append("judgment_evidence.json")
    if schema_version == "1.5":
        names.extend(V15_REQUIRED_FILES)
    elif schema_version in {"1.6", "1.7"}:
        names.extend(V16_REQUIRED_FILES)
    return {name: sha256_file(root / name) for name in names if (root / name).exists()}


def validate_completion_audit(root: Path, catalog_hash: str, workspace_schema_version: str) -> list[str]:
    path = root / "completion_audit.json"
    if not path.exists():
        return [
            f"v{workspace_schema_version} requires completion_audit.json; "
            "run audit_review_completeness.py after the final snapshot"
        ]
    try:
        audit = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        return [f"completion_audit.json is invalid: {error}"]
    errors: list[str] = []
    if (
        audit.get("schema_version") != "1.0"
        or audit.get("workspace_schema_version") != workspace_schema_version
    ):
        errors.append("completion audit schema is invalid")
    if audit.get("status") != "pass" or audit.get("errors"):
        errors.append("completion audit has not passed")
    if audit.get("input_hashes") != workspace_input_hashes(root):
        errors.append("completion audit is stale because review inputs changed")
    if audit.get("rule_catalog_sha256") != catalog_hash:
        errors.append("completion audit is stale because the rule catalog changed")
    return errors


def valid_coverage_topics(catalog: dict | None = None) -> set[str]:
    topics = {topic for values in FAMILY_REQUIRED_TOPICS.values() for topic in values}
    for _terms, report_topics in FUNCTION_TRIGGER_TOPICS:
        for values in report_topics.values():
            topics.update(values)
    if catalog:
        topics.update(
            str(rule.get("coverage_topic", "")).strip()
            for rule in catalog.get("rules", [])
            if str(rule.get("coverage_topic", "")).strip()
        )
    return topics


def function_required_topics(fact_text: str, report_type: str) -> set[str]:
    required: set[str] = set()
    for terms, report_topics in FUNCTION_TRIGGER_TOPICS:
        if any(term in fact_text for term in terms):
            required.update(report_topics.get(report_type, set()))
    return required


def check_closes_topic(check: dict[str, str]) -> bool:
    if check.get("decision_state", "").strip() and check.get("decision_state", "").strip() != "resolved":
        return False
    return (
        check.get("applicability", "").strip() in {"适用", "不适用"}
        and check.get("conclusion", "").strip() in {"符合", "不符合", "不适用"}
    )


def validate_workspace(root: Path, require_completion_audit: bool = True) -> tuple[list[str], list[str]]:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    if not root.exists():
        return [f"Project workspace not found: {root}"], warnings
    for filename in REQUIRED_FILES:
        if not (root / filename).exists():
            errors.append(f"Missing required ledger: {filename}")
    if errors:
        return errors, warnings

    schema_version, manifest = load_manifest(root)
    v11 = schema_version == "1.1"
    v12 = schema_version == "1.2"
    v13 = schema_version == "1.3"
    v14 = schema_version == "1.4"
    v15 = schema_version == "1.5"
    v16 = schema_version in {"1.6", "1.7"}
    v15plus = v15 or v16
    v14plus = v14 or v15plus
    modern = v12 or v13 or v14plus
    versioned = v11 or modern
    if manifest.get("_invalid"):
        errors.append("review_manifest.json is invalid JSON")
    elif manifest and not schema_version:
        errors.append(f"unsupported review_manifest schema_version: {manifest.get('schema_version', '')}")
    if v15:
        for filename in V15_REQUIRED_FILES:
            if not (root / filename).exists():
                errors.append(f"Missing v1.5 required ledger: {filename}")
        if errors:
            return errors, warnings
    if v16:
        if manifest.get("review_stage") != "ai_initial":
            errors.append("v1.6 review_manifest review_stage must be ai_initial")
        if (root / "independent_review_log.csv").exists():
            errors.append("v1.6 must not create independent_review_log.csv")
        for filename in V16_REQUIRED_FILES:
            if not (root / filename).exists():
                errors.append(f"Missing v1.6 required ledger: {filename}")
        if errors:
            return errors, warnings
    inventory = rows(root / "drawing_inventory.csv")
    facts = rows(root / "fact_ledger.csv")
    checks = rows(root / "check_matrix.csv")
    issues = rows(root / "issue_candidates.csv")
    validation = rows(root / "validation_log.csv")
    inventory_fields = fieldnames(root / "drawing_inventory.csv")
    issue_fields = fieldnames(root / "issue_candidates.csv")
    check_fields = fieldnames(root / "check_matrix.csv")
    validation_fields = fieldnames(root / "validation_log.csv")
    graphic_rows = rows(root / "graphic_evidence_chain.csv") if v15plus else []
    applicability_rows = rows(root / "applicability_decisions.csv") if v15plus else []
    independent_rows = rows(root / "independent_review_log.csv") if v15 else []
    graphic_fields = fieldnames(root / "graphic_evidence_chain.csv") if v15plus else set()
    applicability_fields = fieldnames(root / "applicability_decisions.csv") if v15plus else set()
    independent_fields = fieldnames(root / "independent_review_log.csv") if v15 else set()
    has_screenshot_fields = versioned or LEGACY_NEW_ISSUE_FIELDS.issubset(issue_fields)

    if not inventory:
        errors.append("drawing_inventory.csv has no drawing rows")
    if not facts:
        errors.append("fact_ledger.csv has no fact rows")
    if not checks:
        errors.append("check_matrix.csv has no check rows")

    if versioned:
        required_issue_fields = V12_ISSUE_FIELDS if modern else V11_ISSUE_FIELDS
        missing = required_issue_fields - issue_fields
        if missing:
            errors.append(f"v{schema_version} issue_candidates.csv missing fields: {', '.join(sorted(missing))}")
        required_validation_fields = V16_GATE_FIELDS if v16 else V14_GATE_FIELDS if v14plus else V12_GATE_FIELDS if modern else V11_GATE_FIELDS
        missing_validation = required_validation_fields - validation_fields
        if missing_validation:
            errors.append(
                f"v{schema_version} validation_log.csv missing fields: {', '.join(sorted(missing_validation))}"
            )
        if modern:
            missing_inventory = V12_INVENTORY_FIELDS - inventory_fields
            if missing_inventory:
                errors.append(
                    f"v{schema_version} drawing_inventory.csv missing fields: "
                    f"{', '.join(sorted(missing_inventory))}"
                )
        if v13 or v14plus:
            required_check_fields = V16_CHECK_FIELDS if v16 else V15_CHECK_FIELDS if v15 else V14_CHECK_FIELDS if v14 else V13_CHECK_FIELDS
            missing_checks = required_check_fields - check_fields
            if missing_checks:
                errors.append(
                    f"v{schema_version} check_matrix.csv missing fields: "
                    f"{', '.join(sorted(missing_checks))}"
                )
        if v15:
            for label, actual, required in [
                ("graphic_evidence_chain.csv", graphic_fields, V15_GRAPHIC_FIELDS),
                ("applicability_decisions.csv", applicability_fields, V15_APPLICABILITY_FIELDS),
                ("independent_review_log.csv", independent_fields, V15_INDEPENDENT_FIELDS),
            ]:
                missing_fields = required - actual
                if missing_fields:
                    errors.append(
                        f"v1.5 {label} missing fields: {', '.join(sorted(missing_fields))}"
                    )
        if v16:
            for label, actual, required in [
                ("graphic_evidence_chain.csv", graphic_fields, V16_GRAPHIC_FIELDS),
                ("applicability_decisions.csv", applicability_fields, V16_APPLICABILITY_FIELDS),
            ]:
                missing_fields = required - actual
                if missing_fields:
                    errors.append(
                        f"v1.6 {label} missing fields: {', '.join(sorted(missing_fields))}"
                    )
        for items, field in [(facts, "fact_id"), (checks, "check_id"), (issues, "issue_id"), (validation, "issue_id")]:
            for duplicate in duplicate_ids(items, field):
                errors.append(f"duplicate {field}: {duplicate}")
        for fact in facts:
            fact_id = fact.get("fact_id", "").strip() or "[missing fact_id]"
            if not present(fact.get("fact_id")):
                errors.append("fact_ledger.csv contains a row without fact_id")
            elif not fact_matches_inventory(fact, inventory):
                errors.append(f"{fact_id}: source_file/page/drawing_no not found in drawing_inventory.csv")
    else:
        missing_issue = LEGACY_NEW_ISSUE_FIELDS - issue_fields
        if missing_issue:
            warnings.append(f"issue_candidates.csv uses legacy fields; upgrade recommended. Missing: {', '.join(sorted(missing_issue))}")
        missing_validation = LEGACY_GATE_FIELDS - validation_fields
        if missing_validation:
            warnings.append(f"validation_log.csv uses legacy fields; upgrade recommended. Missing: {', '.join(sorted(missing_validation))}")

    fact_ids = {row.get("fact_id", "").strip() for row in facts if present(row.get("fact_id"))}
    check_ids = {row.get("check_id", "").strip() for row in checks if present(row.get("check_id"))}
    facts_by_id = {row.get("fact_id", "").strip(): row for row in facts if present(row.get("fact_id"))}
    checks_by_id = {row.get("check_id", "").strip(): row for row in checks if present(row.get("check_id"))}
    validation_ids = {row.get("issue_id", "").strip(): row for row in validation if present(row.get("issue_id"))}
    profile: dict = {}
    catalog: dict = {}
    rules_by_id: dict[str, dict] = {}
    catalog_hash = ""
    if v14plus:
        for duplicate in duplicate_ids(checks, "atomic_check_id"):
            errors.append(f"duplicate atomic_check_id: {duplicate}")
        if v15plus:
            for items, field in [
                (graphic_rows, "chain_id"),
                (applicability_rows, "decision_id"),
            ]:
                for duplicate in duplicate_ids(items, field):
                    errors.append(f"duplicate {field}: {duplicate}")
            if v15:
                for duplicate in duplicate_ids(independent_rows, "review_id"):
                    errors.append(f"duplicate review_id: {duplicate}")
        profile, profile_errors = load_v14_profile(root)
        errors.extend(profile_errors)
        if profile:
            errors.extend(
                validate_v16_profile(profile, manifest, fact_ids)
                if v16 else validate_v14_profile(profile, manifest, fact_ids)
            )
        catalog, catalog_errors, catalog_hash = load_v14_catalog(root, manifest)
        errors.extend(catalog_errors)
        rules_by_id = {
            str(rule.get("rule_id", "")).strip(): rule
            for rule in catalog.get("rules", [])
            if str(rule.get("rule_id", "")).strip()
        }
        if profile and catalog:
            errors.extend(
                validate_required_rule_packs(
                    catalog,
                    profile,
                    checks,
                    manifest.get("report_type", ""),
                )
            )

    if modern and V12_INVENTORY_FIELDS.issubset(inventory_fields):
        for row_number, drawing in enumerate(inventory, start=2):
            label = drawing.get("drawing_no", "").strip() or drawing.get("drawing_name", "").strip() or f"row {row_number}"
            family = drawing.get("review_family", "").strip()
            status = drawing.get("review_status", "").strip()
            if family not in VALID_REVIEW_FAMILIES:
                errors.append(f"{label}: invalid review_family: {family}")
            if status not in VALID_REVIEW_STATUSES:
                errors.append(f"{label}: invalid review_status: {status}")
                continue
            linked_checks = split_values(drawing.get("review_check_ids"))
            if status == "reviewed":
                if not linked_checks:
                    errors.append(f"{label}: reviewed drawing requires review_check_ids")
                substantive_links = 0
                closed_topics: set[str] = set()
                for check_id in linked_checks:
                    if check_id not in check_ids:
                        errors.append(f"{label}: review_check_id not found in check_matrix.csv: {check_id}")
                        continue
                    check = checks_by_id[check_id]
                    if not check_references_drawing(check, drawing):
                        continue
                    linked_facts = [facts_by_id.get(fact_id) for fact_id in split_values(check.get("fact_ids"))]
                    if any(fact and fact_matches_drawing(fact, drawing) for fact in linked_facts):
                        substantive_links += 1
                        if check_closes_topic(check):
                            closed_topics.add(check.get("coverage_topic", "").strip())
                if linked_checks and not substantive_links:
                    errors.append(f"{label}: reviewed drawing has no substantive sheet-specific check")
                if v13 or v14plus:
                    required_topics = FAMILY_REQUIRED_TOPICS.get(family, set())
                    missing_topics = sorted(required_topics - closed_topics)
                    if missing_topics:
                        errors.append(
                            f"{label}: required coverage topics are not closed: "
                            f"{', '.join(missing_topics)}"
                        )
                if v14plus and profile and catalog:
                    expected = applicable_rules(catalog, profile, family, manifest.get("report_type", ""))
                    expected_ids = {rule["rule_id"] for rule, _state in expected}
                    linked_rule_ids = {
                        checks_by_id[check_id].get("rule_id", "").strip()
                        for check_id in linked_checks
                        if check_id in checks_by_id
                    }
                    missing_rules = sorted(expected_ids - linked_rule_ids)
                    if missing_rules:
                        errors.append(
                            f"{label}: triggered atomic rules are missing: {', '.join(missing_rules)}"
                        )
                    unresolved_rules = sorted(
                        checks_by_id[check_id].get("rule_id", "").strip()
                        for check_id in linked_checks
                        if check_id in checks_by_id
                        and checks_by_id[check_id].get("rule_id", "").strip() in expected_ids
                        and checks_by_id[check_id].get("decision_state", "").strip() != "resolved"
                    )
                    if unresolved_rules:
                        errors.append(
                            f"{label}: triggered atomic rules are unresolved: {', '.join(unresolved_rules)}"
                        )
            elif status == "not_applicable" and not present(drawing.get("review_notes")):
                errors.append(f"{label}: not_applicable drawing requires review_notes")
            elif status == "needs_review":
                errors.append(f"{label}: drawing review_status needs_review blocks report generation")

    for check in checks:
        check_id = check.get("check_id", "").strip() or "[missing check_id]"
        if versioned and not present(check.get("check_id")):
            errors.append("check_matrix.csv contains a row without check_id")
        if not present(check.get("specialty")):
            errors.append(f"{check_id}: missing specialty")
        if not present(check.get("source_review_item")):
            errors.append(f"{check_id}: missing source_review_item")
        applicability = check.get("applicability", "").strip()
        if applicability not in VALID_APPLICABILITY:
            errors.append(f"{check_id}: invalid applicability: {applicability}")
        conclusion = check.get("conclusion", "").strip()
        if conclusion not in VALID_CONCLUSIONS:
            errors.append(f"{check_id}: invalid conclusion: {conclusion}")
        if applicability == "需判断" and conclusion != "需核验":
            errors.append(f"{check_id}: applicability 需判断 requires conclusion 需核验")
        if modern and generic_presence_only(check, facts_by_id):
            errors.append(f"{check_id}: generic drawing-presence statement cannot close a compliant check")
        if v13 or v14plus:
            review_item_id = check.get("review_item_id", "").strip()
            coverage_topic = check.get("coverage_topic", "").strip()
            evidence_class = check.get("evidence_class", "").strip()
            if not review_item_id:
                errors.append(f"{check_id}: missing review_item_id")
            if coverage_topic not in valid_coverage_topics(catalog if v14plus else None):
                errors.append(f"{check_id}: invalid coverage_topic: {coverage_topic}")
            if evidence_class not in VALID_EVIDENCE_CLASSES:
                errors.append(f"{check_id}: invalid evidence_class: {evidence_class}")
            if applicability == "不适用" or conclusion == "不适用":
                if applicability != "不适用" or conclusion != "不适用":
                    errors.append(f"{check_id}: 不适用 requires both applicability and conclusion to be 不适用")
                if evidence_class != "not_applicable":
                    errors.append(f"{check_id}: 不适用 requires evidence_class not_applicable")
            elif evidence_class == "not_applicable":
                errors.append(f"{check_id}: evidence_class not_applicable requires a 不适用 check")
            allowed_classes = TOPIC_EVIDENCE_CLASSES.get(coverage_topic)
            if allowed_classes and evidence_class not in allowed_classes and evidence_class != "not_applicable":
                errors.append(
                    f"{check_id}: evidence_class {evidence_class} does not fit "
                    f"coverage_topic {coverage_topic}"
                )
        if v13 and conclusion in {"符合", "不符合"}:
            for field in ["standard_source", "standard_article", "standard_requirement"]:
                if not present(check.get(field)):
                    errors.append(f"{check_id}: v1.3 technical closure requires {field}; upgrade to v1.4 for design-depth-only rules")
        if v14plus:
            rule_id = check.get("rule_id", "").strip()
            atomic_check_id = check.get("atomic_check_id", "").strip()
            decision_state = check.get("decision_state", "").strip()
            discovery_track = check.get("discovery_track", "").strip()
            rule = rules_by_id.get(rule_id)
            if not rule_id:
                errors.append(f"{check_id}: missing rule_id")
            elif not rule:
                errors.append(f"{check_id}: rule_id not found in snapshotted catalog: {rule_id}")
            elif coverage_topic != str(rule.get("coverage_topic", "")).strip():
                errors.append(
                    f"{check_id}: coverage_topic {coverage_topic} does not match executable rule {rule_id}"
                )
            if not atomic_check_id:
                errors.append(f"{check_id}: missing atomic_check_id")
            if decision_state not in VALID_DECISION_STATES:
                errors.append(f"{check_id}: invalid decision_state: {decision_state}")
            if discovery_track not in VALID_DISCOVERY_TRACKS:
                errors.append(f"{check_id}: invalid discovery_track: {discovery_track}")
            if not present(check.get("applicability_basis")):
                errors.append(f"{check_id}: missing applicability_basis")
            if decision_state == "unreviewed":
                if conclusion != "需核验":
                    errors.append(f"{check_id}: unreviewed check requires conclusion 需核验")
                errors.append(f"{check_id}: unreviewed atomic check blocks report generation")
            elif decision_state == "needs_review":
                if conclusion != "需核验" or not present(check.get("open_reason")):
                    errors.append(f"{check_id}: needs_review requires conclusion 需核验 and open_reason")
                errors.append(f"{check_id}: unresolved atomic check blocks report generation")
            elif decision_state == "resolved":
                if conclusion == "需核验":
                    errors.append(f"{check_id}: resolved check cannot use conclusion 需核验")
                for field in ["actual_fact", "fact_ids", "drawing_refs", "comparison_method", "comparison_record"]:
                    if not present(check.get(field)):
                        errors.append(f"{check_id}: resolved check requires {field}")
                if v16:
                    if check.get("completion_gate", "").strip() != "AI初审完成":
                        errors.append(f"{check_id}: resolved v1.6 check requires completion_gate AI初审完成")
                    if present(check.get("reviewer_gate")) or present(check.get("independent_review_id")):
                        errors.append(f"{check_id}: v1.6 must not contain human review gate fields")
                elif check.get("reviewer_gate", "").strip() != "已复核":
                    errors.append(f"{check_id}: resolved check requires reviewer_gate 已复核")
                for fact_id in split_values(check.get("fact_ids")):
                    if fact_id not in fact_ids:
                        errors.append(f"{check_id}: fact_id not found in fact_ledger.csv: {fact_id}")
                if generic_presence_only(check, facts_by_id):
                    errors.append(f"{check_id}: presence-only wording cannot resolve an atomic check")
                if applicability == "不适用" and not present(check.get("applicability_basis")):
                    errors.append(f"{check_id}: 不适用 requires a project-fact applicability basis")
                if rule:
                    authority_mode = rule.get("authority_mode")
                    expected_track = "technical_compliance" if authority_mode == "normative" else "design_depth"
                    if discovery_track != expected_track and discovery_track != "optimization":
                        errors.append(
                            f"{check_id}: discovery_track {discovery_track} conflicts with rule authority {authority_mode}"
                        )
                    if authority_mode == "normative" and conclusion in {"符合", "不符合"}:
                        basis = rule.get("basis", {})
                        expected = {
                            "standard_source": basis.get("relative_path", ""),
                            "standard_article": basis.get("article", ""),
                            "standard_requirement": basis.get("requirement", ""),
                        }
                        for field, value in expected.items():
                            if check.get(field, "").strip() != str(value).strip():
                                errors.append(f"{check_id}: {field} does not match executable rule {rule_id}")
                        if basis.get("source_role") != "B_核心规范":
                            errors.append(f"{check_id}: normative conclusion is not backed by B_核心规范")
                    if authority_mode == "design_depth" and any(
                        present(check.get(field))
                        for field in ["standard_source", "standard_article", "standard_requirement"]
                    ):
                        errors.append(f"{check_id}: design-depth rule must not carry a technical citation")
                    if rule.get("calculation_required") is True and conclusion in {"符合", "不符合"}:
                        if not present(check.get("calculation_record")):
                            errors.append(f"{check_id}: executable rule requires calculation_record")
                    if invalid_absence_not_applicable(check, rule):
                        errors.append(
                            f"{check_id}: absence of a required residential measure cannot justify 不适用; "
                            "record a positive project-scope fact or keep the check unresolved"
                        )
        forms_issue = check.get("forms_issue", "").strip().lower()
        if forms_issue not in {"yes", "no", "y", "n", "true", "false", "1", "0"}:
            errors.append(f"{check_id}: forms_issue must be yes/no")
        if forms_issue in {"no", "n", "false", "0"} and not present(check.get("not_forming_reason")):
            errors.append(f"{check_id}: missing not_forming_reason for non-issue check")
        if v14plus and forms_issue in {"yes", "y", "true", "1"} and conclusion != "不符合":
            errors.append(f"{check_id}: only an 不符合 check may form a formal issue")

    if v13:
        report_type = manifest.get("report_type", "")
        fact_text = " ".join(
            " ".join(value or "" for value in fact.values())
            for fact in facts
        )
        required_function_topics = function_required_topics(fact_text, report_type)
        closed_function_topics = {
            check.get("coverage_topic", "").strip()
            for check in checks
            if check_closes_topic(check)
            and any(fact_id in fact_ids for fact_id in split_values(check.get("fact_ids")))
        }
        missing_function_topics = sorted(required_function_topics - closed_function_topics)
        if missing_function_topics:
            errors.append(
                "function-triggered coverage topics are not closed: "
                f"{', '.join(missing_function_topics)}"
            )

    reportable_status = "ai_ready" if v16 else "verified"
    verified = [row for row in issues if row.get("status", "").strip() == reportable_status]
    if not verified:
        if not versioned:
            errors.append("issue_candidates.csv has no verified issues")
        else:
            if any(row.get("forms_issue", "").strip().lower() in {"yes", "y", "true", "1"} for row in checks):
                errors.append("zero-opinion review has check items that form issues")
            if any(row.get("conclusion", "").strip() not in {"符合", "不适用"} for row in checks):
                errors.append("zero-opinion review may contain only 符合 or 不适用 conclusions")

    for issue in issues:
        issue_id = issue.get("issue_id", "").strip() or "[missing issue_id]"
        status = issue.get("status", "").strip()
        if versioned and not present(issue.get("issue_id")):
            errors.append("issue_candidates.csv contains a row without issue_id")
        if status not in VALID_ISSUE_STATUSES:
            errors.append(f"{issue_id}: invalid status: {status}")
        elif v16 and status == "verified":
            errors.append(f"{issue_id}: v1.6 uses ai_ready instead of verified")
        elif not v16 and status == "ai_ready":
            errors.append(f"{issue_id}: ai_ready is valid only for schema_version 1.6")
        if status in {"needs_review", "rejected"} and not present(issue.get("notes")):
            errors.append(f"{issue_id}: {status} issue must explain exclusion in notes")

    if versioned and verified:
        orders: list[int] = []
        report_type = manifest.get("report_type", "")
        if report_type not in VALID_SECTIONS:
            errors.append(f"invalid manifest report_type: {report_type}")
        for issue in verified:
            issue_id = issue.get("issue_id", "").strip() or "[missing issue_id]"
            try:
                order = int(issue.get("display_order", ""))
                if order < 1:
                    raise ValueError
                orders.append(order)
            except ValueError:
                errors.append(f"{issue_id}: display_order must be a positive integer")
            if report_type in VALID_SECTIONS and issue.get("report_section", "").strip() not in VALID_SECTIONS[report_type]:
                errors.append(f"{issue_id}: invalid report_section for {report_type}: {issue.get('report_section', '')}")
        if len(orders) != len(set(orders)):
            errors.append("verified issues have duplicate display_order values")
        if orders and sorted(orders) != list(range(1, len(orders) + 1)):
            errors.append("verified issue display_order must be continuous from 1")
        primary_check_ids = [issue.get("check_id", "").strip() for issue in verified]
        duplicate_primary_checks = sorted(
            {check_id for check_id in primary_check_ids if check_id and primary_check_ids.count(check_id) > 1}
        )
        for check_id in duplicate_primary_checks:
            errors.append(f"verified issues share primary check_id: {check_id}")

    for issue in verified:
        issue_id = issue.get("issue_id", "").strip() or "[missing issue_id]"
        check_id = issue.get("check_id", "").strip()
        if not check_id:
            errors.append(f"{issue_id}: missing check_id")
        elif check_id not in check_ids:
            errors.append(f"{issue_id}: check_id not found in check_matrix.csv: {check_id}")
        elif modern:
            linked_check = checks_by_id[check_id]
            if linked_check.get("applicability", "").strip() == "需判断" or linked_check.get("conclusion", "").strip() == "需核验":
                errors.append(f"{issue_id}: unresolved check cannot support a verified issue")
            if v14plus:
                if linked_check.get("decision_state", "").strip() != "resolved":
                    errors.append(f"{issue_id}: verified issue requires a resolved atomic check")
                if linked_check.get("forms_issue", "").strip().lower() not in {"yes", "y", "true", "1"}:
                    errors.append(f"{issue_id}: linked atomic check does not form an issue")
                if linked_check.get("issue_id", "").strip() != issue_id:
                    errors.append(f"{issue_id}: linked atomic check issue_id does not match")
        linked_facts = split_values(issue.get("fact_ids"))
        if not linked_facts:
            errors.append(f"{issue_id}: missing fact_ids")
        for fact_id in linked_facts:
            if fact_id not in fact_ids:
                errors.append(f"{issue_id}: fact_id not found in fact_ledger.csv: {fact_id}")
        for field in ["drawing_refs", "problem"]:
            if not present(issue.get(field)):
                errors.append(f"{issue_id}: missing {field}")
        if versioned and not present(issue.get("judgment")):
            errors.append(f"{issue_id}: missing judgment")
        if v11:
            for field in ["standard_source", "standard_article", "standard_requirement"]:
                if not present(issue.get(field)):
                    errors.append(f"{issue_id}: missing {field}")
        elif modern:
            drawing_refs = issue.get("drawing_refs", "")
            for fact_id in linked_facts:
                fact = facts_by_id.get(fact_id)
                if not fact:
                    continue
                for field in ["drawing_no", "drawing_name"]:
                    value = fact.get(field, "").strip()
                    if value and value not in drawing_refs:
                        errors.append(f"{issue_id}: drawing_refs missing linked fact {field}: {value}")
            citation_mode = issue.get("citation_mode", "").strip().lower()
            if citation_mode not in VALID_CITATION_MODES:
                errors.append(f"{issue_id}: invalid citation_mode: {citation_mode}")
            elif citation_mode == "cited":
                for field in ["standard_source", "standard_display_name", "standard_article", "standard_requirement"]:
                    if not present(issue.get(field)):
                        errors.append(f"{issue_id}: citation_mode cited requires {field}")
                display_name = issue.get("standard_display_name", "").strip().casefold()
                if ".pdf" in display_name:
                    errors.append(f"{issue_id}: standard_display_name must not contain .pdf")
                if "/" in display_name or "\\" in display_name:
                    errors.append(f"{issue_id}: standard_display_name must not contain a file path")
            elif citation_mode == "none":
                if not present(issue.get("citation_none_reason")):
                    errors.append(f"{issue_id}: citation_mode none requires citation_none_reason")
                if issue.get("opinion_type", "").strip() not in DESIGN_DEPTH_OPINION_TYPES:
                    errors.append(f"{issue_id}: citation_mode none is allowed only for design-depth opinion types")
                for field in ["standard_source", "standard_display_name", "standard_article", "standard_requirement"]:
                    if present(issue.get(field)):
                        errors.append(f"{issue_id}: citation_mode none requires empty {field}")
        else:
            for field in ["standard_source", "standard_requirement"]:
                if not present(issue.get(field)):
                    errors.append(f"{issue_id}: missing {field}")

        screenshot_paths = resolve_paths(root, issue.get("screenshot_path"))
        strategy = issue.get("screenshot_strategy", "").strip().lower()
        if has_screenshot_fields and strategy not in VALID_SCREENSHOT_STRATEGIES:
            errors.append(f"{issue_id}: invalid screenshot_strategy: {strategy}")
        if has_screenshot_fields and not present(issue.get("notes")):
            errors.append(f"{issue_id}: verified issue must record professional filtering reason in notes")
        if has_screenshot_fields and strategy == "none":
            if not present(issue.get("screenshot_reason")):
                errors.append(f"{issue_id}: screenshot_strategy none requires screenshot_reason")
        elif has_screenshot_fields and strategy in SCREENSHOT_REQUIRED_STRATEGIES:
            if not screenshot_paths:
                errors.append(f"{issue_id}: screenshot_strategy {strategy} requires screenshot_path")
            for field in ["screenshot_location", "evidence_point", "red_box_target", "context_required", "screenshot_quality"]:
                if not present(issue.get(field)):
                    errors.append(f"{issue_id}: screenshot_strategy {strategy} requires {field}")
            if strategy == "single" and len(screenshot_paths) != 1:
                errors.append(f"{issue_id}: screenshot_strategy single requires exactly one screenshot path")
            if strategy == "multiple" and len(screenshot_paths) < 2:
                errors.append(f"{issue_id}: screenshot_strategy multiple requires at least two screenshots")
            if modern and strategy == "multiple" and not present(issue.get("screenshot_reason")):
                errors.append(f"{issue_id}: screenshot_strategy multiple requires screenshot_reason")
            if strategy == "shared" and not present(issue.get("screenshot_reason")):
                errors.append(f"{issue_id}: screenshot_strategy shared requires screenshot_reason")
            declared = issue.get("screenshot_count", "").strip()
            if declared:
                try:
                    if int(declared) != len(screenshot_paths):
                        errors.append(f"{issue_id}: screenshot_count does not match screenshot_path count")
                except ValueError:
                    errors.append(f"{issue_id}: screenshot_count must be an integer")
        elif issue.get("needs_screenshot", "").strip().lower() in {"yes", "y", "true", "1"}:
            if not screenshot_paths:
                errors.append(f"{issue_id}: screenshot required but screenshot_path is missing")
            if not present(issue.get("screenshot_location")):
                errors.append(f"{issue_id}: screenshot required but screenshot_location is missing")

        for screenshot in screenshot_paths:
            if not screenshot.exists():
                errors.append(f"{issue_id}: screenshot_path does not exist: {screenshot}")
                continue
            if screenshot.stat().st_size == 0:
                errors.append(f"{issue_id}: screenshot_path is empty: {screenshot}")
                continue
            size = image_size(screenshot)
            if size is None:
                warnings.append(f"{issue_id}: screenshot size could not be read: {screenshot}")
            else:
                width, height = size
                if width < 80 or height < 80:
                    errors.append(f"{issue_id}: screenshot is too small: {screenshot} ({width}x{height})")
                if max(width / height, height / width) > 30:
                    errors.append(f"{issue_id}: screenshot aspect ratio is abnormal: {screenshot} ({width}x{height})")
        opinion_type = issue.get("opinion_type", "").strip()
        if opinion_type not in VALID_OPINION_TYPES:
            errors.append(f"{issue_id}: invalid opinion_type: {opinion_type}")
        gate = validation_ids.get(issue_id)
        if not gate:
            errors.append(f"{issue_id}: missing validation_log row")
        elif gate.get("result", "").strip() != "通过":
            errors.append(f"{issue_id}: validation result is not 通过")
        else:
            required_gate_fields = V16_GATE_FIELDS if v16 else V14_GATE_FIELDS if v14plus else V12_GATE_FIELDS if modern else V11_GATE_FIELDS if v11 else LEGACY_GATE_FIELDS
            if required_gate_fields.issubset(validation_fields):
                for column in required_gate_fields:
                    if gate.get(column, "").strip() != "通过":
                        errors.append(f"{issue_id}: {column} is not 通过")
            if v16:
                if gate.get("gate_origin", "").strip() != "agent":
                    errors.append(f"{issue_id}: v1.6 gate_origin must be agent")
                if gate.get("stage_completion", "").strip() != "AI初审完成":
                    errors.append(f"{issue_id}: v1.6 stage_completion must be AI初审完成")
                if not valid_iso_datetime(gate.get("completed_at")):
                    errors.append(f"{issue_id}: v1.6 completed_at must be an ISO date/time")
                for forbidden in ["reviewer_confirmation", "reviewer_name", "reviewed_at", "independent_review_check"]:
                    if present(gate.get(forbidden)):
                        errors.append(f"{issue_id}: v1.6 must not record {forbidden}")
            elif v14plus:
                if gate.get("gate_origin", "").strip() != "manual":
                    errors.append(f"{issue_id}: gate_origin must be manual")
                if gate.get("reviewer_confirmation", "").strip() != "已确认":
                    errors.append(f"{issue_id}: reviewer_confirmation must be 已确认")
                if not present(gate.get("reviewer_name")):
                    errors.append(f"{issue_id}: reviewer_name is required")
                if not valid_iso_datetime(gate.get("reviewed_at")):
                    errors.append(f"{issue_id}: reviewed_at must be an ISO date/time")

    if v15plus:
        errors.extend(
            validate_v15_professional_gates(
                root,
                checks,
                rules_by_id,
                fact_ids,
                graphic_rows,
                applicability_rows,
                independent_rows,
                ai_initial=v16,
            )
        )
    if schema_version == "1.7":
        from judgment_evidence import validate as validate_judgment
        errors.extend(validate_judgment(root, checks, rules_by_id, facts_by_id, issues,
                                       {g["chain_id"]: g for g in graphic_rows}))
    if versioned:
        errors.extend(validate_integrity(root, manifest, verified, checks, schema_version))
    if v14plus and require_completion_audit:
        errors.extend(validate_completion_audit(root, catalog_hash, schema_version))
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_workspace", type=Path)
    args = parser.parse_args()
    errors, warnings = validate_workspace(args.project_workspace)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    for warning in warnings:
        print(f"WARN: {warning}")
    print("PASS: review package is ready for Word report generation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
