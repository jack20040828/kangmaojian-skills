#!/usr/bin/env python3
"""Initialize, record, and validate rendered-page QA for a review DOCX."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_or_absolute(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def resolve_recorded(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate(root: Path, qa_path: Path) -> list[str]:
    if not qa_path.exists():
        return [f"QA record not found: {qa_path}"]
    try:
        qa = load(qa_path)
    except Exception:
        return ["report_qa.json is invalid JSON"]
    errors: list[str] = []
    if qa.get("schema_version") != "1.1":
        errors.append("report QA schema_version must be 1.1")
    docx = resolve_recorded(root, qa.get("docx_path", ""))
    if not docx.exists():
        errors.append(f"QA DOCX is missing: {docx}")
    elif sha256_file(docx) != qa.get("docx_sha256"):
        errors.append("DOCX changed after QA initialization")
    pages = [resolve_recorded(root, value) for value in qa.get("rendered_pages", [])]
    if not pages:
        errors.append("no rendered pages are recorded")
    for page in pages:
        if not page.exists() or page.stat().st_size == 0:
            errors.append(f"rendered page is missing or empty: {page}")
    page_count = qa.get("page_count")
    if page_count != len(pages):
        errors.append("page_count does not match rendered_pages")
    checked = qa.get("checked_pages", [])
    if checked != list(range(1, len(pages) + 1)):
        errors.append("checked_pages must list every page in order")
    if qa.get("content_check") != "通过":
        errors.append("content_check is not 通过")
    if qa.get("visual_check") != "通过":
        errors.append("visual_check is not 通过")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_workspace", type=Path)
    parser.add_argument("--qa", type=Path)
    parser.add_argument("--docx", type=Path)
    parser.add_argument("--render-dir", type=Path)
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--record-content-pass", action="store_true")
    parser.add_argument("--record-visual-pass", action="store_true")
    parser.add_argument("--checked-pages", nargs="*", type=int, default=[])
    args = parser.parse_args()
    root = args.project_workspace.resolve()
    qa_path = (args.qa or root / "report_qa.json").resolve()

    if args.init:
        if not args.docx or not args.render_dir:
            parser.error("--init requires --docx and --render-dir")
        docx = args.docx.resolve()
        pages = sorted(args.render_dir.resolve().glob("*.png"))
        if not docx.exists() or not pages:
            print("FAIL: DOCX and at least one rendered PNG are required")
            return 1
        qa = {
            "schema_version": "1.1",
            "docx_path": relative_or_absolute(docx, root),
            "docx_sha256": sha256_file(docx),
            "rendered_pages": [relative_or_absolute(page, root) for page in pages],
            "page_count": len(pages),
            "checked_pages": [],
            "content_check": "待检查",
            "visual_check": "待检查",
            "notes": "",
        }
        write(qa_path, qa)
        print(f"Initialized pending QA for {len(pages)} pages: {qa_path}")
        return 0

    if args.record_content_pass or args.record_visual_pass:
        if not qa_path.exists():
            print(f"FAIL: QA record not found: {qa_path}")
            return 1
        qa = load(qa_path)
        if args.record_content_pass:
            qa["content_check"] = "通过"
        if args.record_visual_pass:
            expected = list(range(1, int(qa.get("page_count", 0)) + 1))
            if args.checked_pages != expected:
                print(f"FAIL: --checked-pages must be exactly: {' '.join(map(str, expected))}")
                return 1
            qa["checked_pages"] = args.checked_pages
            qa["visual_check"] = "通过"
        write(qa_path, qa)
        print(f"Updated QA record: {qa_path}")
        return 0

    errors = validate(root, qa_path)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: DOCX content and all rendered pages are QA-approved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
