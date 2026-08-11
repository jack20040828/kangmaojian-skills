# Word 报告格式

v1.2 使用 `issue_candidates.csv` 中的 `report_section` 和 `display_order` 决定章节与顺序。v1.1工作区保持原章节样式；更早工作区继续使用历史关键词分类和CSV行顺序。

Use the existing templates:

- 总图: bundled `范本_建筑总图施工图审查意见.docx` in the skill directory
- 单体: bundled `范本_建筑单体施工图审查意见.docx` in the skill directory

## Cover

Use only:
- project name
- report title
- date

Do not add reviewer, directory, separate review basis, project overview, statistics table, review scope, validation notes, evidence ledger summaries, or conclusion sections unless the user explicitly asks for a separate supporting document.

## Sections

For 总图, use template-style sections such as:
- `总图（建筑）施工图设计说明：`
- `总图设计图纸：`

For 单体, use only these template-style sections:
- `设计说明：`
- `二、平面图：`
- `三、立面、剖面图：`
- `四、大样图：`

单体允许的 `report_section`：`设计说明`、`平面图`、`立面剖面图`、`大样图`。总图允许：`总图设计说明`、`总图设计图纸`。

`display_order` 只控制正式显示顺序；`issue_id` 保持稳定，不随排序变化。

v1.2单体默认：
- 报告标题：`建筑单体施工图内审意见`
- 文件名：`【建单内审】{项目名称}{YYYY-MM-DD}.docx`
- 文内日期：`YYYY年M月D日`

显式 `--report-title` 或 `--output` 可以覆盖默认值。总图默认标题、章节和文件名不变。

## Opinion Items

Number opinions continuously through the report. Each item should include:
- involved drawing
- review opinion
- screenshot only when the issue strategy requires visual evidence
- standard article
- opinion type

Do not include `needs_review`, `rejected`, or `delete` issues.
Do not add delivery text such as `截图如下` or `截图说明`; screenshots should sit silently between `【审查意见】` and `【法规条文】`.

`涉及图纸` 优先写图号和图名，PDF页码仅作补充。`citation_mode=cited` 使用 `standard_display_name`，不得显示规范文件路径或 `.pdf`；合法的 `citation_mode=none` 输出 `【法规条文】：无。`

没有正式意见时，仅在审查矩阵完整且所有不形成意见项均有理由的情况下输出“经审查，本次未形成正式审查意见”。

DOCX先写入工作区 `output`；内容校验和逐页视觉QA通过后，再显式复制到项目 `04_审图成果`。

End with the 12-type opinion note from `references/opinion-rules.md`.
