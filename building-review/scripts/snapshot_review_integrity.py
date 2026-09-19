#!/usr/bin/env python3
"""Snapshot workspace sources and standards used by reportable review issues."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_INDEX = Path(
    os.environ.get(
        "BUILDING_REVIEW_INDEX",
        str(Path.cwd() / "building-review-index" / "knowledge-index.json"),
    )
).expanduser()
DEFAULT_RULE_CATALOG = SKILL_DIR / "generated" / "review-rules.json"
IGNORED_NAMES = {".DS_Store", "Thumbs.db"}


def ignored(path: Path) -> bool:
    return path.name in IGNORED_NAMES or path.name.startswith("~$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def role_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".dwg", ".dxf"}:
        return "drawing_dwg"
    if suffix == ".pdf":
        return "drawing_pdf"
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        return "drawing_image"
    if suffix in {".txt", ".md", ".json", ".csv"}:
        return "extracted_text"
    if suffix in {".doc", ".docx"}:
        return "user_supplement"
    return "other"


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def path_key(value: str) -> str:
    return str(Path(value)).replace("/", "\\").casefold()


def resolve_standard(source: str, entries: list[dict]) -> tuple[dict | None, str | None]:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_workspace", type=Path)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--rule-catalog", type=Path, default=DEFAULT_RULE_CATALOG)
    args = parser.parse_args()
    root = args.project_workspace.resolve()
    manifest_path = root / "review_manifest.json"
    issue_path = root / "issue_candidates.csv"
    errors: list[str] = []
    if not manifest_path.exists():
        errors.append("review_manifest.json is required for an integrity snapshot")
    if not issue_path.exists():
        errors.append("issue_candidates.csv is missing")
    if not args.index.exists():
        errors.append(f"knowledge index not found: {args.index}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema_version = manifest.get("schema_version")
    if schema_version not in {"1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7"}:
        print("FAIL: integrity snapshots require schema_version 1.1 through 1.6")
        return 1
    if schema_version in {"1.4", "1.5", "1.6", "1.7"} and not args.rule_catalog.exists():
        print(f"FAIL: rule catalog not found: {args.rule_catalog}")
        return 1
    index = json.loads(args.index.read_text(encoding="utf-8"))
    if index.get("schema_version") != "1.1" or not index.get("corpus_sha256"):
        print("FAIL: rebuild the knowledge index with schema_version 1.1 first")
        return 1

    source_records: list[dict] = []
    source_dir = root / "source"
    for path in sorted(source_dir.rglob("*")) if source_dir.exists() else []:
        if not path.is_file() or ignored(path):
            continue
        source_records.append(
            {
                "role": role_for(path),
                "path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    used: dict[str, dict] = {}
    for issue in csv_rows(issue_path):
        reportable_status = "ai_ready" if schema_version in {"1.6", "1.7"} else "verified"
        if issue.get("status", "").strip() != reportable_status:
            continue
        if schema_version in {"1.2", "1.3", "1.4", "1.5", "1.6", "1.7"} and issue.get("citation_mode", "").strip().lower() == "none":
            continue
        source = issue.get("standard_source", "").strip()
        if not source:
            errors.append(f"{issue.get('issue_id', '[missing issue_id]')}: missing standard_source")
            continue
        entry, error = resolve_standard(source, index.get("files", []))
        if error:
            errors.append(f"{issue.get('issue_id', '[missing issue_id]')}: {error}")
            continue
        assert entry is not None
        path = Path(entry["absolute_path"])
        if not path.exists():
            errors.append(f"standard file is missing: {entry['relative_path']}")
            continue
        current_hash = sha256_file(path)
        if current_hash != entry.get("sha256") or path.stat().st_size != entry.get("size_bytes"):
            errors.append(f"standard changed since index build: {entry['relative_path']}")
            continue
        used[entry["relative_path"]] = {
            "relative_path": entry["relative_path"],
            "size_bytes": entry["size_bytes"],
            "sha256": entry["sha256"],
        }

    if schema_version in {"1.4", "1.5", "1.6", "1.7"}:
        check_path = root / "check_matrix.csv"
        if not check_path.exists():
            errors.append("check_matrix.csv is missing")
        else:
            for check in csv_rows(check_path):
                if check.get("decision_state", "").strip() != "resolved":
                    continue
                if check.get("discovery_track", "").strip() not in {"technical_compliance", "optimization"}:
                    continue
                if check.get("conclusion", "").strip() not in {"符合", "不符合"}:
                    continue
                source = check.get("standard_source", "").strip()
                if not source:
                    errors.append(f"{check.get('check_id', '[missing check_id]')}: missing standard_source")
                    continue
                entry, error = resolve_standard(source, index.get("files", []))
                if error:
                    errors.append(f"{check.get('check_id', '[missing check_id]')}: {error}")
                    continue
                assert entry is not None
                path = Path(entry["absolute_path"])
                if not path.exists() or sha256_file(path) != entry.get("sha256"):
                    errors.append(f"standard changed since index build: {entry['relative_path']}")
                    continue
                used[entry["relative_path"]] = {
                    "relative_path": entry["relative_path"],
                    "size_bytes": entry["size_bytes"],
                    "sha256": entry["sha256"],
                }

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    manifest["source_integrity"] = source_records
    existing_knowledge = manifest.get("knowledge_snapshot", {})
    manifest["knowledge_snapshot"] = {
        "required_layers": existing_knowledge.get("required_layers", ["A", "B", "C", "D"] if schema_version in {"1.6", "1.7"} else []),
        "layers": existing_knowledge.get("layers", {}),
        "index_path": str(args.index.resolve()),
        "index_sha256": sha256_file(args.index),
        "generated_at": index.get("generated_at", ""),
        "corpus_sha256": index["corpus_sha256"],
        "total_files": index.get("total_files", 0),
        "specialty_count": index.get("specialty_count", 0),
        "used_standards": [used[key] for key in sorted(used)],
    }
    if schema_version in {"1.4", "1.5", "1.6", "1.7"}:
        manifest["rule_catalog_snapshot"] = {
            "path": str(args.rule_catalog.resolve()),
            "sha256": sha256_file(args.rule_catalog),
        }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: snapshotted {len(source_records)} source files and {len(used)} standards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
