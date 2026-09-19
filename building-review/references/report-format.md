# Word 正式审查意见格式（v1.6）

新建工作区使用 v1.6。`issue_candidates.csv` 中只有 `ai_ready` 意见进入 Word，`report_section` 和 `display_order` 决定章节与连续编号。v1.1-v1.5 仅作兼容读取。

Use the existing templates:

- 总图: bundled `范本_建筑总图施工图审查意见.docx` in the skill directory
- 单体: bundled `范本_建筑单体施工图审查意见.docx` in the skill directory

## 标题与文件名

- 单体标题及文件名：`【AI初审】{项目名称}建筑施工图审查意见.docx`
- 总图标题及文件名：`【AI初审】{项目名称}建筑总图施工图审查意见.docx`
- 标题必须单独占一行，宋体18pt、加粗、居中；下一行为 `YYYY年M月D日`，宋体12pt、居中。
- 日期后直接进入第一节；不得设置独立封面或单独项目名称行。

不得添加审查人、目录、项目资料、项目画像、审查边界、风险或状态、过程说明、验证记录、证据来源或结论章节。标题是正文中唯一可见的 AI 阶段标识。

## Sections

For 总图, use template-style sections such as:
- `总图（建筑）施工图设计说明：`
- `总图设计图纸：`

For 单体, use only these template-style sections:
- `一、设计说明：`
- `二、平面图：`
- `三、立面、剖面图：`
- `四、大样图：`

单体允许的 `report_section`：`设计说明`、`平面图`、`立面剖面图`、`大样图`。总图允许：`总图设计说明`、`总图设计图纸`。

空章节必须在同一标题行写 `章节名：无意见`。`display_order` 只控制正式显示顺序；`issue_id` 保持稳定，不随排序变化。

## Opinion Items

意见贯穿全文连续编号。每条固定顺序为：

1. `编号及涉及图纸`
2. `【审查意见】`
3. 无标题证据图（按证据策略可为零张、一张或多张）
4. `【法规条文】`
5. `【意见类型】`

不得包含 `needs_review`、`rejected`、`delete` 或 v1.6 中的 legacy `verified` 意见。
Do not add delivery text such as `截图如下` or `截图说明`; screenshots should sit silently between `【审查意见】` and `【法规条文】`.

`涉及图纸` 使用真实图号和图名；脱敏后缺图号时使用 `PDF第N页《图名》`，不得补造图号。`citation_mode=cited` 使用 `standard_display_name`，不得显示规范文件路径或 `.pdf`；合法的 `citation_mode=none` 输出 `【法规条文】：无。`

审查矩阵完整且没有 `ai_ready` 意见时，不另写总结句，只按正式章节输出每个空章节的 `无意见`。

DOCX先写入工作区 `output`；内容校验和逐页视觉QA通过后，再显式复制到项目 `04_审图成果`。

文末必须原样保留：

`注：【意见类型】包含消防安全强制性条文、一般性条文、政策规定、设计深度与必须修改（消防安全）组合4种类型；其它强制性条文、一般性条文、政策规定、设计深度与必须修改（其它）、建议修改（其它）的两两组合共8种类型，共12种意见类型。`

生成器从对应正式 DOCX 范本继承页面设置、样式、编号和主题，清除范本原正文、原图片及关系，添加居中连续页码。内容验证后必须用 Microsoft Word 渲染并逐页检查，确认无截断、重叠、乱码、孤立标题或异常留白。

正文段落不得直接写入 `keepLines`、`keepNext`、`pageBreakBefore`、`suppressLineNumbers` 或 `widowControl` 等分页控制属性，避免在 Word 开启“显示编辑标记”时于段落左侧出现黑方块。分页质量由 Microsoft Word 全文渲染和逐页视觉 QA 控制；不得为维持固定页数重新加入这些属性。
