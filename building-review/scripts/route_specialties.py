#!/usr/bin/env python3
"""Suggest architectural review specialties from facts; output is never authoritative."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

BASE_SPECIALTIES = [
    "001建筑设计文件编制深度专项",
    "003建筑工程消防专项",
    "005建筑无障碍专项",
    "006建筑防水专项",
    "007建筑节能专项",
    "008建筑环境专项",
    "020绿色建筑专项",
    "018湖南省政策规定专项",
    "019长沙市政策规定专项",
]

KEYWORD_ROUTES = [
    (("工业", "厂房", "仓库"), "011工业建筑专项"),
    (("食堂", "餐厅", "厨房", "饮食"), "022饮食建筑专项"),
    (("宿舍", "旅馆", "酒店"), "012宿舍、旅馆建筑专项"),
    (("垃圾", "建筑垃圾", "源头减量", "减源", "材料减量"), "024垃圾减源专项"),
    (("住宅", "住户", "套内"), "013住宅建筑专项"),
    (("车库", "停车", "汽车库"), "009车库建筑专项"),
    (("充电", "电动车", "充电桩"), "029电动车专项"),
    (("幼儿园", "托儿所"), "023幼儿园建筑专项"),
    (("中小学", "学校", "教学楼"), "026中小学校专项"),
    (("办公", "办公室"), "027办公建筑专项"),
    (("医院", "门诊", "病房"), "028医院建筑专项"),
    (("人防", "防空"), "025人防工程专项"),
    (("幕墙",), "017建筑幕墙专项"),
    (("装修", "装饰", "改造"), "010改造装修专项"),
    (("装配式",), "021装配式专项"),
    (("降碳", "碳排放", "低碳"), "018湖南省政策规定专项"),
]


def read_fact_text(root: Path) -> str:
    path = root / "fact_ledger.csv"
    if not path.exists():
        return ""
    parts: list[str] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            parts.extend(row.values())
    return " ".join(value or "" for value in parts)


def routes(text: str) -> list[dict]:
    results = [
        {"specialty": specialty, "trigger_type": "base", "matched_terms": []}
        for specialty in BASE_SPECIALTIES
    ]
    building_specialty = "011工业建筑专项" if any(term in text for term in ("工业", "厂房", "仓库")) else "004民用建筑专项"
    results.append({"specialty": building_specialty, "trigger_type": "building_type", "matched_terms": []})
    existing = {item["specialty"] for item in results}
    for terms, specialty in KEYWORD_ROUTES:
        matched = [term for term in terms if term in text]
        if matched and specialty not in existing:
            results.append({"specialty": specialty, "trigger_type": "keyword", "matched_terms": matched})
            existing.add(specialty)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_workspace", type=Path)
    parser.add_argument("--json", action="store_true", help="emit candidates with trigger reasons")
    args = parser.parse_args()
    results = routes(read_fact_text(args.project_workspace))
    if args.json:
        print(json.dumps({"authoritative": False, "candidates": results}, ensure_ascii=False, indent=2))
    else:
        for item in results:
            print(item["specialty"])
        print("NOTE: candidate routes only; confirm applicability against project facts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
