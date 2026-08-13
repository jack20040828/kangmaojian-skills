# 项目画像

v1.4 在逐项审图前必须完成 `project_profile.json`。项目画像只记录已经从图纸取得或经审查人确认的事实，不是对项目的猜测。

## 状态

每项事实使用：

- `confirmed`：值已由图纸事实支持，填写 `fact_ids`。
- `not_applicable`：确实不适用，并在 `notes` 中写明原因。
- `unknown`：尚不能确定；相关规则保持未决并阻断正式报告。

## 必填事实

包括所在地、建筑使用性质、工业属性、是否留宿、面积、高度、层数、火灾危险性、耐火等级、使用人数、喷淋、地下室、电梯、无障碍要求、上人屋面、有水房间、停车、光伏或太阳能、饮食、宿舍或旅馆、学校、办公及儿童活动功能。

`confirmed=true` 只表示审查人确认项目画像已经核对，不会把仍为 `unknown` 的关键事实变成已知。关键事实未知时，完成度验证仍失败。

## 专项和三次发现

- `route_confirmation.confirmed`：审查人已经核对专项路由结果。
- `discovery_tracks.technical_compliance`：技术条文检查。
- `discovery_tracks.design_depth`：设计深度、套图残留和内部矛盾检查。
- `discovery_tracks.optimization`：有依据的优化建议检查。

三个发现路径均需设为 `completed` 并留下简短记录，不能由程序自动填写。
