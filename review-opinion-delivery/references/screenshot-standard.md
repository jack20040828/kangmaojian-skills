# PDF 证据截图标准

## Mandatory Source Chain

`working-copy marked DWG -> plotted PDF -> rendered PDF page -> crop/red box -> evidence PNG -> Word`

Do not use AutoCAD/T20/model-space/paper-space/DWG-viewer screenshots in the formal Word.

## Plotting

- Use T20天正建筑 when AutoCAD cannot display Tianzheng objects completely.
- Plot the exact sheet/window with correct paper size and orientation.
- Prefer `DWG To PDF.pc3`, monochrome linework, centered output, and readable scale.
- Confirm drawing number/title, text, dimensions, hatches, reviewer marks, and no clipping.

## Cropping and Marking

- retain location context: drawing title/number, axis, room, table header, dimensions, or neighboring construction;
- red-box the smallest decisive target;
- use multi-panel evidence for conflicts or cross-drawing comparison;
- default to a compact white crop with the smallest decisive red box and no visible title/footer; use the blue title treatment only when a title materially helps distinguish panels;
- reconcile the card title, subtitle, footer, dimension labels, and red-box target with the final approved opinion after every reviewer edit; never reuse a stale image whose text still says a superseded value such as 300 mm when the final opinion says 400 mm;
- keep PDF provenance in the manifest and logs. A visible footer is optional and must never expose internal notes, note IDs, PDF page traces, crop coordinates, or red-box instructions;
- enlarge evidence when dimensions or labels are too small at normal Word width.

## Manifest Fields

In v1.2, every opinion uses an `evidence_images` array. Each PDF-provenanced image records:

- `image_path`;
- `source_pdf` ending in `.pdf`;
- 1-based `source_page`;
- `crop_box` with four coordinates per panel;
- `red_box_target`;
- `marked_location_ref`.

An opinion may contain multiple images. Keep their order aligned with the Word evidence sequence. When retaining an image already confirmed in the latest Word, use `strategy: preserve_approved_docx` with `source_docx` and `source_item_ref`; do not invent PDF provenance for it.

Run `scripts/compose_evidence_cards.py` for repeatable composition. Its default `compact` style omits title and footer; use `style: decorated` or explicit `show_header`/`show_footer` only when the visible furniture is genuinely needed. Verify the final image against the recorded PDF before marking provenance/content checks as passed.
