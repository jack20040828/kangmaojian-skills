#!/usr/bin/env python3
"""Search the building-review knowledge index, optionally reopening routed files."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from build_knowledge_index import read_text

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_INDEX = Path(
    os.environ.get(
        "BUILDING_REVIEW_INDEX",
        str(Path.cwd() / "building-review-index" / "knowledge-index.json"),
    )
).expanduser()


def load_index(path: Path) -> dict:
    if not path.exists():
        print(f"Index not found: {path}", file=sys.stderr)
        print("Run scripts/build_knowledge_index.py first.", file=sys.stderr)
        raise SystemExit(2)
    return json.loads(path.read_text(encoding="utf-8"))


def score(item: dict, terms: list[str], text: str | None = None) -> int:
    sample = item.get("text_sample", "") if text is None else text
    total = 0
    for term in terms:
        needle = term.lower()
        if needle in item.get("name", "").lower():
            total += 8
        if needle in item.get("relative_path", "").lower():
            total += 5
        if needle in sample.lower():
            total += 3
        if needle in item.get("specialty", "").lower() or needle in item.get("role", "").lower():
            total += 1
    return total


def snippet(text: str, term: str, width: int = 220) -> str:
    if not text:
        return ""
    lower = text.lower()
    index = lower.find(term.lower())
    if index < 0:
        return text[:width].replace("\n", " ")
    start = max(0, index - width // 2)
    end = min(len(text), index + width // 2)
    return text[start:end].replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terms", nargs="+", help="keywords to search")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="replace")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--role", default="", help="optional normalized role filter")
    parser.add_argument("--specialty", default="", help="optional specialty filter")
    parser.add_argument("--deep", action="store_true", help="reopen files for a deeper routed search")
    args = parser.parse_args()
    if args.deep and not args.specialty:
        parser.error("--deep requires --specialty to avoid scanning the full knowledge base")

    index = load_index(args.index)
    results: list[tuple[int, dict, str]] = []
    unreadable = 0
    for item in index.get("files", []):
        if args.role and args.role not in item.get("role", ""):
            continue
        if args.specialty and args.specialty not in item.get("specialty", ""):
            continue
        searchable_text = item.get("text_sample", "")
        if args.deep:
            path = Path(item.get("absolute_path", ""))
            searchable_text = read_text(path, limit=200000, max_pdf_pages=200) if path.exists() else ""
            if not searchable_text and item.get("kind") == "pdf":
                unreadable += 1
        item_score = score(item, args.terms, searchable_text)
        if item_score:
            results.append((item_score, item, searchable_text))
    results.sort(key=lambda pair: (-pair[0], pair[1].get("relative_path", "")))

    for rank, (item_score, item, searchable_text) in enumerate(results[: args.limit], start=1):
        print(f"[{rank}] score={item_score} {item.get('id', '')} {item.get('role', '')} {item.get('kind', '')}")
        print(f"专项: {item.get('specialty', '')}")
        print(f"文件: {item.get('relative_path', '')}")
        print(f"路径: {item.get('absolute_path', '')}")
        if item.get("sha256"):
            print(f"SHA-256: {item['sha256']}")
        result_snippet = snippet(searchable_text, args.terms[0])
        if result_snippet:
            print(f"片段: {result_snippet}")
        elif item.get("kind") == "pdf":
            print("文本状态: 需视觉/OCR核验")
        print()
    print(f"Total matches: {len(results)}")
    if args.deep and unreadable:
        print(f"Deep unreadable PDF candidates: {unreadable}; require visual/OCR verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
