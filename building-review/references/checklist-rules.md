# 审查清单规则

Do not review broad questions directly. Convert A_审查要点 resources into measurable checks in `check_matrix.csv`.

## Conversion Pattern

For each broad item, create:

- `check_id`
- specialty
- `review_item_id`: exact A_审查要点 item or controlled design-depth item
- `coverage_topic`: one primary topic ID from `single-building-coverage.md`
- `evidence_class`: the kind of fact that can actually resolve that topic
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

For v1.6 also record `rule_id`, `atomic_check_id`, `decision_state`, `discovery_track`, `applicability_basis`, `comparison_method`, `comparison_record`, `calculation_record`, `open_reason`, `graphic_claim_type`, `graphic_chain_ids`, `graphic_gate_reason`, `applicability_decision_ids`, and `completion_gate`. Read `review-rule-schema.md` before editing generated rows. Legacy v1.4/v1.5 fields remain compatibility-only.

## Function-Triggered Specialties

When a drawing fact triggers a function-specific specialty, add that specialty to the matrix and review its A_审查要点 item by item. Common triggers:

- 宿舍、旅馆、酒店 -> `012宿舍、旅馆建筑专项`
- 食堂、餐厅、厨房、备餐、洗消、油烟 -> `022饮食建筑专项`
- 学校、中小学、教学、宿舍服务学校 -> `026中小学校专项`
- 停车、车位、无障碍车位、充电桩 -> 总图、无障碍、车库/电动车相关专项 as applicable
- 无障碍出入口、电梯、无障碍宿舍、无障碍卫生间 -> `005建筑无障碍专项`
- 节能报告、绿色建筑、降碳报告、建筑垃圾源头减量 -> corresponding energy, green-building, Hunan policy, and waste-reduction checks

Do not stop at the first issue. Keep checked-but-compliant rows in `check_matrix.csv` so the final opinion list proves it came from a full review rather than an ad-hoc scan. A compliant row must state what was actually checked; the existence of a drawing, note, special chapter, or detail alone is not a compliant technical finding.

For v1.6, AI-complete `project_profile.json`, classify all sheets, then run `generate_project_checklist.py`. It expands mandatory family topics and profile-triggered technical rules as `unreviewed/需核验`, creates structured applicability rows, and creates required graphic-evidence role placeholders. Do not start `issue_candidates.csv` until every triggered atomic rule exists. One row has one primary topic and one sheet-specific atomic ID; one arbitrary number cannot close a different topic.

For residential single-building reviews, `residential_core_v1` is a package gate, not a suggestion list. The package covers residential storey/clear height, accessible dwellings, solar systems, rescue openings, roof/interior/exterior-wall waterproof layers, wet-area level differences, floor slip resistance, balcony/public guards, and stair horizontal handrails. A missing drawing family or a missing detail does not remove the rule; create evidence-linked checks or leave the package unresolved.

For a single-building review, create checks for every row in `drawing_inventory.csv` using `single-building-coverage.md`. A sheet is not complete merely because another sheet in the same report section was checked. Link each `reviewed` inventory row to one or more real `check_id` values that reference that sheet and facts extracted from it; use `not_applicable` only with a sheet-specific reason. Generic checks spanning many sheets must be decomposed or supported by sheet-specific facts.

For high-risk checks, record the measurable or otherwise objective evidence that resolves the item. Typical evidence includes entrance-platform dimensions and accessible-route details, roof/wet-room slopes and drains, drip details, guardrail height and load, stand sightline data, rescue-opening size/location, and the location or number of sanitary fixtures. If the required fact is not shown or the applicability condition is unresolved, conclude `需核验`; do not use a generic “符合”.

Before concluding a new review, run three distinct discovery passes:

1. Mandatory and general technical requirements.
2. Design-depth and cross-drawing contradictions, including wrong project name/function, nonexistent basement, elevator mismatch, stale code basis, schedule applicability, and inconsistent notes.
3. Supported optimization advice, such as unnecessary fire-door or load grades, kept separate from mandatory corrections.

For missing-expression conclusions, use `evidence_class=absence_chain` only after checking the governing note, relevant plan/section/detail, legend or schedule, and every likely alternate location. Record that checked range in `notes`. If the chain is incomplete, use `需核验`.

For v1.6 graphic claims, classify the claim as `dimension`, `direction`, `symbol`, `absence`, `cross_sheet`, `detail`, `location`, or justified `none`. Complete every rule-required role in `graphic_evidence_chain.csv`. Each role must identify source, page, drawing, location, graphic element, observed fact, interpretation, screenshot, source quality, and `completed_at`; no reviewer name is used. Direction, symbol, absence, and cross-sheet claims must also state a plausible alternative interpretation and the drawing evidence that eliminates it. Low-quality raster evidence alone cannot close the check.

For each v1.6 rule condition, resolve its generated row in `applicability_decisions.csv`. `适用` requires all conditions `met`. `不适用` requires a fact-backed `not_met` condition whose rule outcome is `not_applicable`; missing measures and unknown facts do not qualify.

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

For an `absence_is_noncompliant` rule, absence of the required measure is evidence for `不符合` when the clause applies, not evidence for `不适用`. `不适用` must cite a positive scope fact such as an existing-building alteration, fewer than three above-ground storeys, a non-flat roof, or a non-masonry exterior wall.

Do not use `需核验` for facts that are clearly shown.
When applicability is `需判断`, the conclusion must remain `需核验`. Such a row may be retained as a `needs_review` candidate but cannot support an `ai_ready` issue.

For v1.6, `符合` and `不符合` additionally require a rule ID, resolved structured applicability decisions, actual facts, comparison record, any required calculation record, any required graphic evidence, `decision_state=resolved`, and `completion_gate=AI初审完成`. No independent human review gate is created. Missing any one of them requires `needs_review/需核验`.

## Matrix-to-Issue Rule

- `不符合` rows normally create `issue_candidates.csv` rows.
- High-risk `需核验` rows may create `needs_review` candidate issues.
- `符合` and `不适用` rows do not enter the formal report, but remain in `check_matrix.csv`.
- Every `ai_ready` issue must reference exactly one primary `check_id`; use `notes` for secondary supporting checks.
- A v1.6 formal issue may come only from a resolved `不符合` atomic check whose `issue_id` matches the candidate and whose applicability and graphic gates have closed.
- Before marking `ai_ready`, decide whether the issue should be merged with another issue, downgraded to `needs_review`, or rejected as non-deliverable. Record that AI professional filtering decision in `notes` or `validation_log.csv`.
- If the conclusion depends on a door swing, arrow, line type, symbol, cut direction, or absence of graphic expression, close the legend/context evidence chain first. An ambiguous interpretation remains `需核验` and its candidate remains `needs_review`.
