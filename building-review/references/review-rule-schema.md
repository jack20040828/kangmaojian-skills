# 可执行审查规则

`generated/review-rules.json` 是 v1.4 审查矩阵的唯一可执行规则目录。它由
`scripts/build_review_rules.py` 从 `references/review-rules-core.json` 生成；不得直接手改生成文件。

## 规则字段

- `rule_id`：稳定且唯一的规则编号。
- `status`：仅 `active` 可进入新项目检查表。
- `authority_mode`：
  - `normative`：可支持技术符合或不符合结论，必须关联本地 B 类规范、条文和要求。
  - `design_depth`：只检查图纸表达、内部矛盾和可实施性；不得主张外部技术阈值。
- `specialty`：所属专项。
- `coverage_topic`：所属覆盖主题。
- `review_families`：适用图纸族。
- `report_types`：`single`、`site` 或两者。
- `trigger`：由 `project_profile.json` 事实决定是否激活。事实未知时规则保持候选并生成未决检查，不能静默跳过。
- `required_facts`：必须从图纸取得的事实。
- `comparison_method`：要求的比较或核对方法。
- `calculation_required`：为 `true` 时，关闭检查前必须记录计算输入、公式和结果。
- `risk_level`：`high`、`medium` 或 `normal`。
- `basis`：规范性规则的本地 B 类来源、显示名称、条文和要求。

## 关闭条件

v1.4 原子检查只有同时具备下列内容才可设为 `resolved`：

1. 明确的适用性及其项目事实依据；
2. 本张图纸的事实、`fact_ids` 和图纸定位；
3. 比较方法及比较记录；
4. 规范性规则对应的 B 类来源、条文和要求；
5. 需要计算时的计算记录；
6. `符合`、`不符合` 或证据充分的 `不适用` 结论。

缺一项时使用 `unreviewed` 或 `needs_review`，结论保持 `需核验`。一个覆盖主题只有在该图纸所有已触发原子规则都关闭后才算关闭。

## 来源边界

- A 类资料用于发现和拆分规则。
- B 类资料是 `normative` 规则的正式依据。
- C 类资料只用于解释适用边界。
- D 类案例只用于发现方向，不能写入 `basis`。
- 找不到准确 B 类条文的技术要求不得伪造为活动规范规则。
