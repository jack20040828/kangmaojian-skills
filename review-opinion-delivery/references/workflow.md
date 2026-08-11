# 审查笔记与标记图纸整理为 Word

## Phase 0 接收与建档

Create the workspace and preserve all originals. Store notes/links/exports under `source/notes/`, working-copy DWGs under `source/dwg/`, plotted PDFs under `source/pdf/`, draft/adjusted DOCX files under `source/docx/`, user-supplied screenshots under `source/screenshots/`, and generated evidence images under `screenshots/`.

Record the authoritative source and the output title before editing.

After the source set is stable, run `scripts/snapshot_source_integrity.py <workspace>`. Run it again only after an explicitly accepted source addition or replacement.

## Phase 1 意见清单

Create the v1.2 `delivery_manifest.json`. For every reviewer-authored item, record:

- immutable `item_id` such as `OP-001`, continuous display `item_no`, and exact section;
- source-note reference and marked-location reference;
- drawing number/name wording;
- approved opinion text;
- approved regulation text, including reviewer-approved `无`; distinguish it in the verification record from an unreviewed placeholder;
- approved opinion type;
- evidence strategy and `evidence_images` array, allowing zero, one, or multiple images;
- source PDF, page, crop, and red-box target;
- reviewer-confirmed state and editorial-change note.

Use `pdf_provenance` when the evidence is regenerated from a traceable PDF. Use `preserve_approved_docx` when the latest confirmed Word image is retained in place; record its source DOCX and source item reference. Do not extract/reinsert confirmed images merely to satisfy a generator.

Do not add fields from a technical-review ledger. This manifest is a delivery contract, not a compliance matrix.

## Phase 2 忠实整理

Compare each item with the note and marked location. Preserve the reviewer's conclusion and degree of certainty. Remove assistant-added expansion when it was not in the source, including extra整改路线, unsupported regulation text, broadened drawing scope, or inferred conditions.

Preserve reviewer-approved `无` and never copy an older regulation back. An unreviewed placeholder `无` is not deliverable: regulation research or opinion reclassification belongs to a separately authorized `building-review` phase. Run `normalize_opinion_types.py`: known one-result errors must be corrected and logged; unknown or multi-meaning types must be confirmed before delivery. The normalizer must never exchange mandatory and suggested status. The opinion type follows the final approved conclusion, not the drawing name or isolated keywords.

Default to one core problem per opinion. Consolidate synchronized plan, elevation, and detail requirements into the main opinion unless the reviewer explicitly keeps them separate. Use drawing numbers and names in the body; keep source notes, note IDs, PDF pages, mark numbers, crop coordinates, red-box explanations, and evidence-source descriptions only in provenance/log fields.

## Phase 3 DWG 转 PDF 与证据图

If AutoCAD does not display the marked DWG completely, open a working copy in T20天正建筑. Plot exact sheets/windows to PDF, verify title/drawing number/text/marks, render the PDF, and crop only from the render.

Never insert DWG/CAD/T20 screen captures. Follow `references/screenshot-standard.md`.

## Phase 4 内容验证

For every item, verify:

- note transcription;
- approved order and section;
- drawing number/name;
- numeric values and scope;
- marked-location correspondence;
- PDF provenance of screenshots;
- regulation text copied exactly or `无`;
- opinion type copied exactly;
- editorial changes do not alter substance.

Write actual results to `verification_log.csv`. Run `scripts/validate_delivery_package.py`.

## Phase 5 Word 生成

If a reviewer-approved DOCX exists, copy it to the working output and make only approved local edits while preserving its structure, first-page layout, section numbering, filename convention, and image scale. Generate a new DOCX from the manifest only when no approved base file exists. Use the adjusted-reference layout in `references/delivery-style.md` as the fallback style; it does not require a separate cover page.

Each item contains:

1. bold numbered drawing-reference line;
2. `【审查意见】` paragraph;
3. centered evidence image when required;
4. `【法规条文】` paragraph, including `无` when applicable;
5. `【意见类型】` paragraph.

Do not add explanatory chapters, process notes, or evidence appendices. Formal body, headers, footers, captions, and visible evidence-card text must not expose `笔记`, `得到大脑`, `note_id`, `证据来源`, PDF page traces, mark numbers, crop coordinates, or red-box instructions.

## Phase 6 Word 内容回查

Run `scripts/validate_docx_content.py`. It validates complete opinion blocks, including same-paragraph fields, manual or automatic section numbering, multiple images per opinion, and absence of visible internal-process traces. It must confirm every approved item appears once and no deleted older-draft item returns.

When comparing drafts with `scripts/compare_reviewer_docx.py`, use an explicit reviewer-confirmed mapping whenever deletion, narrowing, or many-to-one consolidation matters. Automatic mapping is only a review aid: unresolved rows must remain `mapping_required` and must not be asserted as deleted or newly added.

## Phase 7 逐页视觉质检

Export DOCX with Microsoft Word, render every PDF page, inspect all pages at full resolution, fill `report_qa.csv`, and run `scripts/validate_report_qa.py`.

Check page count, cover, section headings, uninterrupted item blocks, image readability, clipping, whitespace balance, footer/page numbers, empty-section wording, and final opinion-type note.

## Phase 8 交付

Deliver only the validated final DOCX unless the user also requests PDF/evidence files. Copy it to the project's `04_审图成果` only after all gates pass. Retain the source files, source-integrity snapshot, manifest, logs, plotted PDFs, evidence images, exported PDF, and page renders in the workspace.
