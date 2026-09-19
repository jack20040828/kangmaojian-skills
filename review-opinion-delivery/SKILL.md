---
name: review-opinion-delivery
description: Convert reviewer-authored architectural construction-drawing notes, marked DWG/PDF locations, screenshots, and approved or draft DOCX files into a faithful, evidence-linked, page-verified Chinese Word deliverable. Use only when the reviewer has already formed the opinions, such as 整理审查意见、把审查笔记和标记图纸合成Word、补齐PDF证据截图、核对并排版可交付内审意见. Do not use to inspect drawings for new issues, judge code compliance, invent or change technical conclusions, or perform unrelated generic Word editing. If a request mixes new technical review with delivery work, separate the workflows and require explicit authorization before invoking building-review.
---

# 施工图审查意见整理交付

Package opinions already made by the reviewer into a faithful, evidence-linked Word deliverable. Keep this workflow separate from technical drawing review.

## Non-Negotiable Boundary

- Treat the reviewer's latest confirmed DOCX as the highest content and style authority. Preserve its approved wording, item scope, certainty, regulation text, item consolidation, and mandatory/suggested status.
- Do not add, remove, strengthen, weaken, merge, split, or infer a technical conclusion without explicit reviewer approval.
- Use drawings only to locate marks and verify transcription. Do not derive new issues from them.
- Preserve `无` only when it is reviewer-approved or explicitly confirmed as an internal contradiction, missing name/index, or design-expression issue that does not assert an external threshold. An unreviewed placeholder `无` blocks delivery; regulation research, completion, and conclusion reclassification require a separately authorized `building-review` phase.
- Correct obvious typos, punctuation errors, and deterministic opinion-type aliases; record the before/after/reason in `edit_log.csv`.
- If a correction has two plausible results or could change `必须修改`/`建议修改`, technical meaning, applicability, or responsibility, mark it `需确认` and stop delivery.
- Every opinion type must resolve to one of the 12 canonical values in `references/opinion-types.json`; invalid or unresolved values are a hard failure.
- Record material source conflicts as `需确认`; do not silently correct professional substance.

Read `references/scope-boundary.md` before editing any opinion.

## Required Workflow

1. Create a workspace with `scripts/create_delivery_workspace.py`. For an existing project, pass `--root <project>\03_审图过程`.
2. Preserve every original under `source/`. Never overwrite a source file.
3. After the source set is stable, run `scripts/snapshot_source_integrity.py <workspace>`.
4. Build the v1.3 `delivery_manifest.json` following `references/delivery-contract-v13.md`: stable IDs, source dispositions, approved content, claim/image correspondence, evidence history and location policy. Legacy v1.0–v1.2 remain readable without automatic migration. Distinguish reviewer-approved regulation `无` from an unreviewed placeholder. Fill actual checks in `verification_log.csv` and corrections in `edit_log.csv`.
5. For marked DWG evidence, plot a working copy to PDF and crop only from rendered PDF pages. Never place CAD/T20 interface screenshots in the formal Word.
6. Run `scripts/normalize_opinion_types.py <workspace>` and then `scripts/validate_delivery_package.py <workspace>` before editing or generating the final Word. Deterministic corrections are mandatory; unresolved types must block delivery.
7. If a reviewer-approved DOCX exists, use the newest one as the base and make only approved local edits. Use `scripts/generate_delivery_report.py` only when no base DOCX exists.
8. Run `scripts/validate_docx_content.py`; prohibit all process traces except the strictly authorized PDF page/title locator. Update continuation and cross-references using stable IDs after deletion/merging/reordering. Export with Word, render all pages with the current manifest/DOCX/PDF hash snapshot, inspect each page and run `scripts/validate_report_qa.py`. Any subsequent change invalidates QA.
9. Deliver only after both content and visual gates pass. Copy the final DOCX to `<project>\04_审图成果`; do not make scripts guess the project root.

## Progressive Reference Routing

- Runtime dependencies and public configuration: `references/runtime-requirements.md`
- Always before editing: `references/scope-boundary.md`
- Always for new v1.3 workspaces: `references/delivery-contract-v13.md`
- Full phase flow and manifest fields: `references/workflow.md`
- Known failure traps when sources conflict or validation fails: `references/gotchas.md`
- Only when producing evidence images: `references/screenshot-standard.md`
- Only before Word editing or generation: `references/delivery-style.md`
- Opinion-type generation, correction, and validation: `references/opinion-types.json`
- Only during final validation: `references/qa-checklist.md`

## Practical Defaults

- Set `REVIEW_OPINION_PROJECT_ROOT` or pass `--root <path>` for workspace creation; otherwise the script uses `./review-opinion-projects` under the current working directory.
- Working DOCX output: `<delivery-workspace>\output`
- Final report title: use the reviewer-supplied title; otherwise use `建筑施工图内审意见`
- Empty required section: one concise heading such as `四、大样图：无意见`
- Content authority: latest approved DOCX or explicit correction, then approved notes/order, then marked location or user screenshot, then earlier drafts for formatting/history only
- One core issue normally forms one opinion. Include synchronized plan/elevation/detail requirements only after reviewer confirmation; do not expand technical scope yourself.
- Use drawing number/title by default. Explicit user authorization may select strict `PDF第N页《图名》` with empty drawing number; all other process information stays in logs.
- Default evidence presentation is one focused compact crop without a visible title or provenance footer. Use a composed multi-panel image only when cross-drawing comparison is necessary; visible card furniture is optional, not a delivery default.
- Never restore an item, regulation, or wording deleted from the latest approved DOCX merely because it exists in an older draft.
