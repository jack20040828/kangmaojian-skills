#!/usr/bin/env python3
"""Capture SHA-256 metadata for every preserved file under a v1.1/v1.2/v1.3 source directory."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROLE_BY_DIRECTORY = {
    "notes": "reviewer_note",
    "pdf": "marked_pdf",
    "dwg": "marked_dwg",
    "docx": "approved_docx",
    "screenshots": "user_screenshot",
}
IGNORED_NAMES = {".ds_store", "thumbs.db"}


def ignored(path: Path) -> bool:
    return path.name.startswith("~$") or path.name.casefold() in IGNORED_NAMES


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def infer_role(relative: Path) -> str:
    parts = relative.parts
    return ROLE_BY_DIRECTORY.get(parts[1].casefold(), "other") if len(parts) > 1 else "other"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()

    root = args.workspace.resolve()
    manifest_path = root / "delivery_manifest.json"
    source_root = root / "source"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    if not source_root.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_root}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if str(manifest.get("schema_version", "")) not in {"1.1", "1.2", "1.3"}:
        raise ValueError("Source integrity snapshots require schema_version 1.1, 1.2 or 1.3")

    entries: list[dict[str, object]] = []
    for path in sorted(source_root.rglob("*"), key=lambda value: str(value).casefold()):
        if not path.is_file() or ignored(path):
            continue
        if path.is_symlink():
            raise ValueError(f"Source symlinks are not allowed: {path}")
        relative = path.relative_to(root)
        entries.append(
            {
                "role": infer_role(relative),
                "path": relative.as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    if not entries:
        raise ValueError("No preserved source files found under source/")

    manifest["source_integrity"] = entries
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(manifest_path)
    print(f"PASS: captured {len(entries)} preserved source files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
