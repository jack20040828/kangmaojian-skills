# 事实台账

The fact ledger prevents review by impression. Every later issue should point back to at least one row here.

## `drawing_inventory.csv`

Columns:

`source_file,page,sheet_no,drawing_no,drawing_name,discipline,content_type,scale,title_block_status,review_family,review_status,review_check_ids,review_notes,notes`

Use one row per identifiable drawing sheet or page.

v1.2 rules:
- `review_family`: `设计说明`, `目录索引`, `平面图`, `屋面图`, `立面图`, `剖面图`, `楼梯大样`, `墙身大样`, `其他大样`, `门窗表`, `材料做法表`, `总图设计说明`, `总平面图`, `竖向设计图`, `交通消防图`, `其他总图`, or `其他`.
- `review_status`: `reviewed`, `not_applicable`, or `needs_review`.
- `reviewed` requires one or more existing `review_check_ids`.
- `not_applicable` requires a sheet-specific `review_notes` reason.
- `needs_review`, a blank status, or an invalid family blocks Word generation.

## `fact_ledger.csv`

Columns:

`fact_id,source_file,page,drawing_no,drawing_name,location,fact_type,raw_text_or_measure,value,unit,confidence,needs_verification,notes`

Rules:
- Use stable ids such as `F001`, `F002`.
- Preserve original wording in `raw_text_or_measure`.
- Use `needs_verification=yes` only when the drawing is unclear, the value conflicts, or the source is missing.
- If a value appears in multiple places, create separate rows and note consistency or conflict.

## `check_matrix.csv`

Columns:

`check_id,specialty,source_review_item,applicability,required_fact,actual_fact,fact_ids,drawing_refs,standard_source,standard_article,standard_requirement,conclusion,forms_issue,issue_id,not_forming_reason,notes`

Rules:
- Use stable ids such as `CHK-001`.
- Create rows from A_审查要点 for every active specialty before writing candidate issues.
- Use only `适用`, `不适用`, or `需判断` in `applicability`.
- Use only `符合`, `不符合`, `需核验`, or `不适用` in `conclusion`.
- Set `forms_issue=yes` only when the row forms or supports an issue in `issue_candidates.csv`.
- If `forms_issue=no`, fill `not_forming_reason` with a short reason such as `符合`, `不适用`, `证据不足需复核`, or `建筑专业范围外`.
- Link `verified` issues back to this ledger by `check_id`.

## Minimum Facts Before Review

For 总图:
- design basis and approval references
- coordinate/elevation system
- red line and building control line facts
- building list and indicators
- fire lane, fire access, turning radius, fire separation, fire-fighting field
- parking, accessible parking, EV charging, waste collection, public facilities
- north arrow or wind rose and drawing orientation

For 单体:
- project type, building height, fire classification, durability, structure type
- floors, areas, occupancy, number of units/rooms/beds/classes as applicable
- fire compartments, evacuation doors/stairs/exits, refuge or fire-fighting features
- accessibility route, toilets, elevators, parking, doors
- waterproofing, energy, green-building, equipment-room, curtain wall, safety glass, guardrails
- drawing consistency across notes, plans, elevations, sections, details, door/window schedules

## v1.2 关联完整性

- `fact_id`、`check_id`、`issue_id` 是稳定标识，建立引用后不得因排序而改号。
- 每类ID必须非空且唯一；正式显示次序使用 `display_order`，不要复用ID承担排序。
- `fact_ledger.csv` 的 `source_file` 必须能在 `drawing_inventory.csv` 中找到；页码或图号存在时也必须对应。
- `issue_candidates.csv` 的 `fact_ids` 和 `check_id` 必须引用现有记录。
- 正式意见的 `drawing_refs` 必须包含其关联事实中的图号和图名；PDF页码只能补充定位。
- `source/` 中每个非临时文件必须进入 `review_manifest.json.source_integrity`。
- 源文件或已引用规范发生变化后，旧快照失效；重新核对事实和适用性后再生成快照。
- 零正式意见不是空白工作区：仍须有完整图纸清单、事实台账、审查矩阵、结论和不形成意见理由。
