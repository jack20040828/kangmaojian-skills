# 截图协议

Screenshots are evidence, not decoration.

## When Required

Required when:
- the issue depends on a drawing location, dimension, table row, symbol, door/window number, room, axis, or note.
- the user expects a Word report with visual evidence.

May be omitted when:
- the issue is purely text-based and the exact text is quoted in the opinion.
- the source drawing cannot be rendered, in which case record the reason and ask for usable source if needed.

## Screenshot Strategy

Record one strategy for every candidate issue:

- `none`: no screenshot in the Word report. Use only with a clear exemption reason.
- `single`: default when one local crop proves one issue.
- `multiple`: two or more screenshots are indispensable, such as a plan/detail conflict or two reports with conflicting facts. Always record why one screenshot is insufficient.
- `shared`: one screenshot intentionally supports several related issues.

Prefer one precise evidence image for a single-location issue. Do not add extra screenshots for decoration or general context; use `multiple` only when the issue cannot be proved by one crop.

## Positioning Steps

1. Start from the written candidate issue.
2. Identify drawing file, page, drawing number, and semantic location.
3. Crop the relevant area with surrounding references such as axis, table header, room name, dimension line, drawing title, drawing number, or note heading.
4. Verify the crop contains the exact problem.
5. Draw a red box only around the smallest evidence point: wrong text, table row, room, door/window number, axis bay, dimension, node, missing waterproofing/drainage location, or conflict location.
6. Do not red-box a whole page, whole table, or whole plan unless the whole element is the evidence point.
7. Save the number of screenshots required by the strategy.
8. Record screenshot path, location, evidence point, red-box target, and context requirement in `issue_candidates.csv`.

## Self-Check

All must be yes:
- Does the text describe a specific problem?
- Is the screenshot from the same drawing and location?
- Does the red box mark the exact problem point?
- Can a reviewer understand the location from surrounding context?
- Is the screenshot clean and readable?
- Does the screenshot strategy match the issue: no forced image for purely textual issues, multiple images for cross-sheet or cross-report proof?
- Would the owner or designer know where to revise by looking at the red box?
