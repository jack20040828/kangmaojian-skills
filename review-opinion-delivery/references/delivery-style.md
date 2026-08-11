# Word 交付样式

This style contract is distilled from reviewer-approved, anonymized Word references. The public package intentionally omits project paths, source hashes, client names, and identifying document metadata.



The verified reference set uses a single-section internal-review layout with centered page numbers and evidence images placed next to their approved opinions.

## Page System

- paper: US Letter portrait, 612 x 792 pt;
- margins: top/bottom 72 pt, left/right 90 pt;
- header distance: 36 pt;
- footer distance: 32.4 pt;
- body font: 宋体 10.5 pt;
- body line spacing: 1.18;
- paragraph alignment: left unless specified.

## First Page

- project name: centered, 宋体 16 pt bold, 6 pt before, 8 pt after;
- report title: centered, 宋体 18 pt bold, 8 pt after;
- date: centered, 宋体 11 pt, 14 pt after;
- use the reviewer-supplied title; the adjusted reference uses `建筑施工图内审意见`;
- when a latest approved DOCX exists, preserve its first-page layout and do not insert a new cover;
- when generating without a base DOCX, place project, title, and date compactly at the top of page 1 and continue with the first section; do not force a separate cover page;
- place a centered page number in the footer.

## Sections and Items

- section heading: 宋体 13 pt bold, 5 pt before, 6 pt after, keep with next;
- drawing-reference line: 宋体 10.5 pt bold, 4 pt before, 3 pt after, keep with next;
- opinion paragraph: 宋体 10.5 pt, 5 pt after, keep with next;
- evidence image paragraph: centered, 1 pt before, 5 pt after, keep with next;
- regulation paragraph: 宋体 10.5 pt, 3 pt after, keep with next;
- opinion-type paragraph: 宋体 10.5 pt, 7 pt after;
- final taxonomy note: 宋体 9.5 pt, 6 pt before, 0 pt after.

Required single-building sections:

- `一、设计说明：`
- `二、平面图：`
- `三、立面、剖面图：`
- `四、大样图：`

For an empty section, use a compact single heading such as `四、大样图：无意见`; do not add a second explanatory paragraph unless the reviewer requests it.

## Evidence Images

- maximum width: 6.05 in;
- maximum height: 5.25 in;
- default asset is a focused compact crop with no visible provenance footer or decorative title block; keep PDF provenance in the manifest and logs;
- use a multi-panel composite when one approved opinion depends on two or more drawings; do not create separate evidence-card pages merely because several sources exist;
- choose the larger readable size that stays within both limits;
- preserve aspect ratio;
- landscape/detail evidence may use nearly the full text width when small dimensions or annotations would otherwise be unreadable;
- keep the image with the opinion above and regulation below when possible.

## Pagination

- never orphan a section heading;
- keep the drawing line, opinion, image, regulation, and type as one visual block as far as Word pagination allows;
- prioritize evidence readability over squeezing two dense issues onto one page;
- avoid blank pages, clipping, overlap, or a regulation/opinion type detached from its issue;
- avoid image-only pages and large blank areas. Merge evidence for the same root issue, remove redundant card furniture, and tune image size/paragraph spacing while preserving readability; do not target a fixed page count.
- place centered Arabic page numbers in every footer;
- visually separate the final taxonomy note from the last section. Do not depend on a fixed number of blank paragraphs; use controlled spacing and page review.

## Adjustments Learned from the Reference

- The deliverable title changed from `建筑施工图审查意见` to `建筑施工图内审意见`.
- Several assistant-expanded opinions were shortened back to the reviewer's direct wording.
- Unsupported regulation paragraphs were replaced with `无` instead of being inferred.
- Drawing scopes and measurements were corrected to the reviewer-confirmed values without expanding the affected drawings or technical meaning.
- The reviewer preserved concise actionable statements. v1.2 additionally requires every opinion type to resolve to the canonical 12-type taxonomy, with deterministic typo correction logged.
- The stair-opening evidence image was enlarged for dimension readability.
- Evidence cards were corrected to the reviewer-approved facts; final QA must catch stale screenshot text or red boxes left from an earlier draft.
- The empty detail section became `四、大样图：无意见`.

These are editorial-authority rules, not new technical-review rules.

## Second Confirmed Retrospective

In a later anonymized comparison, the reviewer-final version contained fewer opinions, evidence images, and rendered pages because of confirmed deletions, narrowed scopes, and many-to-one consolidations—not because text or evidence was reduced below readability. This confirms that the latest approved Word controls item identity, scope, regulation state, type, evidence density, and layout.
