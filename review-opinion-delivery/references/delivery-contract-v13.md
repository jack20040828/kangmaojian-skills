# v1.3：忠实整理、图片对应与引用联动

新工作区默认 v1.3。旧 v1.0–v1.2 按原版本验证；创建器发现版本不一致即停止，不自动迁移。整理台账独立，不导入技术审查矩阵；这些检查只核对作者已确认内容和证据记录的一致性，不识别新问题、不替作者形成专业结论。

## 1. 来源处置与确认

`source/` 分别保留摘要、录音转写、图面、确认文字及最新 Word 原件，统一 SHA-256 快照。清单新增：

- `source_items`：每个原始意见有独立 `source_id`、`source_ref`、`disposition`（included/merged/withdrawn/excluded）、`reason`、`item_ids`。撤销/排除必须有 `confirmation_ref` 且无交付映射；合并必须双向对应。
- `source_conflicts`：分别列明摘要、转写、图面和确认文字的差异；实质差异必须 `status: resolved` 且有 `resolution_ref`，否则停止。确定性转录纠正写编辑日志，不能借纠正扩大范围。
- 每项 `source_ids`、`approval_ref`、`approved_content`；后者完整保存四个批准字段 `opinion_text/regulation_text/opinion_type/drawing_refs`。脚本与台账、Word 精确对比，不再仅验证批准句子“包含在”更长文字中。确认记录必须来自审查者，不得自己复制当前文字充当授权。
- `value_origins`：涉及技术数值逐一记录 `value/origin/source_ref`，origin 为 reviewer_remedy/code_requirement/drawing_fact。审查者提出的洞口整改尺寸与规范通行净宽分开记录，前者禁止充当法规最低值。
- `scope_changes`：跨图同步要求仅先提示审查者；纳入正式文字必须 `included: true, status: approved, approval_ref`。新增授权同步更新批准字段，不得自行增加平面、立面、门窗表的整改义务。

## 2. 每句文字对应哪张图

每项 `claims`：`claim_id/text_quote/object_label/requires_image`。`text_quote` 是批准意见中需图像证明的关键短句，覆盖全部关键值、限定条件和对象。无图的纯文字意见须 `no_image_reason`，不能用豁免掩盖缺证据。

每张 `evidence_images` 新增：

- `evidence_id` 稳定且全局唯一；`image_sha256` 是实际 PNG/JPEG 或原 Word 媒体文件哈希；保持顺序。
- `observed_evidence` 列表，每项 `claim_id/object_label/visible/observation`。必须实际看清关键文字、数值、构件和限定条件，不能只因“沿用已确认 Word”就填通过。地面与楼面、卧室与卫生间是不同对象。
- `word_crop: [left,top,right,bottom]` 为 0–1 裁切比例；`display_width_inches` 为 Word 实际显示宽度。保留原图仍核对 DOCX 内裁切和缩放。文本关键位置被裁掉或过小，先修复再验收。
- `evidence_history` 保留旧图 `evidence_id/source_ref/disposition/reason`；replaced 还需 `replacement_ids`。精简只从交付移除，不删除过程证据；替换要明确对象是否变化、为何仍支持原句。

## 3. 独立裁切框和问题框

新截图记录 `crop_box/problem_boxes/source_size`，均为原始渲染像素坐标，问题框逐点设置；裁切扩大不得改变问题框。`context_anchor` 记录轴号、房间名、表头、尺寸链或节点上下文。默认红色；用户指定黄色等用 `mark_color/color_authorization_ref`。

取景优先为问题框共同包络宽、高各 2–3 倍；不足方向扩至约 2.5 倍，已经充分方向不变。页边限制写 `boundary_limitation`，必要时拆图；不得用整图红框或边界贴框掩盖证据不足。若保留定位需超过 3 倍，应目视确认可读性，不能机械缩小而丢上下文。

`compose_evidence_cards.py` 使用 `source_problem_boxes`（原图绝对坐标）、`crop`、`source_image/source_pdf/source_page`；生成 `.geometry.json` 记录实际裁切。将结果和颜色授权回填台账。新交付默认纯局部截图，不使用装饰卡头、灰底或外红框；保留旧相对坐标接口仅为兼容。

## 4. 稳定 ID 与严格定位例外

正式序号按 `item_id → item_no`，删项、合并、重排后更新所有主编号、续图和交叉引用。用 `sync_docx_references.py <workspace> <base.docx> <mapping.json> --output <workspace>/output/<new.docx>`，映射每项为：

```json
{"paragraph_index": 8, "before_text": "第9条续", "kind": "continuation", "occurrence": 0, "item_id": "OP-010"}
```

kind 可为 main/continuation/cross_reference；段落序号 0 起算，显式人工核对所属稳定 ID。禁止只凭旧序号猜归属。保留格式替换数字并生成引用编辑日志。最终清单 `docx_references` 记录最终段落序号、occurrence、item_id（续图/交叉引用）；校验正文每一处“第N条”均映射且序号正确。主编号另有连续性、唯一性检查。

默认 `location_policy.mode: drawing_number_title`。仅有用户明确授权时允许 `pdf_page_title` 并记录 `authorization_ref`，所有 `drawing_no` 空值，定位仅为 `PDF第N页《图名》`（N≥1，可用分号并列）。这仅豁免定位格式，笔记编号、坐标、核验过程等仍不得进入正文。

## 5. 内容与页面验收

依次执行包校验、DOCX 校验、Microsoft Word 导出、逐页渲染、实际目视检查、页面 QA 校验。使用 `render_pdf_pages.py ... --docx ... --qa-csv <workspace>/report_qa.csv`：v1.3 自动绑定清单、DOCX、PDF、每页 PNG 的哈希，填入全部页数；初始化一律待检查，不自动通过。

QA 另核对图片对应、引用编号、文字流、Word 内裁切。所有意见或排版修改后必须重新渲染并重检，旧哈希不通过；联系表不冒充单页渲染。脚本无法判断图片是否真的看清专业内容，必须由操作者逐页检查并如实记录。

匿名回归 `evals/test_v13_delivery_contract.py`：每类错误有有效通过样例；运行旧版回归确保兼容。真实项目、截图、笔记和完整规范不进入公开仓库。
