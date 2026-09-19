#!/usr/bin/env python3
"""Compose compact formal evidence images from internally PDF-provenanced page renders."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


RED = "#e32020"
INK = "#1f2937"
MUTED = "#5b6472"
LINE = "#d5d9df"
ACCENT = "#1d4f91"
DEFAULT_FONT = Path(r"C:\Windows\Fonts\msyh.ttc")
DEFAULT_BOLD_FONT = Path(r"C:\Windows\Fonts\msyhbd.ttc")


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def load_font(path: Path, size: int):
    if not path.exists():
        raise FileNotFoundError(f"Font not found: {path}")
    return ImageFont.truetype(str(path), size)


def require_box(value, label: str) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{label} must be [left, top, right, bottom]")
    box = tuple(int(x) for x in value)
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError(f"{label} is not a positive rectangle: {box}")
    return box


def build_panel(base: Path, spec: dict, target_width: int) -> Image.Image:
    source_pdf = resolve(base, spec["source_pdf"])
    if source_pdf.suffix.lower() != ".pdf":
        raise ValueError(f"Evidence provenance must be PDF: {source_pdf}")
    if not source_pdf.exists() or source_pdf.stat().st_size == 0:
        raise FileNotFoundError(f"Source PDF not found or empty: {source_pdf}")
    page = int(spec["source_page"])
    if page < 1:
        raise ValueError("source_page is 1-based and must be positive")

    source_image = resolve(base, spec["source_image"])
    if not source_image.exists():
        raise FileNotFoundError(f"Rendered PDF page not found: {source_image}")
    crop = require_box(spec["crop"], "crop")
    with Image.open(source_image) as image:
        if "source_problem_boxes" in spec:
            from evidence_geometry import prepare_crop
            crop, limited = prepare_crop(crop, spec["source_problem_boxes"], image.size)
            spec["resolved_geometry"] = {"crop_box": list(crop), "problem_boxes": spec["source_problem_boxes"],
                                         "source_size": list(image.size), "limited_axes": limited}
        panel = image.convert("RGB").crop(crop)

    draw = ImageDraw.Draw(panel)
    stroke = max(5, round(panel.width / 260))
    boxes = spec.get("red_boxes", [])
    color = spec.get("mark_color", RED)
    if color not in {RED, "red", "#ff0000"} and not spec.get("color_authorization_ref"):
        raise ValueError("Non-red marks require user color authorization")
    if "source_problem_boxes" in spec:
        boxes = [[b[0]-crop[0], b[1]-crop[1], b[2]-crop[0], b[3]-crop[1]] for b in spec["source_problem_boxes"]]
    for index, raw_box in enumerate(boxes, start=1):
        box = require_box(raw_box, f"red_boxes[{index}]")
        draw.rectangle(box, outline=color, width=stroke)

    if panel.width != target_width:
        height = round(panel.height * target_width / panel.width)
        panel = panel.resize((target_width, height), Image.Resampling.LANCZOS)
    return panel


def build_card(base: Path, spec: dict, font_path: Path, bold_font_path: Path) -> Path:
    width = int(spec.get("width", 2000))
    margin = int(spec.get("margin", 40))
    panel_width = width - 2 * margin
    gap = int(spec.get("panel_gap", 28))
    panels = [build_panel(base, panel, panel_width) for panel in spec["panels"]]
    if not panels:
        raise ValueError("Each card requires at least one panel")

    panel_height = sum(panel.height for panel in panels) + gap * (len(panels) - 1)
    style = spec.get("style", "compact")
    if style not in {"compact", "decorated"}:
        raise ValueError("style must be compact or decorated")
    show_header = bool(spec.get("show_header", style == "decorated"))
    show_footer = bool(spec.get("show_footer", style == "decorated" and spec.get("footer")))
    if show_header and not spec.get("title"):
        raise ValueError("title is required when show_header is true")
    if show_footer and not spec.get("footer"):
        raise ValueError("footer is required when show_footer is true")

    header_h = int(spec.get("header_height", 150)) if show_header else margin
    footer_h = int(spec.get("footer_height", 112)) if show_footer else margin
    canvas = Image.new("RGB", (width, header_h + panel_height + footer_h), "white")
    draw = ImageDraw.Draw(canvas)
    if show_header:
        draw.rectangle((0, 0, 16, header_h), fill=ACCENT)
        draw.text((48, 24), spec["title"], font=load_font(bold_font_path, 40), fill=INK)
        draw.text((48, 86), spec.get("subtitle", ""), font=load_font(font_path, 25), fill=MUTED)

    y = header_h
    for panel in panels:
        canvas.paste(panel, (margin, y))
        if style == "decorated":
            draw.rectangle((margin, y, width - margin, y + panel.height), outline=LINE, width=2)
        y += panel.height + gap
    y -= gap
    if show_footer:
        draw.line((margin, y + 20, width - margin, y + 20), fill=LINE, width=2)
        draw.text((48, y + 38), spec["footer"], font=load_font(font_path, 25), fill=INK)

    output = resolve(base, spec["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, dpi=(220, 220), optimize=True)
    if any("resolved_geometry" in panel for panel in spec["panels"]):
        output.with_suffix(".geometry.json").write_text(json.dumps(
            [p.get("resolved_geometry", {}) for p in spec["panels"]], ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON file containing one card or a cards array")
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT)
    parser.add_argument("--bold-font", type=Path, default=DEFAULT_BOLD_FONT)
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    cards = data.get("cards") if isinstance(data, dict) else None
    if cards is None:
        cards = [data]
    if not isinstance(cards, list) or not cards:
        raise ValueError("Manifest must contain a card object or a non-empty cards array")

    for card in cards:
        output = build_card(manifest.parent, card, args.font, args.bold_font)
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
