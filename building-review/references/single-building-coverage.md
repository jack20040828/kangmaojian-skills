# 单体图纸族覆盖清单

单体审查先逐张图纸归类，再按本清单建立 `check_matrix.csv`。清单是最低覆盖面，不替代项目功能触发的专项审查。

## 覆盖状态

- 每张可识别图纸在 `drawing_inventory.csv` 填写一个 `review_family`。
- `reviewed`：已经形成至少一个实质且可追溯的 `check_id`。该检查项须写出本张图纸的图号或图名，链接本张图纸的 `fact_id`，并记录实际核对结果；合格项也必须保留。
- `not_applicable`：本张图确无可审内容，必须写图纸特定理由。
- `needs_review`：图纸未读清、缺页、无法渲染或判断未闭合。该状态阻断Word生成。

## 图纸族与最低检查主题

- `设计说明`：项目基本属性、地下室、面积/高度/层数、耐火等级、防火分类、节能与绿建、屋面防水等级、材料和专项说明之间的一致性。
- `目录索引`：图号、图名、详图索引和实际图纸可追溯性。纯文件整理问题默认不形成正式意见。
- `平面图`：功能与特殊使用场所、防火分区面积和分隔、安全出口、疏散宽度与距离、消防救援条件、无障碍和防护边界。
- `屋面图`：坡向、标高、雨水口/天沟/溢流/落水管、屋面材料厚度、防水层数、设备与可再生能源的建筑控制条件。
- `立面图`：建筑高度和标高、材料分格、洞口与救援窗、栏杆或女儿墙、防火及安全控制关系。
- `剖面图`：层高净高、楼梯和看台、屋面与露台、相邻空间关系、栏杆防护、构造落地关系。
- `楼梯大样`：详图名称与索引、梯段和平台、净宽净高、扶手栏杆高度、临空与楼梯井防护。
- `墙身大样`：详图索引和编号唯一性、栏杆/女儿墙高度、屋面与露台防水上翻、收头、压顶坡向和滴水。
- `其他大样`：节点与平立剖索引闭合，尺寸、材料、耐火、防水和安全做法可实施。
- `门窗表`：编号对应、洞口尺寸、开启与安全玻璃、防火门窗和救援窗要求。
- `材料做法表`：材料厚度、燃烧性能、防水层次、保温构造及与说明/详图的一致性。

## v1.4 必闭合主题ID

每张 `reviewed` 图纸应逐项关闭本图纸族的全部主题，并关闭项目画像为本图纸触发的全部可执行原子规则。确实不适用的主题也要建立有项目事实支撑的 `不适用` 检查，不得省略。

- `目录索引`：`document_traceability`
- `设计说明`：`project_identity_function`、`project_scope_consistency`、`code_basis_consistency`
- `平面图`：`function_layout`、`fire_egress`、`accessibility`、`wet_room_hygiene`、`safety_coordination`
- `屋面图`：`roof_drainage`、`roof_fall_protection`、`roof_access`、`renewable_energy_safety`
- `立面图`：`height_elevation`、`openings_rescue`、`facade_safety_weather`
- `剖面图`：`height_clearance`、`vertical_relationship`、`roof_guard`
- `楼梯大样`：`stair_geometry`、`stair_guard`、`roof_exit`
- `墙身大样`：`detail_traceability`、`window_sill_drainage`、`parapet_flashing`、`waterproofing_detail`
- `其他大样`：`detail_traceability`、`wet_room_drainage`、`accessibility_detail`、`detail_implementability`
- `门窗表`：`door_window_identity`、`fire_rescue_openings`、`door_window_safety`
- `材料做法表`：`project_applicability`、`material_performance`、`cross_drawing_consistency`
- `总图设计说明`：`project_identity_function`、`project_scope_consistency`、`code_basis_consistency`、`site_design_parameters`
- `总平面图`：`site_accessible_route`、`parking_special_spaces`、`site_fire_access`、`site_function_space`
- `竖向设计图`：`site_vertical_drainage`、`accessible_route_gradient`、`site_elevation_relationship`
- `交通消防图`：`site_fire_access`、`parking_special_spaces`、`pedestrian_vehicle_relationship`
- `其他总图`：`site_function_space`、`site_accessible_route`

项目事实还会触发跨图纸主题包：

- 宿舍、旅馆、酒店：单体关闭 `dormitory_refuse`、`dormitory_acoustics`、`accessible_room`、`accessible_room_detail`；总图关闭 `site_assembly_space`。
- 食堂、餐厅、厨房、备餐、洗消：关闭 `food_wet_room_vertical`。
- 电梯：关闭 `accessible_elevator`。
- 光伏或太阳能：关闭 `renewable_energy_safety`。
- 停车或车位：总图关闭 `parking_special_spaces`。

## 跨图纸闭环

- 设计说明、平面、立面、剖面、大样、门窗表和材料表出现同一事实时，分别记录事实并核对一致性。
- “图纸已提供”“可识别”“已有专篇”“大样覆盖完整”只说明文件存在，不能替代技术校核。无障碍、防水、屋面、栏杆、看台、消防救援口和卫生间等高风险主题，应按适用情况记录尺寸、数量、位置、坡度、荷载、性能等级或等价的客观图纸事实。
- 一个宽泛检查项不得批量关闭多张图纸。每个原子规则按图纸生成独立 `atomic_check_id`；若图号、图名和 `fact_ids` 不能指向本张图纸，该张图纸仍未形成有效闭环。
- 原子检查必须记录比较过程；要求计算的规则还要记录输入、方法和结果。“数量和宽度已核对”等摘要不能代替计算记录。
- 立面、剖面或大样图存在而正式意见章节为空并不自动构成漏审，但这些图纸必须各自留下实质的合格、不适用或待核验记录；不能借其他章节的检查项代替。
- 门扇开启、箭头、线型、剖切方向或“未表达”结论，必须核对图例和相关视图；不能唯一解释时保持 `needs_review`。
- 机电或结构图只作为协调接口，不据此形成建筑专业之外的技术结论。
