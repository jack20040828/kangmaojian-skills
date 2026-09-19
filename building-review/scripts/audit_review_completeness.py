#!/usr/bin/env python3
"""Write a hash-bound v1.4-v1.6 completion audit and list all blocking open items."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from validate_review_package import sha256_file, validate_workspace, workspace_input_hashes


def category(error: str) -> str:
    text = error.casefold()
    if "project_profile" in text or "route" in text or "discovery track" in text:
        return "project_profile"
    if "drawing" in text or "coverage" in text or "图纸" in text:
        return "drawing_coverage"
    if "atomic" in text or "rule" in text or "check" in text:
        return "atomic_checks"
    if "standard" in text or "knowledge" in text or "规范" in text:
        return "standards"
    if "issue" in text or "opinion" in text:
        return "issues"
    if "source" in text or "snapshot" in text or "integrity" in text:
        return "integrity"
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_workspace", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.project_workspace.resolve()
    output = args.output or root / "completion_audit.json"
    errors, warnings = validate_workspace(root, require_completion_audit=False)
    manifest_path = root / "review_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    if str(manifest.get("schema_version", "")) not in {"1.4", "1.5", "1.6", "1.7"}:
        errors.append("completion audit is available only for schema_version 1.4, 1.5, or 1.6")
    catalog_path = Path(str(manifest.get("rule_catalog_snapshot", {}).get("path", "")))
    catalog_hash = sha256_file(catalog_path) if catalog_path.exists() else ""
    grouped: dict[str, list[str]] = {}
    for error in errors:
        grouped.setdefault(category(error), []).append(error)
    payload = {
        "schema_version": "1.0",
        "workspace_schema_version": str(manifest.get("schema_version", "")),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "pass" if not errors else "fail",
        "input_hashes": workspace_input_hashes(root),
        "rule_catalog_sha256": catalog_hash,
        "open_items": grouped,
        "errors": errors,
        "warnings": warnings,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        print(f"FAIL: {len(errors)} blocking item(s); audit written to {output}")
        for name, items in sorted(grouped.items()):
            print(f"- {name}: {len(items)}")
            for item in items:
                print(f"  - {item}")
        return 1
    print(f"PASS: completion audit written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
