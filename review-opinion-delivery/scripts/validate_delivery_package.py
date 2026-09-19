#!/usr/bin/env python3
"""Validate an opinion-delivery manifest before Word editing or generation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

from opinion_types import classify


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
SOURCE_ROLES = {
    "reviewer_note",
    "marked_pdf",
    "marked_dwg",
    "approved_docx",
    "user_screenshot",
    "other",
}
IGNORED_SOURCE_NAMES = {".ds_store", "thumbs.db"}
GENERAL_CHECKS = [
    "note_transcription_check",
    "author_intent_check",
    "drawing_reference_check",
    "numeric_scope_check",
    "marked_location_check",
    "regulation_check",
    "opinion_type_check",
    "editorial_change_check",
]
EDIT_LOG_FIELDS = {"item_id", "item_no", "field", "before", "after", "reason", "result"}


def present(value) -> bool:
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return bool(str(value or "").strip())


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def values(value) -> list:
    return value if isinstance(value, list) else [value]


def evidence_images(item: dict) -> list[dict]:
    if "evidence_images" in item:
        value = item.get("evidence_images")
        return value if isinstance(value, list) else []
    screenshot = item.get("screenshot")
    return [screenshot] if isinstance(screenshot, dict) and screenshot else []


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def ignored_source(path: Path) -> bool:
    return path.name.startswith("~$") or path.name.casefold() in IGNORED_SOURCE_NAMES


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_source_path(raw: str) -> str:
    return raw.replace("\\", "/").strip()


def validate_source_integrity(root: Path, manifest: dict, errors: list[str]) -> None:
    source_root = (root / "source").resolve()
    entries = manifest.get("source_integrity")
    if not isinstance(entries, list) or not entries:
        errors.append("Manifest v1.1/v1.2/v1.3 requires a non-empty source_integrity array")
        return
    if not source_root.is_dir():
        errors.append(f"Source directory not found: {source_root}")
        return

    tracked: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        label = f"source_integrity[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry must be an object")
            continue
        role = str(entry.get("role", "")).strip()
        if role not in SOURCE_ROLES:
            errors.append(f"{label}: invalid role: {role}")
        relative_text = normalized_source_path(str(entry.get("path", "")))
        if not relative_text or relative_text.startswith("/") or not relative_text.startswith("source/"):
            errors.append(f"{label}: path must be relative and start with source/: {relative_text}")
            continue
        relative = Path(*relative_text.split("/"))
        if ".." in relative.parts:
            errors.append(f"{label}: path cannot contain '..': {relative_text}")
            continue
        if relative_text in tracked:
            errors.append(f"{label}: duplicate path: {relative_text}")
            continue
        tracked.add(relative_text)
        path = (root / relative).resolve()
        try:
            path.relative_to(source_root)
        except ValueError:
            errors.append(f"{label}: path escapes source/: {relative_text}")
            continue
        if not path.exists() or not path.is_file() or path.is_symlink():
            errors.append(f"{label}: source file not found, not regular, or symlinked: {path}")
            continue
        try:
            expected_size = int(entry.get("size_bytes"))
        except (TypeError, ValueError):
            errors.append(f"{label}: size_bytes must be an integer")
        else:
            if path.stat().st_size != expected_size:
                errors.append(f"{label}: source size changed: {relative_text}")
        expected_hash = str(entry.get("sha256", "")).strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            errors.append(f"{label}: sha256 must be 64 hexadecimal characters")
        elif sha256(path) != expected_hash:
            errors.append(f"{label}: source hash changed: {relative_text}")

    actual = {
        path.relative_to(root).as_posix()
        for path in source_root.rglob("*")
        if path.is_file() and not ignored_source(path)
    }
    missing = sorted(tracked - actual)
    untracked = sorted(actual - tracked)
    if missing:
        errors.append(f"Source snapshot contains missing files: {missing}")
    if untracked:
        errors.append(f"Source directory contains untracked files: {untracked}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    errors: list[str] = []

    manifest_path = root / "delivery_manifest.json"
    log_path = root / "verification_log.csv"
    if not manifest_path.exists():
        errors.append("Missing delivery_manifest.json")
    if not log_path.exists():
        errors.append("Missing verification_log.csv")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema_version = str(manifest.get("schema_version", "1.0"))
    if schema_version not in {"1.0", "1.1", "1.2", "1.3"}:
        errors.append(f"Unsupported schema_version: {schema_version}")
    for field in ["project_name", "report_title", "report_date", "sections", "items"]:
        if not manifest.get(field):
            errors.append(f"Manifest missing {field}")

    if schema_version in {"1.1", "1.2", "1.3"}:
        validate_source_integrity(root, manifest, errors)
    if schema_version in {"1.2", "1.3"}:
        edit_log_path = root / "edit_log.csv"
        if not edit_log_path.exists():
            errors.append("Manifest v1.2 requires edit_log.csv")
        else:
            with edit_log_path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                fields = set(reader.fieldnames or [])
                if not EDIT_LOG_FIELDS.issubset(fields):
                    errors.append(f"edit_log.csv missing fields: {sorted(EDIT_LOG_FIELDS - fields)}")
                for row_number, row in enumerate(reader, start=2):
                    if row.get("result", "").strip() not in {"", "已修改"}:
                        errors.append(f"edit_log.csv row {row_number}: result must be 已修改")

    section_rows = manifest.get("sections", [])
    sections = [row.get("heading", "").strip() if isinstance(row, dict) else str(row).strip() for row in section_rows]
    if not all(sections) or len(sections) != len(set(sections)):
        errors.append("Manifest sections must be unique non-empty headings")

    items = manifest.get("items", [])
    if not items:
        errors.append("Manifest has no reviewer-authored items")
    numbers = [item.get("item_no") for item in items]
    if numbers != list(range(1, len(items) + 1)):
        errors.append(f"Item numbers must be continuous and ordered from 1: {numbers}")

    item_ids: list[str] = []
    if schema_version in {"1.1", "1.2", "1.3"}:
        item_ids = [str(item.get("item_id", "")).strip() for item in items]
        for item_id in item_ids:
            if not re.fullmatch(r"OP-\d{3,}", item_id):
                errors.append(f"Invalid v1.1/v1.2/v1.3 item_id: {item_id!r}")
        if len(item_ids) != len(set(item_ids)):
            errors.append(f"v1.1/v1.2/v1.3 item_id values must be unique: {item_ids}")

    log_rows = read_csv(log_path)
    log_field = "item_id" if schema_version in {"1.1", "1.2", "1.3"} else "item_no"
    log_keys = [row.get(log_field, "").strip() for row in log_rows if present(row.get(log_field))]
    if len(log_keys) != len(set(log_keys)):
        errors.append(f"verification_log.csv has duplicate {log_field} values: {log_keys}")
    logs = {row.get(log_field, "").strip(): row for row in log_rows if present(row.get(log_field))}

    expected_log_keys: set[str] = set()
    for index, item in enumerate(items):
        item_no = item.get("item_no")
        item_id = item_ids[index] if schema_version in {"1.1", "1.2", "1.3"} and index < len(item_ids) else ""
        label = f"Item {item_id or item_no}"
        if item.get("section", "").strip() not in sections:
            errors.append(f"{label}: invalid section: {item.get('section', '')}")
        for field in [
            "source_note_ref",
            "marked_location_ref",
            "drawing_refs",
            "opinion_text",
            "regulation_text",
            "opinion_type",
            "editorial_change_note",
        ]:
            if not present(item.get(field)):
                errors.append(f"{label}: missing {field}")
        if item.get("reviewer_confirmed") is not True:
            errors.append(f"{label}: reviewer_confirmed must be true before delivery")

        opinion_status, normalized_type = classify(str(item.get("opinion_type", "")))
        if opinion_status == "alias":
            errors.append(
                f"{label}: opinion_type requires deterministic correction to {normalized_type!r}; "
                "run normalize_opinion_types.py"
            )
        elif opinion_status == "invalid":
            errors.append(f"{label}: invalid or ambiguous opinion_type requires reviewer confirmation")

        if "evidence_images" in item and not isinstance(item.get("evidence_images"), list):
            errors.append(f"{label}: evidence_images must be an array")
        evidence = evidence_images(item)
        if schema_version in {"1.2", "1.3"} and present(item.get("image_count")):
            try:
                if int(item["image_count"]) != len(evidence):
                    errors.append(f"{label}: image_count must equal evidence_images length")
            except (TypeError, ValueError):
                errors.append(f"{label}: image_count must be an integer")

        has_pdf_evidence = False
        for evidence_index, screenshot in enumerate(evidence, start=1):
            evidence_label = f"{label} evidence[{evidence_index}]"
            if not isinstance(screenshot, dict):
                errors.append(f"{evidence_label}: evidence entry must be an object")
                continue
            strategy = str(screenshot.get("strategy", "pdf_provenance")).strip()
            if strategy == "preserve_approved_docx":
                for field in ["source_docx", "source_item_ref"]:
                    if not present(screenshot.get(field)):
                        errors.append(f"{evidence_label}: preserved evidence missing {field}")
                if present(screenshot.get("source_docx")):
                    source_docx = resolve(root, str(screenshot["source_docx"]))
                    if source_docx.suffix.lower() != ".docx":
                        errors.append(f"{evidence_label}: preserved evidence source must be DOCX: {source_docx}")
                    elif not source_docx.exists() or source_docx.stat().st_size == 0:
                        errors.append(f"{evidence_label}: preserved source DOCX not found or empty: {source_docx}")
                continue
            if strategy != "pdf_provenance":
                errors.append(f"{evidence_label}: unsupported strategy: {strategy}")
                continue
            has_pdf_evidence = True
            for field in ["image_path", "source_pdf", "source_page", "crop_box", "red_box_target"]:
                if not present(screenshot.get(field)):
                    errors.append(f"{evidence_label}: PDF evidence missing {field}")
            if present(screenshot.get("image_path")):
                image_path = resolve(root, screenshot["image_path"])
                if image_path.suffix.lower() not in IMAGE_SUFFIXES:
                    errors.append(f"{evidence_label}: evidence image must be PNG or JPEG: {image_path}")
                elif not image_path.exists() or image_path.stat().st_size == 0:
                    errors.append(f"{evidence_label}: evidence image not found or empty: {image_path}")
            if present(screenshot.get("source_pdf")):
                for raw_pdf in values(screenshot["source_pdf"]):
                    pdf_path = resolve(root, str(raw_pdf))
                    if pdf_path.suffix.lower() != ".pdf":
                        errors.append(f"{evidence_label}: screenshot provenance must be a PDF: {pdf_path}")
                    elif not pdf_path.exists() or pdf_path.stat().st_size == 0:
                        errors.append(f"{evidence_label}: source PDF not found or empty: {pdf_path}")
            if present(screenshot.get("source_page")):
                for raw_page in values(screenshot["source_page"]):
                    try:
                        if int(raw_page) < 1:
                            raise ValueError
                    except (TypeError, ValueError):
                        errors.append(f"{evidence_label}: source_page must contain positive 1-based integers")
            crop = str(screenshot.get("crop_box", ""))
            if crop and len(re.findall(r"-?\d+(?:\.\d+)?", crop)) < 4:
                errors.append(f"{evidence_label}: crop_box must contain at least four coordinates")

        log_key = item_id if schema_version in {"1.1", "1.2", "1.3"} else str(item_no)
        expected_log_keys.add(log_key)
        log = logs.get(log_key)
        if not log:
            errors.append(f"{label}: missing verification_log.csv row")
            continue
        if schema_version in {"1.1", "1.2", "1.3"} and log.get("item_no", "").strip() != str(item_no):
            errors.append(f"{label}: verification item_no does not match manifest")
        for check in GENERAL_CHECKS:
            if log.get(check, "").strip() != "通过":
                errors.append(f"{label}: {check} is not 通过")
        provenance = log.get("pdf_provenance_check", "").strip()
        expected = {"通过"} if has_pdf_evidence else {"不适用", "通过"}
        if provenance not in expected:
            errors.append(f"{label}: pdf_provenance_check must be {'通过' if has_pdf_evidence else '不适用/通过'}")
        if log.get("result", "").strip() != "通过":
            errors.append(f"{label}: verification result is not 通过")

    unknown_logs = sorted(set(logs) - expected_log_keys)
    if unknown_logs:
        errors.append(f"verification_log.csv has unknown item keys: {unknown_logs}")

    if schema_version == "1.3":
        from delivery_contract import validate_contract
        errors.extend(validate_contract(root, manifest))

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: delivery package is ready for Word editing or generation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
