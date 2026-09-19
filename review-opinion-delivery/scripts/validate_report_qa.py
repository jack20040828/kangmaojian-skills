#!/usr/bin/env python3
"""Validate page-by-page visual QA records for the final Word export."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


CHECK_FIELDS = [
    "visual_check",
    "section_check",
    "issue_block_check",
    "image_readability_check",
    "overflow_check",
    "page_number_check",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("qa_csv", type=Path)
    args = parser.parse_args()
    qa_path = args.qa_csv.resolve()
    errors: list[str] = []

    if not qa_path.exists():
        print(f"FAIL: report QA file not found: {qa_path}")
        return 1
    with qa_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    from page_qa_integrity import enabled, errors as integrity_errors
    if enabled(qa_path):
        errors.extend(integrity_errors(qa_path, rows))
    if not rows:
        errors.append("report_qa.csv has no page rows")

    pages: list[int] = []
    pdfs: set[str] = set()
    docx_paths: set[str] = set()
    for row in rows:
        label = f"Page {row.get('page_no', '?')}"
        try:
            page = int(row.get("page_no", ""))
            pages.append(page)
        except ValueError:
            errors.append(f"{label}: page_no must be an integer")
        render = Path(row.get("render_path", ""))
        if not render.exists() or render.stat().st_size == 0:
            errors.append(f"{label}: render_path not found or empty: {render}")
        for field in CHECK_FIELDS:
            if row.get(field, "").strip() != "通过":
                errors.append(f"{label}: {field} is not 通过")
        if row.get("result", "").strip() != "通过":
            errors.append(f"{label}: result is not 通过")
        pdfs.add(row.get("report_pdf", "").strip())
        docx_paths.add(row.get("report_docx", "").strip())

    if pages and pages != list(range(1, len(rows) + 1)):
        errors.append(f"Page numbers must be continuous from 1: {pages}")
    if len(pdfs - {""}) != 1:
        errors.append("All QA rows must refer to the same non-empty report_pdf")
    if len(docx_paths - {""}) != 1:
        errors.append("All QA rows must refer to the same non-empty report_docx")
    for value, label in [(next(iter(pdfs - {""}), ""), "report_pdf"), (next(iter(docx_paths - {""}), ""), "report_docx")]:
        path = Path(value)
        if not path.exists() or path.stat().st_size == 0:
            errors.append(f"{label} not found or empty: {path}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: every rendered report page passed visual QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
