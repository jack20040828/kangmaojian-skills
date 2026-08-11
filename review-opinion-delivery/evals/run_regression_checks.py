#!/usr/bin/env python3
"""Run anonymous v1.1 delivery regression checks in a temporary workspace."""

from __future__ import annotations

import copy
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw


SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_ROOT / "scripts"
CHECK_FIELDS = [
    "note_transcription_check",
    "author_intent_check",
    "drawing_reference_check",
    "numeric_scope_check",
    "marked_location_check",
    "regulation_check",
    "opinion_type_check",
    "editorial_change_check",
]


def run(script: str, *args: object, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *(str(arg) for arg in args)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if result.returncode != expected:
        raise AssertionError(
            f"{script} returned {result.returncode}, expected {expected}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def write_verification_log(path: Path, items: list[dict]) -> None:
    headers = [
        "item_id",
        "item_no",
        *CHECK_FIELDS[:5],
        "pdf_provenance_check",
        *CHECK_FIELDS[5:],
        "result",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for item in items:
            screenshot = item.get("screenshot")
            row = {
                "item_id": item["item_id"],
                "item_no": item["item_no"],
                "pdf_provenance_check": "通过" if screenshot else "不适用",
                "result": "通过",
                "notes": "匿名回归样例",
            }
            row.update({field: "通过" for field in CHECK_FIELDS})
            writer.writerow(row)


def write_qa(path: Path, docx: Path, pdf: Path, render: Path, value: str) -> None:
    headers = [
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
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerow(
            {
                "report_docx": str(docx),
                "report_pdf": str(pdf),
                "page_no": 1,
                "render_path": str(render),
                "visual_check": value,
                "section_check": value,
                "issue_block_check": value,
                "image_readability_check": value,
                "overflow_check": value,
                "page_number_check": value,
                "result": value,
                "notes": "匿名回归样例",
            }
        )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="review-opinion-v11-") as temporary:
        test_root = Path(temporary)
        created = run("create_delivery_workspace.py", "匿名回归项目", "--root", test_root)
        workspace = Path(created.stdout.strip().splitlines()[-1])
        manifest_path = workspace / "delivery_manifest.json"
        verification_path = workspace / "verification_log.csv"

        (workspace / "source" / "notes" / "reviewer.txt").write_text(
            "匿名审查笔记：原始编号第十二条A与第十二条B。", encoding="utf-8"
        )
        (workspace / "source" / "pdf" / "marked-1.pdf").write_bytes(b"%PDF-1.4\nanonymous fixture 1\n%%EOF")
        (workspace / "source" / "pdf" / "marked-2.pdf").write_bytes(b"%PDF-1.4\nanonymous fixture 2\n%%EOF")
        (workspace / "source" / "docx" / "approved.docx").write_bytes(b"anonymous approved docx source")
        user_image = Image.new("RGB", (80, 50), "white")
        user_image.save(workspace / "source" / "screenshots" / "user.png")

        evidence_path = workspace / "screenshots" / "shared-evidence.png"
        evidence = Image.new("RGB", (640, 360), "white")
        ImageDraw.Draw(evidence).rectangle((120, 80, 500, 280), outline="red", width=8)
        evidence.save(evidence_path)

        run("snapshot_source_integrity.py", workspace)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["schema_version"] = "1.1"
        shared_screenshot = {
            "image_path": "screenshots/shared-evidence.png",
            "source_pdf": ["source/pdf/marked-1.pdf", "source/pdf/marked-2.pdf"],
            "source_page": [1, 1],
            "crop_box": [[0, 0, 100, 100], [0, 0, 100, 100]],
            "red_box_target": "匿名目标位置",
        }
        manifest["items"] = [
            {
                "item_id": "OP-001",
                "item_no": 1,
                "section": "一、设计说明：",
                "source_note_ref": "原笔记第12条",
                "marked_location_ref": "标记PDF第1页",
                "drawing_refs": "SM-01 建筑设计说明",
                "opinion_text": "【审查意见】：按审查人确认文字整理。",
                "regulation_text": "【法规条文】：无",
                "opinion_type": "【意见类型】：一般性条文，必须修改（其它）",
                "editorial_change_note": "仅规范标点。",
                "reviewer_confirmed": True,
                "screenshot": copy.deepcopy(shared_screenshot),
            },
            {
                "item_id": "OP-002",
                "item_no": 2,
                "section": "二、平面图：",
                "source_note_ref": "原笔记第12条",
                "marked_location_ref": "标记PDF第1页",
                "drawing_refs": "A-01 一层平面图",
                "opinion_text": "【审查意见】：保留第二条独立意见。",
                "regulation_text": "【法规条文】：无",
                "opinion_type": "【意见类型】：设计深度，建议修改（其它）",
                "editorial_change_note": "无实质修改。",
                "reviewer_confirmed": True,
                "screenshot": copy.deepcopy(shared_screenshot),
            },
            {
                "item_id": "OP-003",
                "item_no": 3,
                "section": "三、立面、剖面图：",
                "source_note_ref": "原笔记第13条",
                "marked_location_ref": "审查人文字说明",
                "drawing_refs": "A-05 建筑剖面图",
                "opinion_text": "【审查意见】：无截图意见保持原文。",
                "regulation_text": "【法规条文】：无",
                "opinion_type": "【意见类型】：设计深度，必须修改（其它）",
                "editorial_change_note": "无实质修改。",
                "reviewer_confirmed": True,
            },
        ]
        write_manifest(manifest_path, manifest)
        write_verification_log(verification_path, manifest["items"])

        run("validate_delivery_package.py", workspace)
        generated = run("generate_delivery_report.py", workspace)
        docx = Path(generated.stdout.strip().splitlines()[-1])
        if docx.parent != workspace / "output":
            raise AssertionError(f"Unexpected default DOCX output: {docx}")
        run("validate_docx_content.py", workspace, docx)

        original = copy.deepcopy(manifest)
        duplicate_id = copy.deepcopy(original)
        duplicate_id["items"][1]["item_id"] = "OP-001"
        write_manifest(manifest_path, duplicate_id)
        run("validate_delivery_package.py", workspace, expected=1)

        wrong_order = copy.deepcopy(original)
        wrong_order["items"][1]["item_no"] = 3
        write_manifest(manifest_path, wrong_order)
        run("validate_delivery_package.py", workspace, expected=1)

        missing_image = copy.deepcopy(original)
        missing_image["items"][0]["screenshot"]["image_path"] = "screenshots/missing.png"
        write_manifest(manifest_path, missing_image)
        run("validate_delivery_package.py", workspace, expected=1)

        write_manifest(manifest_path, original)
        source_note = workspace / "source" / "notes" / "reviewer.txt"
        source_bytes = source_note.read_bytes()
        source_note.write_bytes(source_bytes + b"changed")
        run("validate_delivery_package.py", workspace, expected=1)
        source_note.write_bytes(source_bytes)
        run("validate_delivery_package.py", workspace)

        untracked = workspace / "source" / "notes" / "untracked.txt"
        untracked.write_text("untracked", encoding="utf-8")
        run("validate_delivery_package.py", workspace, expected=1)
        untracked.unlink()
        run("validate_delivery_package.py", workspace)

        pdf = workspace / "output" / "anonymous.pdf"
        pdf.write_bytes(b"anonymous rendered PDF placeholder")
        render = workspace / "renders" / "page-001.png"
        Image.new("RGB", (200, 280), "white").save(render)
        qa = workspace / "report_qa.csv"
        write_qa(qa, docx, pdf, render, "待检查")
        run("validate_report_qa.py", qa, expected=1)
        write_qa(qa, docx, pdf, render, "通过")
        run("validate_report_qa.py", qa)

    print("PASS: anonymous v1.1 package, DOCX, integrity, ordering, evidence, and QA regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
