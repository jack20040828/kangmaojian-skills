#!/usr/bin/env python3
"""Create a workspace for reviewer-authored opinion delivery."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from datetime import date
from pathlib import Path


DEFAULT_ROOT = Path(
    os.environ.get("REVIEW_OPINION_PROJECT_ROOT", str(Path.cwd() / "review-opinion-projects"))
).expanduser()

SECTIONS = [
    "一、设计说明：",
    "二、平面图：",
    "三、立面、剖面图：",
    "四、大样图：",
]

DEFAULT_NOTE = (
    "注：【意见类型】包含消防安全强制性条文、一般性条文、政策规定、设计深度与必须修改（消防安全）组合4种类型；"
    "其它强制性条文、一般性条文、政策规定、设计深度与必须修改（其它）、建议修改（其它）的两两组合共8种类型，共12种意见类型。"
)

VERIFICATION_HEADERS = [
    "item_id",
    "item_no",
    "note_transcription_check",
    "author_intent_check",
    "drawing_reference_check",
    "numeric_scope_check",
    "marked_location_check",
    "pdf_provenance_check",
    "regulation_check",
    "opinion_type_check",
    "editorial_change_check",
    "result",
    "notes",
]

QA_HEADERS = [
    "report_docx",
    "report_pdf",
    "page_no",
    "render_path",
    "visual_check",
    "section_check",
    "issue_block_check",
    "image_readability_check",
    "overflow_check",
    "page_number_check",
    "result",
    "notes",
]

EDIT_HEADERS = [
    "item_id",
    "item_no",
    "field",
    "before",
    "after",
    "reason",
    "result",
]


def slugify(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "-", value.strip())
    value = re.sub(r"\s+", "-", value)
    return value or "未命名项目"


def write_csv(path: Path, headers: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerow(headers)


def chinese_date(value: date) -> str:
    return f"{value.year}年{value.month}月{value.day}日"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_name")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--report-title", default="建筑施工图内审意见")
    parser.add_argument("--report-date", default="")
    parser.add_argument("--schema-version", choices=["1.0", "1.1", "1.2", "1.3"], default="1.3")
    args = parser.parse_args()

    workspace = args.root / f"{date.today().isoformat()}-{slugify(args.project_name)}"
    manifest_path = workspace / "delivery_manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("schema_version", "1.0") != args.schema_version:
            raise SystemExit("Existing workspace has a different schema; no automatic migration")
    for relative in [
        "source/notes",
        "source/dwg",
        "source/pdf",
        "source/docx",
        "source/screenshots",
        "screenshots",
        "renders",
        "output",
    ]:
        (workspace / relative).mkdir(parents=True, exist_ok=True)

    manifest_path = workspace / "delivery_manifest.json"
    if not manifest_path.exists():
        manifest = {
            "schema_version": args.schema_version,
            "project_name": args.project_name,
            "report_title": args.report_title,
            "report_date": args.report_date or chinese_date(date.today()),
            "source_integrity": [],
            "sections": [{"heading": heading, "empty_text": "无意见"} for heading in SECTIONS],
            "footer_note": DEFAULT_NOTE,
            "items": [],
        }
        if args.schema_version == "1.3":
            manifest.update(location_policy={"mode": "drawing_number_title", "authorization_ref": ""},
                            source_items=[], source_conflicts=[], evidence_history=[])
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    for name, headers in [
        ("verification_log.csv", VERIFICATION_HEADERS),
        ("report_qa.csv", QA_HEADERS),
        ("edit_log.csv", EDIT_HEADERS),
    ]:
        path = workspace / name
        if not path.exists():
            write_csv(path, headers)

    print(workspace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
