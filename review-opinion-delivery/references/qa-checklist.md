# 交付质量门禁

## Content Gate

All must pass:

- v1.2 item IDs are unique, stable, and linked to the matching verification rows;
- every file under `source/` matches the manifest source-integrity snapshot, with no missing, modified, or untracked source;
- item count and numbering match the reviewer-approved source;
- section and order match the approved structure;
- drawing numbers/names and scope match the latest source;
- opinion text preserves the reviewer’s conclusion and certainty;
- dimensions and quantities match the note/marked evidence;
- regulation text is exact; any `无` is reviewer-approved rather than an unreviewed placeholder;
- opinion type is one of the canonical 12 values; known aliases have been corrected and logged;
- no unknown/multi-meaning type or untreated known typo remains;
- deterministic correction never exchanges `必须修改` and `建议修改`;
- `edit_log.csv` records every automatic before/after/reason;
- no assistant-added technical conclusion or整改路线 remains;
- every image matches the item and uses either complete PDF provenance or a recorded latest-approved-DOCX preservation strategy;
- older-draft deleted items and regulations do not reappear;
- every screenshot title/subtitle/footer, red box, dimension, and drawing label agrees with the final approved wording; no stale pre-edit evidence card remains;
- all non-trivial editorial edits are recorded;
- unresolved substance questions are marked `需确认`, not silently rewritten.
- no formal body/header/footer/caption exposes notes, note IDs, 得到大脑, evidence-source labels, PDF page traces, mark numbers, crop coordinates, or red-box instructions;

## DOCX Structure Gate

- first page follows the latest approved base; a newly generated file is not required to have an independent cover page;
- required sections exist;
- every manifest item appears exactly once and in order;
- each complete issue block contains drawing reference, opinion, zero or more evidence images as approved, regulation, and type; same-paragraph fields and automatic section numbering are accepted;
- empty sections use the approved concise wording;
- final opinion-type note is present when configured;
- page-number field exists in the footer.

## Visual Gate

Inspect every rendered page:

- no clipping, overlap, broken glyphs, or blank page;
- section heading is not orphaned;
- issue block is understandable without page hunting;
- evidence image is sharp, readable, correctly cropped, and large enough;
- compact evidence avoids redundant visible title/footer furniture; multi-panel composition is used only when the opinion needs cross-drawing proof;
- red box identifies the right location;
- CAD/T20 interface is absent;
- paragraph spacing and whitespace feel balanced;
- no avoidable image-only page or large blank gap remains; compactness is achieved without a fixed page cap or unreadably small evidence;
- regulation and opinion type remain attached to the issue;
- page numbers are centered and continuous;
- the final note is readable and separated from the last issue.

Record one row per page in `report_qa.csv`. Do not pre-mark uninspected pages as passed.
Any DOCX or PDF revision invalidates the previous page QA. Render again and initialize a fresh ledger.
