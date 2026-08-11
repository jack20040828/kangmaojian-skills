# 审查清单规则

Do not review broad questions directly. Convert A_审查要点 resources into measurable checks in `check_matrix.csv`.

## Conversion Pattern

For each broad item, create:

- `check_id`
- specialty
- source review item
- applicability: `适用`, `不适用`, or `需判断`
- required drawing fact
- actual drawing fact and `fact_ids`
- drawing references
- standard source to search
- standard article and requirement when found
- pass condition
- fail condition
- not-applicable condition
- screenshot need: yes/no

## Function-Triggered Specialties

When a drawing fact triggers a function-specific specialty, add that specialty to the matrix and review its A_审查要点 item by item. Common triggers:

- 宿舍、旅馆、酒店 -> `012宿舍、旅馆建筑专项`
- 食堂、餐厅、厨房、备餐、洗消、油烟 -> `022饮食建筑专项`
- 学校、中小学、教学、宿舍服务学校 -> `026中小学校专项`
- 停车、车位、无障碍车位、充电桩 -> 总图、无障碍、车库/电动车相关专项 as applicable
- 无障碍出入口、电梯、无障碍宿舍、无障碍卫生间 -> `005建筑无障碍专项`
- 节能报告、绿色建筑、降碳报告、建筑垃圾源头减量 -> corresponding energy, green-building, Hunan policy, and waste-reduction checks

Do not stop at the first issue. Keep checked-but-compliant rows in `check_matrix.csv` so the final opinion list proves it came from a full review rather than an ad-hoc scan. A compliant row must state what was actually checked; the existence of a drawing, note, special chapter, or detail alone is not a compliant technical finding.

For a single-building review, create checks for every row in `drawing_inventory.csv` using `single-building-coverage.md`. A sheet is not complete merely because another sheet in the same report section was checked. Link each `reviewed` inventory row to one or more real `check_id` values that reference that sheet and facts extracted from it; use `not_applicable` only with a sheet-specific reason. Generic checks spanning many sheets must be decomposed or supported by sheet-specific facts.

For high-risk checks, record the measurable or otherwise objective evidence that resolves the item. Typical evidence includes entrance-platform dimensions and accessible-route details, roof/wet-room slopes and drains, drip details, guardrail height and load, stand sightline data, rescue-opening size/location, and the location or number of sanitary fixtures. If the required fact is not shown or the applicability condition is unresolved, conclude `需核验`; do not use a generic “符合”.

Document-stage labels, directory cleanup, title-block differences, and similar packaging matters normally remain checked-but-nonformal. They form a formal issue only when they directly prevent technical verification or the user explicitly requests that scope.

Example:

Broad item: 消防车道是否符合规范要求。

Checkable items:
- fire lane width is shown and meets the applicable standard.
- fire lane turning radius is shown and meets the applicable standard.
- fire lane clear height is shown when relevant.
- fire lane connects to required site entrances/exits.
- fire-fighting field is shown when required.

## Conclusions

Use only:
- `符合`: drawing fact and standard agree.
- `不符合`: drawing fact conflicts with a specific standard/policy requirement.
- `需核验`: drawing is unclear, source is missing, local status is uncertain, or fact conflicts need designer confirmation.
- `不适用`: the check does not apply to the project type or scope.

Do not use `需核验` for facts that are clearly shown.
When applicability is `需判断`, the conclusion must remain `需核验`. Such a row may be retained as a `needs_review` candidate but cannot support a `verified` issue.

## Matrix-to-Issue Rule

- `不符合` rows normally create `issue_candidates.csv` rows.
- High-risk `需核验` rows may create `needs_review` candidate issues.
- `符合` and `不适用` rows do not enter the formal report, but remain in `check_matrix.csv`.
- Every `verified` issue must reference exactly one primary `check_id`; use `notes` for secondary supporting checks.
- Before marking `verified`, decide whether the issue should be merged with another issue, downgraded to `needs_review`, or rejected as non-deliverable. Record that professional filtering decision in `notes` or `validation_log.csv`.
- If the conclusion depends on a door swing, arrow, line type, symbol, cut direction, or absence of graphic expression, close the legend/context evidence chain first. An ambiguous interpretation remains `需核验` and its candidate remains `needs_review`.
