# 功能边界与内容权限

This skill is an editorial-delivery workflow, not a drawing-review workflow.

## Routing Split

- Use this skill only when reviewer-authored opinions already exist and the task is faithful organization, evidence linking, Word editing, or delivery QA.
- Route requests to find new issues, interpret regulations, or judge drawing compliance to `building-review`.
- Route unrelated Word formatting or writing to the general document workflow.
- Split mixed requests into a delivery scope and a separately authorized technical-review scope. Do not expand authority inside the delivery workspace.

## Content Authority

Use this priority:

1. the reviewer's latest adjusted DOCX or explicit correction;
2. the reviewer's note text and approved item order;
3. the marked drawing location and user screenshot;
4. an earlier generated draft, only as formatting/history reference.

If sources conflict, preserve the higher-priority source and record the conflict in `verification_log.csv`.

## Allowed Without Re-Approval

- normalize punctuation, spaces, drawing-number brackets, and obvious transcription errors when the correction has one unambiguous result;
- replace a known opinion-type alias with its canonical value from `opinion-types.json`, including `设计深度文，必须修改（其它）` → `设计深度，必须修改（其它）`;
- place the approved item in the correct section;
- preserve substantive wording; v1.3 shortening beyond deterministic punctuation requires an updated author-confirmed content snapshot;
- make screenshots cleaner and more readable without changing the marked evidence;
- adjust Word typography, image size, spacing, page breaks, and page numbers;
- preserve `无` where the reviewer has approved it or explicitly confirmed that the opinion is an internal drawing contradiction, missing name/index, or design-expression issue without an external technical threshold.

Record every deterministic correction in `edit_log.csv`, including original text, corrected text, and reason. Merely recording an obvious error without correcting it is not allowed.

## Requires Reviewer Approval

- adding or removing an issue;
- changing a dimension, drawing scope, factual premise, mandatory/suggested status, opinion type, regulation, or整改要求;
- turning a conditional opinion into a confirmed violation;
- adding code-derived language, a new professional judgment, or a new cross-discipline requirement;
- merging or splitting issues in a way that changes emphasis or accountability.
- selecting between two or more plausible typo/type corrections.
- deciding whether an unreviewed regulation placeholder should be replaced with a code citation, or changing the opinion type because of that technical judgment.

## Correct or Query

Correct a deterministic typo, punctuation error, or known opinion-type alias immediately and record it. Do not use correction logic to change `必须修改` into `建议修改` or the reverse.

When the note, screenshot, marked drawing, or draft disagrees:

1. record the exact discrepancy;
2. keep the reviewer's latest approved wording;
3. set the relevant verification check to `需确认`;
4. ask the reviewer only if the unresolved difference affects the deliverable.

Do not call `building-review` or search standards merely to make the prose look more complete. If the reviewer explicitly asks to find a missing provision or reclassify an opinion, stop the delivery phase, perform that separately authorized technical review, obtain an approved result, and only then resume faithful delivery.
