#!/usr/bin/env python3
"""Compare two reviewer-opinion DOCX files as semantic opinion blocks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from opinion_types import classify


ITEM_START = re.compile(r"^\s*(\d+)\s*[、.]?\s*涉及图纸\s*[：:]")
SECTION = re.compile(
    r"^\s*(?:[一二三四五六七八九十百]+、\s*)?(设计说明|平面图|立面、剖面图|大样图)\s*[：:]?"
)
FIELD_PATTERNS = {
    "drawing_refs": re.compile(r"涉及图纸\s*[：:]\s*(.*?)(?=【审查意见】\s*[：:]?)", re.S),
    "opinion_text": re.compile(r"【审查意见】\s*[：:]\s*(.*?)(?=【法规条文】\s*[：:]?)", re.S),
    "regulation_text": re.compile(r"【法规条文】\s*[：:]\s*(.*?)(?=【意见类型】\s*[：:]?)", re.S),
    "opinion_type": re.compile(r"【意见类型】\s*[：:]\s*([^\r\n]+)"),
}
FIELD_NAMES = {
    "drawing_refs": "涉及图纸",
    "opinion_text": "审查意见",
    "regulation_text": "法规条文",
    "opinion_type": "意见类型",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def body_paragraphs(doc: Document) -> list[Paragraph]:
    return [Paragraph(element, doc) for element in doc.element.body.iter(qn("w:p"))]


def paragraph_images(paragraph: Paragraph) -> int:
    return len(paragraph._p.xpath(".//a:blip"))


def paragraph_page_breaks(paragraph: Paragraph) -> int:
    return sum(1 for element in paragraph._p.xpath(".//w:br") if element.get(qn("w:type")) == "page")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().rstrip("。")


def similarity(left: str, right: str) -> float:
    compact_left = re.sub(r"\s+", "", left)
    compact_right = re.sub(r"\s+", "", right)
    return SequenceMatcher(None, compact_left, compact_right).ratio()


def drawing_ref_tokens(value: str) -> set[str]:
    text = clean(value).replace("－", "-").casefold()
    codes = set(re.findall(r"[a-z]{1,8}-?[a-z0-9]+", text))
    if codes:
        return codes
    return {token for token in re.split(r"[\s、，,；;]+", text) if len(token) >= 2}


def token_overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def item_similarity(final: dict, draft: dict) -> float:
    opinion_score = similarity(final.get("opinion_text", ""), draft.get("opinion_text", ""))
    drawing_score = token_overlap(
        drawing_ref_tokens(final.get("drawing_refs", "")),
        drawing_ref_tokens(draft.get("drawing_refs", "")),
    )
    type_score = float(clean(final.get("opinion_type", "")) == clean(draft.get("opinion_type", "")))
    section_score = float(clean(final.get("section", "")) == clean(draft.get("section", "")))
    return 0.65 * opinion_score + 0.25 * drawing_score + 0.05 * type_score + 0.05 * section_score


def narrowed_scope(before: dict, after: dict) -> bool:
    before_refs = drawing_ref_tokens(before.get("drawing_refs", ""))
    after_refs = drawing_ref_tokens(after.get("drawing_refs", ""))
    refs_narrowed = bool(before_refs and after_refs and after_refs < before_refs)
    before_text = re.sub(r"\s+", "", before.get("opinion_text", ""))
    after_text = re.sub(r"\s+", "", after.get("opinion_text", ""))
    text_narrowed = bool(
        before_text
        and after_text
        and len(after_text) <= len(before_text) * 0.8
        and similarity(before_text, after_text) >= 0.35
    )
    return refs_narrowed or text_narrowed


def extract_document(path: Path) -> dict:
    doc = Document(path)
    paragraphs = body_paragraphs(doc)
    texts = [paragraph.text.strip() for paragraph in paragraphs]
    section_at: dict[int, str] = {}
    current_section = ""
    for index, text in enumerate(texts):
        match = SECTION.match(text)
        if match and "涉及图纸" not in text:
            current_section = clean(match.group(1))
        section_at[index] = current_section

    starts: list[tuple[int, int]] = []
    for index, text in enumerate(texts):
        match = ITEM_START.match(text)
        if match:
            starts.append((int(match.group(1)), index))

    items: list[dict] = []
    for position, (number, start) in enumerate(starts):
        end = starts[position + 1][1] if position + 1 < len(starts) else len(paragraphs)
        block_text = "\n".join(texts[start:end])
        item = {
            "item_no": number,
            "section": section_at.get(start, ""),
            "image_count": sum(paragraph_images(paragraph) for paragraph in paragraphs[start:end]),
        }
        for field, pattern in FIELD_PATTERNS.items():
            match = pattern.search(block_text)
            item[field] = clean(match.group(1)) if match else ""
        status, normalized_type = classify(item["opinion_type"])
        item["opinion_type_status"] = status
        if status != "canonical":
            item["opinion_type_normalized"] = normalized_type
        items.append(item)

    first_item_index = starts[0][1] if starts else len(paragraphs)
    return {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "item_count": len(items),
        "image_count": sum(paragraph_images(paragraph) for paragraph in paragraphs),
        "page_break_count": sum(paragraph_page_breaks(paragraph) for paragraph in paragraphs),
        "pre_first_item_page_breaks": sum(paragraph_page_breaks(paragraph) for paragraph in paragraphs[:first_item_index]),
        "drawing_refs_with_page_numbers": sum(1 for item in items if "页" in item["drawing_refs"]),
        "items": items,
    }


def count_render_pages(path: Path | None) -> int | None:
    if path is None:
        return None
    return len([entry for entry in path.iterdir() if entry.is_file() and entry.suffix.lower() == ".png"])


def load_mapping(path: Path | None) -> dict:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def auto_mapping(draft_items: list[dict], final_items: list[dict]) -> dict:
    draft_by_no = {item["item_no"]: item for item in draft_items}
    final_by_no = {item["item_no"]: item for item in final_items}
    candidates = sorted(
        (
            (item_similarity(final, draft), final["item_no"], draft["item_no"])
            for final in final_items
            for draft in draft_items
        ),
        reverse=True,
    )
    used_final: set[int] = set()
    used_draft: set[int] = set()
    primary: dict[int, list[int]] = {}
    for score, final_no, draft_no in candidates:
        if score < 0.50:
            break
        if final_no in used_final or draft_no in used_draft:
            continue
        primary[final_no] = [draft_no]
        used_final.add(final_no)
        used_draft.add(draft_no)

    absorbed: dict[int, list[int]] = {}
    mapping_required: list[dict] = []
    matched_finals = set(primary)
    for draft_no in sorted(set(draft_by_no) - used_draft):
        scored = sorted(
            (
                (item_similarity(final_by_no[final_no], draft_by_no[draft_no]), final_no)
                for final_no in matched_finals
            ),
            reverse=True,
        )
        best_score = scored[0][0] if scored else 0.0
        margin = best_score - (scored[1][0] if len(scored) > 1 else 0.0)
        if scored and best_score >= 0.52 and margin >= 0.06:
            absorbed.setdefault(scored[0][1], []).append(draft_no)
            used_draft.add(draft_no)
            continue
        mapping_required.append(
            {
                "kind": "unmatched_draft",
                "item_no": draft_no,
                "possible_final_items": [number for score, number in scored[:3] if score >= 0.30],
            }
        )

    for final_no in sorted(set(final_by_no) - used_final):
        scored = sorted(
            (
                (item_similarity(final_by_no[final_no], draft), draft["item_no"])
                for draft in draft_items
            ),
            reverse=True,
        )
        mapping_required.append(
            {
                "kind": "unmatched_final",
                "item_no": final_no,
                "possible_draft_items": [number for score, number in scored[:3] if score >= 0.30],
            }
        )
    return {"primary": primary, "absorbed": absorbed, "mapping_required": mapping_required}


def normalize_mapping(
    raw: dict, draft_items: list[dict], final_items: list[dict]
) -> tuple[dict[int, list[int]], dict[int, list[int]], list[dict], bool]:
    explicit = "final_to_draft" in raw or "absorbed" in raw
    primary_raw = raw.get("final_to_draft", {})
    primary = {
        int(final_no): [int(value) for value in (draft_nos if isinstance(draft_nos, list) else [draft_nos])]
        for final_no, draft_nos in primary_raw.items()
    }
    if not explicit:
        automatic = auto_mapping(draft_items, final_items)
        return automatic["primary"], automatic["absorbed"], automatic["mapping_required"], False
    absorbed_raw = raw.get("absorbed", {})
    absorbed = {
        int(final_no): [int(value) for value in (draft_nos if isinstance(draft_nos, list) else [draft_nos])]
        for final_no, draft_nos in absorbed_raw.items()
    }
    return primary, absorbed, list(raw.get("mapping_required", [])), True


def build_diff(draft: dict, final: dict, mapping: dict) -> dict:
    draft_by_no = {item["item_no"]: item for item in draft["items"]}
    final_by_no = {item["item_no"]: item for item in final["items"]}
    primary, absorbed, mapping_required, explicit_mapping = normalize_mapping(mapping, draft["items"], final["items"])
    referenced_draft = {number for values in primary.values() for number in values}
    referenced_draft.update(number for values in absorbed.values() for number in values)
    deleted = sorted(set(draft_by_no) - referenced_draft) if explicit_mapping else []
    added = sorted(set(final_by_no) - set(primary) - set(absorbed)) if explicit_mapping else []

    comparisons: list[dict] = []
    field_changes: list[dict] = []
    regulation_changes: list[dict] = []
    type_changes: list[dict] = []
    image_changes: list[dict] = []
    merges: list[dict] = []
    narrowed: list[dict] = []
    for final_no in sorted(final_by_no):
        sources = primary.get(final_no, []) + absorbed.get(final_no, [])
        if not sources:
            continue
        if len(sources) > 1:
            merges.append({"final_item": final_no, "draft_items": sources})
        primary_source = primary.get(final_no, sources)[:1]
        if not primary_source or primary_source[0] not in draft_by_no:
            continue
        draft_no = primary_source[0]
        before = draft_by_no[draft_no]
        after = final_by_no[final_no]
        if narrowed_scope(before, after):
            narrowed.append({"draft_item": draft_no, "final_item": final_no})
        changes: list[dict] = []
        for field in ["drawing_refs", "opinion_text", "regulation_text", "opinion_type", "section"]:
            if clean(before.get(field, "")) != clean(after.get(field, "")):
                change = {
                    "draft_item": draft_no,
                    "final_item": final_no,
                    "field": field,
                    "field_name": FIELD_NAMES.get(field, "章节"),
                    "before": before.get(field, ""),
                    "after": after.get(field, ""),
                }
                changes.append(change)
                field_changes.append(change)
                if field == "regulation_text":
                    regulation_changes.append(change)
                elif field == "opinion_type":
                    type_changes.append(change)
        if before["image_count"] != after["image_count"]:
            image_changes.append(
                {
                    "draft_item": draft_no,
                    "final_item": final_no,
                    "before": before["image_count"],
                    "after": after["image_count"],
                }
            )
        comparisons.append(
            {
                "draft_item": draft_no,
                "final_item": final_no,
                "absorbed_draft_items": absorbed.get(final_no, []),
                "changes": changes,
            }
        )

    anomalies: list[dict] = []
    for version, document in [("draft", draft), ("final", final)]:
        for item in document["items"]:
            if item["opinion_type_status"] != "canonical":
                anomalies.append(
                    {
                        "version": version,
                        "item_no": item["item_no"],
                        "value": item["opinion_type"],
                        "status": item["opinion_type_status"],
                        "normalized": item.get("opinion_type_normalized", ""),
                    }
                )

    regulations_to_no = sorted(
        {change["final_item"] for change in regulation_changes if clean(change["after"]) == "无"}
    )
    return {
        "summary": {
            "draft_items": draft["item_count"],
            "final_items": final["item_count"],
            "draft_images": draft["image_count"],
            "final_images": final["image_count"],
            "deleted_draft_items": deleted,
            "added_final_items": added,
            "merged_final_items": [row["final_item"] for row in merges],
            "regulations_changed_to_no": regulations_to_no,
            "mapping_mode": "explicit" if explicit_mapping else "automatic",
            "mapping_required_count": len(mapping_required),
        },
        "mapping": {str(key): value for key, value in sorted(primary.items())},
        "absorbed": {str(key): value for key, value in sorted(absorbed.items())},
        "comparisons": comparisons,
        "deleted": [draft_by_no[number] for number in deleted],
        "added": [final_by_no[number] for number in added],
        "merges": merges,
        "narrowed": narrowed,
        "mapping_required": mapping_required,
        "field_changes": field_changes,
        "regulation_changes": regulation_changes,
        "opinion_type_changes": type_changes,
        "image_count_changes": image_changes,
        "opinion_type_anomalies": anomalies,
        "upgraded": mapping.get("upgraded", []),
        "reviewer_observations": mapping.get("reviewer_observations", []),
    }


def markdown_report(result: dict) -> str:
    summary = result["summary"]
    draft = result["documents"]["draft"]
    final = result["documents"]["final"]
    def numbers(values: list[int]) -> str:
        return "、".join(str(value) for value in values) if values else "无"

    def item_numbers(values: list[int]) -> str:
        return f"第{numbers(values)}条" if values else "无"

    def page_count(value: int | None) -> str:
        return "未统计" if value is None else str(value)

    def change_text(label: str, before: int | None, after: int | None, unit: str) -> str:
        if before is None or after is None:
            return f"{label}：{page_count(before)}{unit} → {page_count(after)}{unit}"
        verb = "增加至" if after > before else "减少至" if after < before else "保持"
        return f"{label}由{before}{unit}{verb}{after}{unit}" if verb != "保持" else f"{label}保持{before}{unit}"

    merge_text = "；".join(
        f"最终第{row['final_item']}条吸收整理稿第{numbers(row['draft_items'])}条"
        for row in result["merges"]
    ) or "无"
    upgrade_text = "；".join(
        f"整理稿第{row['draft_item']}条 → 最终第{row['final_item']}条（{row.get('note', '内容升级')}）"
        for row in result.get("upgraded", [])
    ) or "无"
    lines = [
        "# 建筑施工图审查意见整理差异复盘",
        "",
        "## 基线",
        "",
        f"- 整理稿：{summary['draft_items']}条意见、{summary['draft_images']}张图片、{page_count(draft.get('page_count'))}页。",
        f"- 最终版：{summary['final_items']}条意见、{summary['final_images']}张图片、{page_count(final.get('page_count'))}页。",
        f"- 整理稿 SHA-256：`{draft['sha256']}`",
        f"- 最终版 SHA-256：`{final['sha256']}`",
        "",
        "## 意见增删与合并",
        "",
        f"- 删除的整理稿独立意见：{item_numbers(summary['deleted_draft_items'])}。",
        f"- 最终版新增意见：{item_numbers(summary['added_final_items'])}。",
        f"- 吸收或合并后的最终意见：{merge_text}。",
        f"- 升级意见：{upgrade_text}。",
        f"- 缩小范围的意见：{item_numbers([row['final_item'] for row in result.get('narrowed', [])])}。",
        f"- 映射方式：{'人工映射（权威）' if summary.get('mapping_mode') == 'explicit' else '自动建议（须复核）'}；待人工确认{summary.get('mapping_required_count', 0)}项。",
        "",
        "## 版式与图纸表达",
        "",
        f"- {change_text('页数', draft.get('page_count'), final.get('page_count'), '页')}，{change_text('图片', summary['draft_images'], summary['final_images'], '张')}。",
        f"- 涉及图纸字段中含页码的意见由{draft['drawing_refs_with_page_numbers']}条降至{final['drawing_refs_with_page_numbers']}条，最终版更偏向图号、图名表达。",
        f"- 首条意见前的显式分页符：整理稿{draft['pre_first_item_page_breaks']}个，最终版{final['pre_first_item_page_breaks']}个；无底稿生成器不应强制独立封面页。",
        *[f"- {value}" for value in result.get("reviewer_observations", [])],
        "",
        "## 字段变化",
        "",
    ]
    for change in result["field_changes"]:
        lines.append(
            f"- 整理稿第{change['draft_item']}条 → 最终第{change['final_item']}条，{change['field_name']}："
            f"“{change['before']}” → “{change['after']}”。"
        )
    if not result["field_changes"]:
        lines.append("- 无。")
    if result.get("mapping_required"):
        lines.extend(["", "## 待人工确认的映射", ""])
        for row in result["mapping_required"]:
            if row["kind"] == "unmatched_draft":
                lines.append(
                    f"- 整理稿第{row['item_no']}条：可能对应最终第{numbers(row.get('possible_final_items', []))}条；不得自动认定为删除。"
                )
            else:
                lines.append(
                    f"- 最终第{row['item_no']}条：可能对应整理稿第{numbers(row.get('possible_draft_items', []))}条；不得自动认定为新增。"
                )
    lines.extend(["", "## 法规与意见类型", ""])
    if result["regulation_changes"]:
        for change in result["regulation_changes"]:
            lines.append(
                f"- 法规：整理稿第{change['draft_item']}条 → 最终第{change['final_item']}条："
                f"“{change['before']}” → “{change['after']}”。"
            )
    else:
        lines.append("- 法规无变化。")
    if summary.get("regulations_changed_to_no"):
        lines.append(f"- 最终版法规明确改为“无”的意见：{item_numbers(summary['regulations_changed_to_no'])}。")
    if result["opinion_type_changes"]:
        for change in result["opinion_type_changes"]:
            lines.append(
                f"- 类型：整理稿第{change['draft_item']}条 → 最终第{change['final_item']}条："
                f"“{change['before']}” → “{change['after']}”。"
            )
    else:
        lines.append("- 意见类型无变化。")
    lines.extend(["", "## 图片差异", ""])
    lines.append(f"- 总图片数：{summary['draft_images']} → {summary['final_images']}。")
    for change in result["image_count_changes"]:
        lines.append(
            f"- 整理稿第{change['draft_item']}条 → 最终第{change['final_item']}条："
            f"{change['before']}张 → {change['after']}张。"
        )
    lines.extend(["", "## 必须处理的异常", ""])
    if result["opinion_type_anomalies"]:
        for anomaly in result["opinion_type_anomalies"]:
            action = f"应确定性修正为“{anomaly['normalized']}”" if anomaly["status"] == "alias" else "需审查人确认后方可交付"
            version = "整理稿" if anomaly["version"] == "draft" else "最终版"
            lines.append(f"- {version}第{anomaly['item_no']}条：类型“{anomaly['value']}”{action}。")
    else:
        lines.append("- 未发现意见类型异常。")
    lines.extend(
        [
            "",
            "## 沉淀规则",
            "",
            "- 最终确认Word是内容与样式最高权威；旧稿已删除内容不得自动回流。",
            "- 明显错字、标点错误和已知意见类型别名必须直接修正并写入编辑日志；未知或多义类型必须阻止交付。",
            "- 不得以纠错名义互换“必须修改”和“建议修改”，也不得改变技术结论、适用范围或责任程度。",
            "- 审查者已确认的“法规条文：无”必须保留；未审定的占位“无”不得直接交付，也不得由本Skill自行检索补写，应转入building-review技术审查阶段确认。",
            "- 默认一个核心问题形成一条意见；平面、立面、门窗等同步要求并入主意见，避免重复拆项。",
            "- 正文优先使用图号和图名；页码、标记号和裁剪坐标保留在证据链及核验日志。",
            "- 有底稿时延续底稿首页、标题、章节编号与图片尺度；无底稿时不强制生成独立封面页。",
            "- 本Skill只整理审查人已有结论；新的技术审图仍由building-review负责。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    parser.add_argument("final", type=Path)
    parser.add_argument("--mapping", type=Path)
    parser.add_argument("--draft-render-dir", type=Path)
    parser.add_argument("--final-render-dir", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    draft = extract_document(args.draft.resolve())
    final = extract_document(args.final.resolve())
    draft["page_count"] = count_render_pages(args.draft_render_dir)
    final["page_count"] = count_render_pages(args.final_render_dir)
    mapping = load_mapping(args.mapping)
    result = build_diff(draft, final, mapping)
    result["documents"] = {"draft": draft, "final": final}

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(markdown_report(result), encoding="utf-8")
    print(args.json_output.resolve())
    print(args.markdown_output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
