#!/usr/bin/env python3
"""Render every PDF page to PNG and initialize a fresh report QA ledger."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pypdfium2 as pdfium


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--dpi", type=int, default=180)
    parser.add_argument("--qa-csv", type=Path)
    parser.add_argument("--docx", type=Path)
    args = parser.parse_args()

    pdf_path = args.pdf.resolve()
    output_dir = args.output_dir.resolve()
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise FileNotFoundError(f"PDF not found or empty: {pdf_path}")
    if args.dpi < 96:
        raise ValueError("Use at least 96 DPI for page QA")

    output_dir.mkdir(parents=True, exist_ok=True)
    document = pdfium.PdfDocument(pdf_path)
    render_paths: list[Path] = []
    for index, page in enumerate(document, start=1):
        image = page.render(scale=args.dpi / 72).to_pil()
        output = output_dir / f"page-{index:03d}.png"
        image.save(output, dpi=(args.dpi, args.dpi), optimize=True)
        render_paths.append(output)
        print(output)

    if args.qa_csv:
        qa_path = args.qa_csv.resolve()
        qa_path.parent.mkdir(parents=True, exist_ok=True)
        from page_qa_integrity import EXTRA_CHECKS, enabled, snapshot
        extra = EXTRA_CHECKS if enabled(qa_path) else []
        if extra:
            snapshot(qa_path, args.docx.resolve() if args.docx else None, pdf_path, render_paths)
        with qa_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=QA_HEADERS+extra)
            writer.writeheader()
            for index, render_path in enumerate(render_paths, start=1):
                writer.writerow(
                    {
                        "report_docx": str(args.docx.resolve()) if args.docx else "",
                        "report_pdf": str(pdf_path),
                        "page_no": index,
                        "render_path": str(render_path),
                        "visual_check": "待检查",
                        "section_check": "待检查",
                        "issue_block_check": "待检查",
                        "image_readability_check": "待检查",
                        "overflow_check": "待检查",
                        "page_number_check": "待检查",
                        "result": "待检查",
                        "notes": "",
                        **{field: "待检查" for field in extra},
                    }
                )
        print(qa_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
