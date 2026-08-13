#!/usr/bin/env python3
"""Suggest architectural specialties from a confirmed profile; never authoritative."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from review_rules import load_profile, normalized, profile_state, profile_value

BASE_SPECIALTIES = [
    "001建筑设计文件编制深度专项",
    "003建筑工程消防专项",
    "005建筑无障碍专项",
    "006建筑防水专项",
    "007建筑节能专项",
    "008建筑环境专项",
    "020绿色建筑专项",
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
]

PROFILE_ROUTES = {
    "food_service": "022饮食建筑专项",
    "dormitory_or_hotel": "012宿舍、旅馆建筑专项",
    "parking": "009车库建筑专项",
    "school": "026中小学校专项",
    "office": "027办公建筑专项",
}

COVERAGE_PACKETS = {
    "001建筑设计文件编制深度专项": [
        "project_identity_function", "project_scope_consistency",
        "code_basis_consistency", "project_applicability",
    ],
    "005建筑无障碍专项": [
        "site_accessible_route", "parking_special_spaces", "accessibility",
        "accessible_elevator", "accessibility_detail",
    ],
    "006建筑防水专项": [
        "wet_room_drainage", "window_sill_drainage", "parapet_flashing", "waterproofing_detail",
    ],
    "012宿舍、旅馆建筑专项": [
        "site_assembly_space", "dormitory_refuse", "dormitory_acoustics",
        "accessible_room", "accessible_room_detail",
    ],
    "022饮食建筑专项": ["food_wet_room_vertical"],
    "026中小学校专项": ["project_identity_function", "site_function_space"],
}

NEGATION_PREFIXES = ("未设置", "不设置", "不含", "无", "非")


def read_fact_text(root: Path) -> str:
    path = root / "fact_ledger.csv"
    if not path.exists():
        return ""
    parts: list[str] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            parts.extend(row.values())
    return " ".join(value or "" for value in parts)


def positive_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for term in terms:
        for found in re.finditer(re.escape(term), text):
            prefix = text[max(0, found.start() - 4):found.start()]
            if not any(prefix.endswith(negative) for negative in NEGATION_PREFIXES):
                matches.append(term)
                break
    return matches


def add_result(results: list[dict], specialty: str, trigger_type: str, matched_terms: list[str], state: str) -> None:
    if any(item["specialty"] == specialty for item in results):
        return
    results.append(
        {
            "specialty": specialty,
            "trigger_type": trigger_type,
            "matched_terms": matched_terms,
            "state": state,
            "required_topics": COVERAGE_PACKETS.get(specialty, []),
        }
    )


def routes_from_profile(profile: dict) -> list[dict]:
    results: list[dict] = []
    for specialty in BASE_SPECIALTIES:
        add_result(results, specialty, "base", [], "candidate")

    industrial_state = profile_state(profile, "industrial_building")
    industrial_value = normalized(profile_value(profile, "industrial_building"))
    if industrial_state == "unknown":
        add_result(results, "004民用建筑专项", "profile", ["industrial_building=unknown"], "uncertain")
        add_result(results, "011工业建筑专项", "profile", ["industrial_building=unknown"], "uncertain")
    elif industrial_value is True:
        add_result(results, "011工业建筑专项", "profile", ["industrial_building=true"], "candidate")
    else:
        add_result(results, "004民用建筑专项", "profile", ["industrial_building=false"], "candidate")

    province = str(profile_value(profile, "location_province"))
    city = str(profile_value(profile, "location_city"))
    if profile_state(profile, "location_province") == "unknown":
        add_result(results, "018湖南省政策规定专项", "jurisdiction", ["province=unknown"], "uncertain")
    elif "湖南" in province:
        add_result(results, "018湖南省政策规定专项", "jurisdiction", [province], "candidate")
    if profile_state(profile, "location_city") == "unknown":
        add_result(results, "019长沙市政策规定专项", "jurisdiction", ["city=unknown"], "uncertain")
    elif "长沙" in city:
        add_result(results, "019长沙市政策规定专项", "jurisdiction", [city], "candidate")

    for field, specialty in PROFILE_ROUTES.items():
        state = profile_state(profile, field)
        value = normalized(profile_value(profile, field))
        if state == "unknown":
            add_result(results, specialty, "profile", [f"{field}=unknown"], "uncertain")
        elif value is True:
            add_result(results, specialty, "profile", [f"{field}=true"], "candidate")
    return results


def routes(text: str) -> list[dict]:
    results: list[dict] = []
    for specialty in BASE_SPECIALTIES:
        add_result(results, specialty, "base", [], "candidate")
    industrial = positive_terms(text, ("工业", "厂房", "仓库"))
    add_result(results, "011工业建筑专项" if industrial else "004民用建筑专项", "building_type", industrial, "candidate")
    for terms, specialty in KEYWORD_ROUTES:
        matched = positive_terms(text, terms)
        if matched:
            add_result(results, specialty, "keyword", matched, "candidate")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_workspace", type=Path)
    parser.add_argument("--json", action="store_true", help="emit candidates with trigger reasons")
    args = parser.parse_args()
    profile_path = args.project_workspace / "project_profile.json"
    if profile_path.exists():
        results = routes_from_profile(load_profile(profile_path))
        profile_used = True
    else:
        results = routes(read_fact_text(args.project_workspace))
        profile_used = False
    if args.json:
        print(json.dumps({"authoritative": False, "profile_used": profile_used, "candidates": results}, ensure_ascii=False, indent=2))
    else:
        for item in results:
            print(f"{item['specialty']}\t{item['state']}")
        print("NOTE: candidate routes only; confirm applicability against project facts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
