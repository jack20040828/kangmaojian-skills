#!/usr/bin/env python3
"""Load and deterministically normalize the delivery opinion-type taxonomy."""

from __future__ import annotations

import json
import re
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
TAXONOMY_PATH = SKILL_ROOT / "references" / "opinion-types.json"
LABEL = "【意见类型】："


def load_taxonomy() -> tuple[set[str], dict[str, str]]:
    data = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    canonical = {str(value).strip() for value in data["canonical_types"]}
    aliases = {str(key).strip(): str(value).strip() for key, value in data.get("aliases", {}).items()}
    if not canonical or not all(value in canonical for value in aliases.values()):
        raise ValueError("Opinion-type taxonomy is empty or contains an alias with a non-canonical target")
    return canonical, aliases


def strip_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith(LABEL):
        text = text[len(LABEL) :].strip()
    return text.rstrip("。.").strip()


def normalize_typography(value: str) -> str:
    text = strip_label(value)
    text = re.sub(r"\s+", "", text)
    return (
        text.replace(",", "，")
        .replace("(", "（")
        .replace(")", "）")
        .replace("必须修政", "必须修改")
        .replace("建议修政", "建议修改")
    )


def classify(value: str) -> tuple[str, str]:
    """Return (status, normalized value): canonical, alias, or invalid."""
    canonical, aliases = load_taxonomy()
    normalized = normalize_typography(value)
    if normalized in canonical:
        original = strip_label(value)
        status = "canonical" if original == normalized else "alias"
        return status, normalized
    if normalized in aliases:
        return "alias", aliases[normalized]
    return "invalid", normalized


def with_original_label(original: str, normalized: str) -> str:
    return f"{LABEL}{normalized}" if str(original or "").strip().startswith(LABEL) else normalized
