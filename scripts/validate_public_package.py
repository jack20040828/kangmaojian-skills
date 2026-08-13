#!/usr/bin/env python3
"""Validate the public repository boundary and both Agent Skills."""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree


SKILLS = ("building-review", "review-opinion-delivery")
TEXT_SUFFIXES = {".md", ".py", ".ps1", ".json", ".yaml", ".yml", ".svg", ".txt"}
FORBIDDEN_TEXT = (
    "D:" + r"\Codex",
    "C:" + "\\Users\\",
    "E:" + r"\沙坪",
    "小金" + "洞",
)
EXPECTED_LINKS = (
    "building-review/SKILL.md",
    "review-opinion-delivery/SKILL.md",
    "media/building-review-workflow.svg",
    "media/review-opinion-delivery-workflow.svg",
)
FORBIDDEN_DOCX_TEXT = ("永州零陵", "永州零零")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def parse_frontmatter(path: Path, errors: list[str]) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        fail(errors, f"{path}: missing YAML frontmatter")
        return {}
    raw = text[4:].split("\n---\n", 1)[0]
    values: dict[str, str] = {}
    keys: list[str] = []
    for line in raw.splitlines():
        if not line.strip() or line.startswith((" ", "\t")):
            continue
        match = re.match(r"^([a-z][a-z0-9_-]*):\s*(.*)$", line)
        if not match:
            fail(errors, f"{path}: unsupported frontmatter line: {line}")
            continue
        key, value = match.groups()
        keys.append(key)
        values[key] = value.strip().strip('"\'')
    if keys != ["name", "description"]:
        fail(errors, f"{path}: frontmatter must contain only name then description")
    if not values.get("description"):
        fail(errors, f"{path}: description is required")
    if len(text.splitlines()) > 500:
        fail(errors, f"{path}: SKILL.md exceeds 500 lines")
    return values


def validate_skill(root: Path, skill: str, errors: list[str]) -> None:
    skill_root = root / skill
    if not skill_root.is_dir():
        fail(errors, f"missing skill directory: {skill}")
        return
    skill_md = skill_root / "SKILL.md"
    agents_yaml = skill_root / "agents" / "openai.yaml"
    if not skill_md.is_file():
        fail(errors, f"{skill}: missing SKILL.md")
        return
    values = parse_frontmatter(skill_md, errors)
    if values.get("name") != skill:
        fail(errors, f"{skill}: frontmatter name must match directory")
    if not agents_yaml.is_file():
        fail(errors, f"{skill}: missing agents/openai.yaml")
    else:
        metadata = agents_yaml.read_text(encoding="utf-8")
        if f"${skill}" not in metadata:
            fail(errors, f"{skill}: default_prompt must mention ${skill}")
        for required in ("display_name:", "short_description:", "default_prompt:"):
            if required not in metadata:
                fail(errors, f"{skill}: openai.yaml missing {required}")
    for extra in ("README.md", "INSTALLATION_GUIDE.md", "CHANGELOG.md"):
        if (skill_root / extra).exists():
            fail(errors, f"{skill}: human-facing {extra} belongs at repository root")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def validate_docx(path: Path, errors: list[str]) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if "docProps/custom.xml" in names:
                fail(errors, f"{path}: custom document properties remain")
            if "docProps/core.xml" in names:
                root = ElementTree.fromstring(archive.read("docProps/core.xml"))
                for node in root.iter():
                    if local_name(node.tag) in {"creator", "lastModifiedBy"} and (node.text or "").strip():
                        fail(errors, f"{path}: author metadata remains in {local_name(node.tag)}")
            for name in names:
                if not name.startswith("word/") or not name.endswith(".xml"):
                    continue
                xml_root = ElementTree.fromstring(archive.read(name))
                story_text = "".join(
                    (node.text or "") for node in xml_root.iter() if local_name(node.tag) == "t"
                )
                for needle in FORBIDDEN_DOCX_TEXT:
                    if needle in story_text:
                        fail(errors, f"{path}: forbidden project text remains in {name}: {needle}")
                for node in xml_root.iter():
                    if any(local_name(key).startswith("rsid") for key in node.attrib):
                        fail(errors, f"{path}: revision session metadata remains in {name}")
                        return
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        fail(errors, f"{path}: invalid DOCX package: {exc}")


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    for required in ("README.md", "README.en.md", "LICENSE", ".gitignore", "sync-manifest.json"):
        if not (root / required).is_file():
            fail(errors, f"missing repository file: {required}")
    for skill in SKILLS:
        validate_skill(root, skill, errors)
    for link in EXPECTED_LINKS:
        if not (root / link).is_file():
            fail(errors, f"README target is missing: {link}")
    for forbidden_dir in ("03_审图项目", "04_审图成果", "review_crops", "修复备份"):
        for path in root.rglob(forbidden_dir):
            if path.is_dir():
                fail(errors, f"forbidden private/generated directory: {path.relative_to(root)}")
    allowed_generated_file = Path("building-review/generated/review-rules.json")
    if not (root / allowed_generated_file).is_file():
        fail(errors, f"missing public runtime catalog: {allowed_generated_file}")
    for generated_dir in root.rglob("generated"):
        if not generated_dir.is_dir():
            continue
        relative_dir = generated_dir.relative_to(root)
        if relative_dir != Path("building-review/generated"):
            fail(errors, f"forbidden private/generated directory: {relative_dir}")
            continue
        for item in generated_dir.rglob("*"):
            relative_item = item.relative_to(root)
            if item.is_dir() or relative_item != allowed_generated_file:
                fail(errors, f"forbidden generated content: {relative_item}")
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix.lower() in {".pyc", ".pyo"}:
            fail(errors, f"cache artifact: {relative}")
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
            for needle in FORBIDDEN_TEXT:
                if needle in text:
                    fail(errors, f"{relative}: forbidden public text: {needle}")
        if path.suffix.lower() == ".docx":
            validate_docx(path, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate_repository(args.root.resolve())
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: public package structure, privacy boundary, links, and DOCX metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
