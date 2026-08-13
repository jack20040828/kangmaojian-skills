# 知识库地图

Raw knowledge base:

`BUILDING_REVIEW_KNOWLEDGE_BASE` or an explicit `--knowledge-base <path>`.

The public Skill contains indexing and search code only. Users must supply lawfully obtained local standards, policies, review guides, and project-specific materials; none are bundled in this repository.

## Resource Types

- `A_审查要点`: the entry point for checklist-led review. Convert these items into `check_matrix.csv` rows.
- `B_核心规范`: authoritative standards, policies, and source documents for article citations.
- `C_疑难解析`: interpretation guides, Q&A, training, and special judgment notes.
- `D_案例与截图`: high-frequency comments, screenshots, and prior cases. These never replace standards or project facts.
- `辅助识图`: drafting standards and common review Q&A.
- `政策文件`: Hunan, Changsha, and other local policies.
- `未知待整理`: files whose role is unclear from path/name.

The index layer normalizes inconsistent folder names. Do not rename raw folders unless the user explicitly asks.

## Review Routing

Always activate:
- `0000建筑制图标准`
- `000建筑施工图审查共性问题回复`
- `001建筑设计文件编制深度专项`

For every architectural single-building review, activate:
- 消防: `003建筑工程消防专项`.
- 民用建筑 or 工业建筑 according to project facts: `004民用建筑专项` or `011工业建筑专项`.
- 无障碍: `005建筑无障碍专项`.
- 防水: `006建筑防水专项`.
- 节能/绿建: `007建筑节能专项`, `020绿色建筑专项`.
- 建筑环境: `008建筑环境专项`.
- 湖南/长沙政策: `018湖南省政策规定专项`, `019长沙市政策规定专项` when local policy applies.

Activate by drawing/project facts:
- 总图: `002建筑总图专项`, local policy folders.
- 食堂、餐厅、厨房、饮食建筑: `022饮食建筑专项`.
- 宿舍、旅馆: `012宿舍、旅馆建筑专项`.
- 住宅: `013住宅建筑专项`.
- 车库: `009车库建筑专项`.
- 改造装修: `010改造装修专项`.
- 园林/环卫/垃圾减源: `014园林工程专项`, `015市容环卫工程专项`, `024垃圾减源专项`.
- 设备配套: `016设备配套专项`.
- 幕墙: `017建筑幕墙专项`.
- 装配式: `021装配式专项`.
- 人防: `025人防工程专项`.
- 幼儿园: `023幼儿园建筑专项`.
- 中小学校: `026中小学校专项`.
- 办公建筑: `027办公建筑专项`.
- 医院: `028医院建筑专项`.
- 电动车/充电车位: `029电动车专项`.

Do not route to administrative submission review, qualification review, seal review, geotechnical review, or non-architectural discipline drawing review.

## Citation Rule

When citing, record:
- source file path
- standard or policy name
- article number if available
- quoted or paraphrased requirement
- how it applies to the project fact
- whether current status needs outside verification

Cases cannot replace standards. If a case and a standard conflict, re-check the standard first.

## v1.4 可执行规则

- Read `review-rule-schema.md` before building or changing rules.
- Edit `references/review-rules-core.json`, then run `scripts/build_review_rules.py`; do not edit `generated/review-rules.json` directly.
- A normative rule is executable only when its basis resolves to a local B-source file with path, hash, article, and requirement.
- The generated catalog also contains design-depth coverage shells. They force topic inspection but cannot support an external technical violation.
- Snapshot the catalog for every new workspace. A catalog hash change invalidates the old checklist until routing and atomic expansion are repeated.

## v1.1 检索与版本规则

- 知识索引为每个文件记录大小和SHA-256，并用 `corpus_sha256` 标识整套知识库快照。
- 普通搜索先按专项、资料角色、文件名、路径和索引文本片段缩小范围。
- 只有在已限定专项时使用 `search_knowledge.py --deep --specialty <专项>`，避免无差别扫描整个知识库。
- PDF返回 `scan_or_unreadable` 或深度检索提示“需视觉/OCR核验”时，必须打开原文件或执行OCR，不得把无文本当成无规定。
- A类资料用于展开检查项，B类资料用于正式引用，C类资料辅助解释，D类资料只能提供发现方向和截图经验。
- `route_specialties.py --json` 输出候选专项、触发理由和最低 `required_topics`，不证明专项必然适用；确认适用后必须把对应主题逐项写入v1.3检查矩阵。
- `verified`意见引用的规范必须能唯一解析到索引文件，并进入工作区 `knowledge_snapshot.used_standards`。
- 知识库整体哈希或已引用规范哈希发生变化时，原验证失效；不得沿用旧的“通过”状态。
