# 截图协议

Screenshots are evidence, not decoration.

v1.6 distinguishes two uses. `graphic_evidence_chain.csv` proves the professional interpretation used to close an atomic check; `issue_candidates.csv` controls what is inserted into the Word report. The same crop may serve both only when it satisfies both records. A Word screenshot exemption never exempts a rule-required graphic evidence chain.

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

## Context Range Standard

For a screenshot with one or more red boxes, use the smallest rectangle enclosing all red boxes as the red-box envelope.

- When feasible, the screenshot crop's width and height should each be 2–3 times the red-box envelope's width and height. The crop must also show useful locating references such as an axis, table header, room name, dimension line, drawing title/number, or note heading.
- If both crop-to-envelope ratios are already within or above this range and the location is understandable, keep the crop unchanged. Do not zoom out merely to make the image larger.
- If either ratio is below 2, or the crop is too local to find on the drawing, expand the entire crop only on the deficient axis or axes to about 2.5 times the envelope. Preserve the red box's source-drawing coordinates and size; never enlarge or move the red box to simulate more context.
- If a page boundary prevents a 2-times ratio, expand to the available boundary and include the strongest available locating reference. Record the limitation in the evidence ledger.
- For evidence images without a red box, the numeric ratio does not apply; choose the crop from the semantic location and surrounding references.
- Confirm readability after the image is placed in Word. Crop range and Word display size are separate decisions.


## Positioning Steps

1. Start from the written candidate issue.
2. Identify drawing file, page, drawing number, and semantic location.
3. Crop the relevant area with surrounding references such as axis, table header, room name, dimension line, drawing title, drawing number, or note heading.
4. Verify the crop contains the exact problem.
5. Draw a red box only around the smallest evidence point: wrong text, table row, room, door/window number, axis bay, dimension, node, missing waterproofing/drainage location, or conflict location.
6. Do not red-box a whole page, whole table, or whole plan unless the whole element is the evidence point.
7. Save the number of screenshots required by the strategy.
8. Record screenshot path, location, evidence point, red-box target, and context requirement in `issue_candidates.csv`.

## Professional Graphic Chain

For every required evidence role, record one `graphic_evidence_chain.csv` row with the exact drawing role, source, page, drawing number/name, semantic location, graphic element, observed fact, interpretation, fact IDs, screenshot, source quality, and `completed_at`. v1.6 does not record a reviewer name.

- Use `vector` when linework/text can be inspected at source quality, `raster_high` when the render remains clearly readable, and `raster_limited` when aliasing, blur, overlap, or resolution limits interpretation.
- A required chain cannot be closed from `raster_limited` rows alone.
- Direction, symbol, absence, and cross-sheet claims must record at least one plausible `alternative_interpretation` and the objective `elimination_basis` from the legend, plan, elevation, section, detail, schedule, dimension, or index.
- For absence claims, include every rule-required likely location; one local crop cannot prove whole-set absence.
- If any required role is missing or the alternative cannot be eliminated, set the chain/check to `needs_review`.

## Self-Check

All must be yes:
- Does the text describe a specific problem?
- Is the screenshot from the same drawing and location?
- Does the red box mark the exact problem point?
- Can a reviewer understand the location from surrounding context?
- Is the screenshot clean and readable?
- Does the screenshot strategy match the issue: no forced image for purely textual issues, multiple images for cross-sheet or cross-report proof?
- Would the owner or designer know where to revise by looking at the red box?
