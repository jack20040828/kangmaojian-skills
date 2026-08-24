# 项目画像与专项路由（v1.6）

项目画像是 AI 初审的规则适用入口。它只记录可追溯的项目事实和 AI 完成状态，不设置人工确认、签名或裁决字段。

## 新工作区结构

v1.6 的 `project_profile.json` 使用：

- `schema_version: "1.1"`
- `review_stage: "ai_initial"`
- `ai_review_completed: true|false`
- `completed_at`
- `report_type: single|site`
- `facts`
- `route_completion`
- `discovery_tracks`

不得包含 `confirmed`、`confirmed_by`、`confirmed_at` 或 `route_confirmation` 等 legacy 人工字段。

## 项目事实

每个事实必须使用下列状态之一：

- `ai_completed`：AI 已从本地图纸事实关闭，必须填写 `value` 和至少一个 `fact_id`。
- `not_applicable`：项目事实明确证明不适用，必须填写理由。
- `unknown`：仍无法由图纸确认。任何必需事实保持 unknown 时，不得完成项目画像或生成 Word。

事实必须能回指 `fact_ledger.csv`，不得用经验、项目名称关键词或案例替代。

## 专项路由

运行 `scripts/route_specialties.py --json` 得到候选专项和触发理由。AI 依据项目画像、图纸和本地解析资料逐项判断：

- 已关闭时写 `route_completion.status = "AI初审完成"` 并记录 `completed_at`。
- 规则适用仍有歧义时，在过程台账保持开放；不得默认为适用或不适用，也不得创建人工确认门禁。
- 住宅、宿舍/旅馆、饮食、学校、车库、屋面、湿房间、电梯、光伏等功能触发包必须完整展开。

## 三条发现路径

`technical_compliance`、`design_depth`、`optimization` 均须由 AI 逐项完成并填写实质性 notes。只有三个状态均为 `completed`，才可设置 `ai_review_completed=true`。

## 兼容

v1.1-v1.5 工作区继续按各自旧字段读取，不迁移、不伪改。新建项目只能使用 v1.6。
