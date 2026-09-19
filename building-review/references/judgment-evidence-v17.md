# v1.7 判断证据与交付筛选

本文件在原子检查实施、候选意见筛选和最终审计时读取。v1.7 继承 v1.6 的 AI 独立初审流程，不增加人工身份或人工通过字段。旧工作区仍按原版本读取，不迁移、不补写历史通过状态。

## 判断记录

`judgment_evidence.json` 使用 `schema_version: "1.0"`，包含 `checks` 和 `issue_screening` 两个数组；它不是整理交付技能的输入合同。每次变更使完成审计失效。

每个 `checks` 对象对应唯一 `check_id`，有 `object_id`、`obligations`、`object_links`、`counterevidence`。生成器只生成待核验占位，不生成实际值、通过结果或完成声明。

- 义务来自规则的 `judgment_requirements.obligations`；未定制时，逐项展开 `required_facts` 为稳定的 F01、F02 等。不得删除不利的义务。
- 每项记录 `id`、`fact_ids`、`observation`、`reason`、`result`。结果为 `unknown`、`pass`、`fail`、`not_applicable`。引用必须属于本检查的事实；须看图后写具体观察及比较理由，不能复制通用“已核对”。
- 数值义务从事实台账的 `value/unit` 读取实际值，从规则读取 `threshold/unit/operator`。校验器统一 m/mm 和 ratio/% 后复算；不从自然语言猜值，不把洞口尺寸当净尺寸，不改写提交的专业结论。
- 条文包含多项要求时逐项关闭，例如净高、障碍物、标识分别核验；宽度合格不证明净高。某项不适用须为规则明确的条件性义务，记录 `scope_reason` 及正向事实。图上没有要求表达的内容不等于不适用。
- `counterevidence` 记录实际检索的 `fact_ids`、`finding: consistent|none_found|conflict|unknown`、具体 `reason`。冲突或未知阻断关闭。缺失断言设 `assertion: absent`，反证所见设 `observed: present|absent`；图上已有表达时不得继续发布“请补充同一内容”。无反证也须说明检索过哪些可能位置。

## 房间与外窗关联

窗地比等对象敏感计算必须先把 `object_linkage: room_window` 规则关闭。`object_links` 分别记录 room、exterior_wall、window_position、window_mark、schedule 五个角色，字段为 `role/object_id/related_object_id/fact_id/chain_id`，后两项另记 `mark`。

关联顺序为房间—外墙—墙上的窗—窗编号—对应门窗表。外墙 related_object_id 指向房间，窗位置指向外墙，窗编号和门窗表 object_id 指向同一窗对象；两处 mark 一致。各角色必须有事实和本检查图形证据链，同时写 `association_observation`，使阅读者能从清晰局部图重新建立对应关系。

这些 ID 检查只能发现已记录的关联矛盾，不能证明看图正确。必须实际检查房间边界和窗所在墙体；不得为了让校验通过而补造对象或关联。关联不清时保留待核验，即使算式正确也不得出确定意见。

## 候选意见筛选

每个候选 ID 在 `issue_screening` 中记录一次：`issue_id`、`responsibility: design|client_data|coordination|undetermined`、`delivery_decision: include|exclude|needs_review`、`reason`；正式交付另需 `design_action`。

- 技术是否成立、资料由谁提供、设计是否需整改分别判断。只有有依据的建筑设计整改或建筑协调动作进入正式意见。仅需甲方补资料的线索保留过程记录，不一概删除防氡检查。
- 目录须核对真实内容和名称。无图签、图号或页码导致的索引困难不是设计错误；`value_basis: index_difficulty_only` 不得形成正式意见。
- 同根因合并时保留全部整改对象，尤其总说明与节能专篇的旧依据分别追溯。不能让总说明的一条泛化意见吞掉专篇问题。
- 候选意见依据不足仍为 needs_review；不以“交付价值低”掩盖尚未解决的高风险技术问题。

## 补缺覆盖回归

专项说明及目录对应、淋浴防水翻起、条件性楼梯扶手、住宅噪声隔声、节能专篇依据、疏散净高及户门净宽、窗台排水及窗上口滴水，分别检查规则—路由—原子清单—事实—意见的去向。已存在规则修执行，不另造重复规则；所有正式技术要求回到本项目适用的原始 B 类来源及哈希，不照搬案例。

`judgment-rule-supplement.json` 保存经原始来源核验的覆盖增补及义务拆分，由 build_review_rules.py 与既有源规则一起生成运行目录。规范版本按实际项目适用日期复核，不将回归案例日期固化为通用日期。
