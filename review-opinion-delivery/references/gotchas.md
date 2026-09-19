# 已验证的失败陷阱

Apply these constraints when the matching situation appears. Do not load this file for unrelated phases.

## Routing and Authority

- A request to find new drawing issues or judge compliance belongs to `building-review`, not this skill.
- A mixed request must be split. Finish or scope the delivery task separately from any newly authorized technical review.
- Duplicate source numbering does not prove duplicate content. Preserve separate source references and change the approved item count only with reviewer confirmation.
- When note, marked drawing, screenshot, and DOCX disagree, keep the highest-authority source and record the conflict. Do not silently choose the most plausible technical answer.
- Do not add regulation text,整改路径, applicability conditions, dimensions, drawing ranges, or opinion types merely to make prose look complete.
- The latest confirmed DOCX may intentionally delete, merge, or weaken older-draft content. Never restore those decisions from history.
- Reviewer-approved `无` is a deliberate regulation value, not a blank to be filled from standards or an older draft. An unreviewed placeholder `无` is different and must block delivery until a separately authorized technical review resolves it.
- One problem described across plan/elevation/detail drawings is not automatically three opinions. Avoid evidence-driven duplicate splitting.
- One-to-one text similarity can misclassify narrowed or absorbed opinions as deletion plus addition. Use reviewer-confirmed mapping for consequential comparisons; automatic unresolved relations stay `mapping_required`.

## Evidence

- Never use AutoCAD, T20, model-space, paper-space, or DWG-viewer interface screenshots in the formal Word.
- A red box alone is not enough. Retain the minimum drawing title, number, axis, room, dimension, or neighboring context needed to locate the change.
- Rebuild or recheck an evidence card after any wording, number, scope, or drawing-reference change. A stale card is a delivery failure.
- Reusing one evidence image across items is allowed only when the manifest records the same PDF provenance and the image genuinely proves every linked item.
- Do not expose provenance machinery in the formal deliverable. Notes, note IDs, 得到大脑, evidence-source labels, mark numbers, crop coordinates, and red-box instructions remain internal. Only explicit user authorization enables the strict v1.3 PDF page/title locator; it does not permit other process traces.
- Do not wrap every crop in a blue title/footer card. Default to one focused compact image; compose related panels only when one opinion genuinely needs cross-drawing proof.

## Manifest and Word

- Keep `item_id` stable even when display order changes. Never use a renumbering operation to redefine item identity.
- Do not generate a fresh report over a reviewer-approved DOCX. Use the latest approved file as the base and make local edits.
- Do not treat successful DOCX generation as proof of content fidelity. Run manifest-to-DOCX validation.
- Preserve `无` regulations. Deterministically correct known opinion-type aliases and log the correction; fail on unknown/multi-meaning values.
- Opinion type follows the final approved conclusion. Do not infer it from the drawing family, the word “消防”, or an older draft's classification.
- Never let typo correction exchange `必须修改` and `建议修改`, alter technical certainty, or broaden responsibility.
- A validator warning is insufficient for an invalid type or untreated known typo. The package must fail until corrected or confirmed.

## QA

- Never prefill `report_qa.csv` with `通过`. Keep every page `待检查` until that rendered page has actually been viewed.
- Do not reuse page QA after the DOCX or exported PDF changes. Render again and create a fresh ledger.
- Check image labels, subtitles, footers, dimensions, and red boxes against the final opinion, not only the surrounding Word text.
- Avoid image-only pages and large blank areas by merging the same root issue, removing redundant visible card furniture, and sizing evidence deliberately. Do not enforce compactness with a fixed page cap.
