# 可执行审查规则（v1.6）

`generated/review-rules.json` 是审查矩阵的唯一可执行规则目录，由 `references/review-rules-core.json` 经 `scripts/build_review_rules.py` 生成；不得直接修改生成文件。

## 规则字段

每条规则至少包含：

- 稳定 `rule_id`、规则包、专项、适用图纸族和覆盖主题。
- `authority_mode`：`normative` 或 `design_depth`。
- `basis`：规范规则必须唯一解析到本地 B_核心规范的相对路径、SHA-256、条文和要求。
- `applicability_conditions`：逐项条件、期望值及 false 时的结果。
- `required_facts`、`comparison_method`、必要计算要求。
- `graphic_evidence_requirements`：是否必需、claim type、证据角色和歧义敏感性。
- 规则包与项目功能触发条件。

目录中的 legacy `independent_review_required` 仅供 v1.5 兼容。v1.6 不创建独立人工复核台账，也不把该字段作为完成门禁。

## v1.6 原子检查关闭条件

原子检查只有同时具备下列内容才可设为 `resolved`：

1. 规则 ID 与当前快照一致。
2. 图纸族、页码/图号/图名和项目事实可追溯。
3. 所有适用条件均有 `actual_value`、`fact_ids`、`drawing_refs`、结果和 `completed_at`；`unknown` 阻断关闭。
4. `actual_fact`、比较方法和比较记录完整。
5. 规则要求计算时，计算输入来自事实台账且计算记录完整。
6. 规范结论与 B 类 basis 的来源、条文和要求完全一致。
7. 图形 claim 已分类；所需角色全部进入 `graphic_evidence_chain.csv`，有截图、观察事实、解释、来源质量和 `completed_at`。
8. 对方向、符号、缺失和跨图等歧义敏感 claim，记录至少一个合理替代解释及排除依据。
9. `completion_gate=AI初审完成`；不得出现 `reviewer_gate`、`independent_review_id` 或人工姓名。
10. “不适用”必须由项目范围的正向事实支持，不能把“图纸未表达应有措施”当作不适用理由。

规范规则的结论可为 `符合`、`不符合`、`不适用`；证据或适用性未关闭时保持 `需核验`，不得设为 resolved。

## 权限边界

- A类审查要点可发现问题但不能作为正式规范引用。
- B类核心规范支撑技术结论。
- C类疑难解析解决适用、版本和解释问题。
- D类案例只辅助发现与差异比对。
- 设计深度规则不得伪装成外部技术条文。
- 脚本只能展开工作项和验证一致性，不能预填专业结论或 AI 完成状态。

## 兼容

v1.4/v1.5 继续按原字段与各自门禁读取；既有工作区不迁移。新建项目只能使用 v1.6。
