# 审查意见规则

## Candidate Issue Fields

`issue_candidates.csv` columns:

`issue_id,status,display_order,report_section,specialty,check_id,fact_ids,drawing_refs,problem,citation_mode,standard_source,standard_display_name,standard_article,standard_requirement,citation_none_reason,judgment,case_refs,needs_screenshot,screenshot_path,screenshot_location,screenshot_strategy,screenshot_reason,screenshot_count,evidence_point,red_box_target,context_required,screenshot_quality,opinion_type,validation_status,notes`

Status values:
- `verified`
- `needs_review`
- `rejected`
- `delete`

## Final Opinion Requirements

A final opinion must have:
- a matching `check_matrix.csv` row whose `check_id` equals the issue `check_id`
- drawing reference: drawing name and drawing number
- precise project fact
- a specific standard/policy requirement, or a valid design-depth `citation_mode=none` reason
- judgment explaining why the fact fails
- screenshot or screenshot exemption reason
- screenshot strategy and evidence-point records when the current ledger supports them
- opinion type

## Professional Filtering

Formal opinions should be few, precise, and delivery-ready:

- Merge duplicate or overlapping issues before Word generation.
- Do not keep weak evidence in the final report; mark it `needs_review`.
- Do not write suspicious-but-unverified items as violations.
- Do not force screenshots for explanatory design-depth issues when quoting the exact drawing text is clearer.
- Record why each `verified` issue remains formal after filtering, using `notes` or `professional_filter_check`.
- Packaging-only issues such as drawing-stage labels, directory cleanup, or title-block differences normally remain in the matrix rather than the report.
- Write the opinion as `precise drawing fact -> requirement or conflict -> specific revision action`. Avoid unsupported phrases such as `疑为套用`, `不能采信`, or broad `全面复核` instructions.
- Do not verify a graphical direction, symbol, or missing-expression conclusion until `graphical_interpretation_check` records a closed legend and drawing-context chain.

## Citation Modes

- `cited`: required for mandatory clauses, technical thresholds, performance requirements, policy requirements, and any conclusion that claims a drawing violates an external rule. Fill `standard_source`, `standard_display_name`, `standard_article`, and `standard_requirement`. `standard_display_name` is the formal human-readable name and must not contain a path or `.pdf`.
- `none`: allowed only for the three approved design-depth opinion types when the issue is a drawing-internal contradiction, missing index/name/number, duplicate detail, or incomplete expression that does not claim an external technical threshold. Leave all standard fields empty and fill `citation_none_reason`.
- Never use `none` because the applicable standard could not be located. Such an item remains `needs_review`.

## Opinion Format

Use this structure:

```text
涉及图纸：图号-图名。
【审查意见】：...
【法规条文】：《...》第...条：...
【意见类型】：...
```

Only `verified` issues may enter the formal Word report. Keep `needs_review` and `rejected` rows in ledgers for review and training, with a clear reason in `notes`.

For a valid `citation_mode=none` issue, render the regulation line exactly as `【法规条文】：无。`

When screenshots are inserted, place them after `【审查意见】` and before `【法规条文】`. Do not add delivery text such as `截图如下` or `截图说明` unless the user explicitly asks for a supporting evidence appendix.

## 12 Opinion Types

Use exactly one:

- 消防安全强制性条文，必须修改（消防安全）
- 一般性条文，必须修改（消防安全）
- 政策规定，必须修改（消防安全）
- 设计深度，必须修改（消防安全）
- 其它强制性条文，必须修改（其它）
- 其它强制性条文，建议修改（其它）
- 一般性条文，必须修改（其它）
- 一般性条文，建议修改（其它）
- 政策规定，必须修改（其它）
- 政策规定，建议修改（其它）
- 设计深度，必须修改（其它）
- 设计深度，建议修改（其它）

## Case Use

Cases are supporting evidence only. Before using a case, record:
- matching facts
- different facts
- why the case is still relevant

If a case is similar but not fact-matched, do not use it as support.

## v1.2 正式顺序与章节

- `issue_id` 是稳定身份；不得因为正式报告排序变化而重编号。
- 只有 `verified` 行填写正式 `display_order`，从1开始连续且不得重复。
- 单体 `report_section` 只能是：`设计说明`、`平面图`、`立面剖面图`、`大样图`。
- 总图 `report_section` 只能是：`总图设计说明`、`总图设计图纸`。
- `verified`意见必须填写 `judgment`、合法引用模式和专业筛选理由。
- `validation_log.csv` 中 `graphical_interpretation_check` 与 `opinion_wording_check` 必须通过。
- `needs_review`、`rejected`、`delete` 不得进入Word，也不得占用正式显示顺序。
- 同一根因和同一整改动作的重复意见先合并，再确定正式顺序。
- v1.1报告生成器只服从显式章节和顺序；旧工作区才使用历史关键词分类和CSV行顺序。
