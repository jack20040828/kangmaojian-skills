#!/usr/bin/env python3
"""Build a hash-backed, searchable index for the building-review knowledge base."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_KNOWLEDGE_BASE = (
    Path(os.environ["BUILDING_REVIEW_KNOWLEDGE_BASE"]).expanduser()
    if os.environ.get("BUILDING_REVIEW_KNOWLEDGE_BASE")
    else None
)
DEFAULT_OUTPUT_DIR = Path(
    os.environ.get("BUILDING_REVIEW_INDEX_DIR", str(Path.cwd() / "building-review-index"))
).expanduser()
SCHEMA_VERSION = "1.1"
IGNORED_NAMES = {".DS_Store", "Thumbs.db"}
TEXT_EXTENSIONS = {".txt", ".md"}
WORD_EXTENSIONS = {".docx"}
OFFICE_EXTENSIONS = {".doc", ".ppt", ".pptx", ".xls", ".xlsx"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def is_ignored(path: Path) -> bool:
    return path.name in IGNORED_NAMES or path.name.startswith("~$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_role(parts: list[str], name: str) -> str:
    haystack = "/".join(parts + [name])
    if "制图标准" in haystack or "共性问题" in haystack:
        return "辅助识图"
    if "政策" in haystack or "规定" in haystack or "通知" in haystack:
        return "政策文件"
    if re.search(r"(^|/)A[^/]*(审查要点|要点)", haystack):
        return "A_审查要点"
    if re.search(r"(^|/)B[^/]*(核心规范|规范|标准)", haystack):
        return "B_核心规范"
    if re.search(r"(^|/)C[^/]*(疑难|解析|问题)", haystack):
        return "C_疑难解析"
    if re.search(r"(^|/)[CD][^/]*(案例|意见|截图|高频)", haystack):
        return "D_案例与截图"
    if "核心规范" in haystack or "通用规范" in haystack or "设计规范" in haystack or "标准" in haystack:
        return "B_核心规范"
    if "审查要点" in haystack:
        return "A_审查要点"
    if "疑难" in haystack or "解析" in haystack:
        return "C_疑难解析"
    if "审查意见" in haystack or "高频" in haystack or "截图" in haystack or "案例" in haystack:
        return "D_案例与截图"
    return "未知待整理"


def read_docx_text(path: Path, limit: int) -> str:
    texts: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for member in sorted(archive.namelist()):
            if not member.startswith("word/") or not member.endswith(".xml"):
                continue
            root = ElementTree.fromstring(archive.read(member))
            for node in root.iter():
                if node.tag.endswith("}t") and node.text:
                    texts.append(node.text)
            if sum(len(text) for text in texts) >= limit:
                break
    return "\n".join(texts)[:limit]


def read_pdf_text(path: Path, limit: int, max_pages: int) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    texts: list[str] = []
    try:
        logging.getLogger("pypdf").setLevel(logging.ERROR)
        reader = PdfReader(str(path))
        for page in reader.pages[:max_pages]:
            texts.append(page.extract_text() or "")
            if sum(len(text) for text in texts) >= limit:
                break
    except Exception:
        return ""
    return "\n".join(texts)[:limit]


def read_text(path: Path, limit: int = 12000, max_pdf_pages: int = 12) -> str:
    suffix = path.suffix.lower()
    try:
        if suffix in TEXT_EXTENSIONS:
            return path.read_text(encoding="utf-8", errors="ignore")[:limit]
        if suffix in WORD_EXTENSIONS:
            return read_docx_text(path, limit)
        if suffix in PDF_EXTENSIONS:
            return read_pdf_text(path, limit, max_pdf_pages)
    except Exception:
        return ""
    return ""


def file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in PDF_EXTENSIONS:
        return "pdf"
    if suffix in WORD_EXTENSIONS or suffix in OFFICE_EXTENSIONS:
        return suffix.lstrip(".") or "office"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in TEXT_EXTENSIONS:
        return suffix.lstrip(".")
    return suffix.lstrip(".") or "unknown"


def extraction_status(path: Path, text: str) -> str:
    if text:
        return "text"
    if path.suffix.lower() == ".pdf":
        return "scan_or_unreadable"
    return "metadata_only"


def build_index(knowledge_base: Path) -> dict:
    files: list[dict] = []
    specialties: dict[str, dict] = {}
    corpus = hashlib.sha256()
    for path in sorted(knowledge_base.rglob("*")):
        if not path.is_file() or is_ignored(path):
            continue
        relative = path.relative_to(knowledge_base)
        parts = list(relative.parts)
        specialty = parts[0] if parts else ""
        text = read_text(path)
        file_hash = sha256_file(path)
        relative_text = relative.as_posix()
        corpus.update(relative_text.encode("utf-8"))
        corpus.update(b"\0")
        corpus.update(file_hash.encode("ascii"))
        corpus.update(b"\n")
        entry = {
            "id": f"K{len(files) + 1:04d}",
            "specialty": specialty,
            "role": normalize_role(parts, path.name),
            "kind": file_kind(path),
            "name": path.name,
            "relative_path": relative_text,
            "absolute_path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": file_hash,
            "text_available": bool(text),
            "extraction_status": extraction_status(path, text),
            "text_sample": text,
        }
        files.append(entry)
        bucket = specialties.setdefault(specialty, {"total": 0, "roles": {}})
        bucket["total"] += 1
        role = entry["role"]
        bucket["roles"][role] = bucket["roles"].get(role, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "knowledge_base": str(knowledge_base),
        "total_files": len(files),
        "specialty_count": len(specialties),
        "corpus_sha256": corpus.hexdigest(),
        "specialties": specialties,
        "files": files,
    }


def write_markdown(index: dict, output_path: Path) -> None:
    lines = [
        "# 建筑审图知识库索引",
        "",
        f"- Schema: `{index['schema_version']}`",
        f"- 生成时间: {index['generated_at']}",
        f"- 知识库: `{index['knowledge_base']}`",
        f"- 专项数: {index['specialty_count']}",
        f"- 文件数: {index['total_files']}",
        f"- 知识库哈希: `{index['corpus_sha256']}`",
        "",
        "## 专项概览",
        "",
        "| 专项 | 文件数 | 资料类型 |",
        "|---|---:|---|",
    ]
    for specialty, info in sorted(index["specialties"].items()):
        roles = ", ".join(f"{role}:{count}" for role, count in sorted(info["roles"].items()))
        lines.append(f"| {specialty} | {info['total']} | {roles} |")
    lines.extend(["", "## 文件清单", ""])
    for item in index["files"]:
        lines.append(
            f"- `{item['id']}` [{item['role']}] `{item['relative_path']}` "
            f"({item['kind']}, {item['extraction_status']}, sha256={item['sha256'][:12]}...)"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-base", type=Path, default=DEFAULT_KNOWLEDGE_BASE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    if args.knowledge_base is None:
        parser.error(
            "pass --knowledge-base or set BUILDING_REVIEW_KNOWLEDGE_BASE; "
            "this public package does not include standards or project knowledge files"
        )
    if not args.knowledge_base.exists():
        parser.error(f"knowledge base not found: {args.knowledge_base}")
    index = build_index(args.knowledge_base.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "knowledge-index.json"
    md_path = args.output_dir / "knowledge-index.md"
    json_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(index, md_path)
    print(f"Indexed {index['total_files']} files across {index['specialty_count']} specialties")
    print(f"Corpus SHA-256: {index['corpus_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
