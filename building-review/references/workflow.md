# 审图工作流

## Phase 0 接收与建档

Create a project workspace before reviewing. Store all intermediate files there.

Required output:
- `drawing_inventory.csv`
- `fact_ledger.csv`
- `project_profile.json`
- `check_matrix.csv`
- `issue_candidates.csv`
- `validation_log.csv`
- `screenshots/`
- `output/`
- `completion_audit.json`（逐项完成后生成）
Project-local `output/` is for working files. Formal review reports generated without an explicit `--output` path must be written under `<project-workspace>\04_审图成果\`.

## Phase 1 图纸清点

Inventory every submitted file and every drawing sheet that can be identified.

Record:
- source file
- page or sheet number
- drawing name
- drawing number
- discipline
- scale if visible
- whether the page contains notes, legends, title block, index, tables, plan, elevation, section, detail, or schedule
- extraction confidence
- `review_family`, `review_status`, linked check IDs, and the reason for `not_applicable`

For single-building work, read `single-building-coverage.md`. Do not start issue writing before the inventory exists. Do not generate Word while an identifiable sheet is blank or `needs_review`.

## Phase 2 事实台账

Extract facts from drawings before judging compliance.

Always include:
- design notes and design basis
- title blocks and drawing stage
- technical/economic indicators
- fire classification, height, area, floors, occupancy, parking, accessible parking, green-building and energy-saving statements when present
- dimensions, elevations, coordinates, fire separation, evacuation, waterproofing, accessibility, equipment-room, and local-policy facts relevant to the project

If a value is explicitly shown, record the value. Do not write `需核实` merely because it was easy to miss.

## Phase 3 项目画像与专项路由

For v1.4, complete and reviewer-confirm `project_profile.json` before choosing the review path. Unknown facts do not justify `不适用`; they keep related rules open.

Choose only the needed review path after Phase 1 and Phase 2:
- 总图
- 民用建筑单体
- 工业建筑单体
- 改造装修
- 园林绿化
- policy-only or consultation task

For 建筑专业施工图技术审查:
- Do not review administrative submission materials, planning permits, geotechnical reports, qualifications, stamps, signatures, or registered-professional seal validity.
- Do not review structural, plumbing, electrical, or HVAC drawings themselves.
- Do review architectural drawing completeness, project attributes, and architectural responsibilities for fire safety, energy, green building, accessibility, waterproofing, civil defense, curtain wall, decoration, food-service, and similar specialties.

For each active specialty, read or search A_审查要点 first through a user-built `knowledge-index.json` or `scripts/search_knowledge.py`. Use B_核心规范 for article citations, C_疑难解析 for judgment support, and D_案例与截图 only after fact matching.

Function facts trigger specialties. If the fact ledger shows dormitory, hotel, canteen, restaurant, kitchen, school, parking, charging, accessibility, waterproofing, green-building, energy-saving, carbon-reduction, Hunan local policy, or special fire-review facts, activate the matching specialty and convert its A_审查要点 into check rows. Do not rely on general civil-building checks when a function-specific specialty applies.

## Phase 4 原子审查矩阵

After the project profile and sheet families are ready, run `scripts/generate_project_checklist.py <workspace>`. It creates `unreviewed/需核验` rows from the executable catalog. Never programmatically promote them to `符合` or mark drawings reviewed.

Create `check_matrix.csv` before writing candidate issues. After recording repeated facts from different sheets, run `scripts/check_cross_sheet_consistency.py <workspace>` and record each conflict in the design-depth discovery track. The comparator only reports differing recorded values; it cannot decide which sheet is correct.

For every applicable active specialty, turn A_审查要点 items into checkable rows. For each row, record:
- specialty and check_id
- source review point
- applicability
- required drawing fact
- actual drawing fact and location
- standard source and article
- conclusion: `符合`, `不符合`, `需核验`, or `不适用`
- whether it forms a candidate/final issue
- reason when it does not form a formal opinion
- v1.4 rule ID, atomic ID, decision state, applicability basis, discovery track, comparison method and record, calculation record, open reason, and reviewer gate

Only `不符合` and selected high-risk `需核验` items become candidate issues. Do not write formal opinions directly from user notes, OCR snippets, or high-frequency cases; every formal issue must pass through the matrix.

## Phase 5 候选意见验证

Validate each candidate issue before final report:
- the issue has a matching `check_matrix.csv` row by `check_id`
- drawing fact exists in `fact_ledger.csv`
- local standard/source was searched or opened
- standard citation is specific enough to re-check
- specialty route is correct
- high-frequency case is matched only as supporting reference
- screenshot positioning is recorded when screenshot is required
- screenshot strategy is recorded as `none`, `single`, `multiple`, or `shared`
- the citation strategy is `cited` or the narrowly controlled design-depth `none` path
- drawing references contain the linked drawing number and drawing name; PDF page is supplementary only
- graphical interpretation and opinion wording gates are passed
- the candidate has passed professional filtering: merge duplicates, delete non-issues, downgrade weak evidence to `needs_review`, and keep only issues a construction drawing reviewer would deliver to the owner/designer
- opinion type is one of the 12 approved categories

Candidate status values:
- `verified`: evidence complete; may enter formal Word.
- `needs_review`: plausible but incomplete; keep in ledgers only.
- `rejected`: checked and not a formal issue; keep reason in ledgers.
- `delete`: remove from final consideration.

If any validation check fails, fix the candidate, downgrade it to `needs_review`, or mark it `rejected/delete`.

## Phase 5.5 截图证据复核

Decide screenshot strategy before Word generation:
- `none`: no screenshot is inserted; use only when the exact text is already quoted or the issue is purely explanatory. Record the exemption reason.
- `single`: default for one local evidence point.
- `multiple`: two or more screenshots are indispensable, such as a cross-sheet conflict; record why one screenshot cannot prove the issue.
- `shared`: one screenshot is intentionally reused by several related issues; record the shared evidence reason.

For every required screenshot, record the evidence point, red-box target, and context that must remain visible. The screenshot must let the owner or designer see where to revise without reading the working ledgers.

## Phase 6 Word 报告

First snapshot sources, the executable rule catalog, and all used standards. Run `scripts/audit_review_completeness.py`; resolve every listed open item. Then run `scripts/validate_review_package.py`. Generate Word only after both pass. Any later change to the manifest, profile, or ledgers invalidates the completion audit.

The final report must contain only `verified` issues and must follow `references/report-format.md`. Do not include working ledgers, review scope, basis, conclusions, screenshot explanations, or evidence summaries in the formal Word unless the user explicitly asks for a separate supporting document.

## v1.4 完整性与交付门禁

新工作区执行以下顺序：

1. `review_manifest.json` 固定 `schema_version=1.4`、`report_type` 和规则目录快照；验证器与生成器继续兼容读取v1.1至v1.3工作区。
2. 图纸与派生资料放入工作区 `source/`，不得修改项目原件。
3. 填写并由审查人确认 `project_profile.json`；未知事实保持开放，地区政策按所在地触发。
4. 每张可识别图纸填写 `review_family`，运行 `scripts/generate_project_checklist.py` 展开全部图纸族和项目事实触发的原子规则。新检查默认 `unreviewed/需核验`。
5. 运行 `scripts/route_specialties.py --json` 并由审查人确认；任何不确定路由、已触发主题或原子规则未闭合时保持 `needs_review`。
6. 分别完成技术条文、设计深度/内部矛盾和优化建议三次发现；运行 `check_cross_sheet_consistency.py` 核对跨图重复事实，解决或保留每个冲突，并在项目画像中记录完成情况。
7. 每条已关闭技术检查记录图纸事实、B类条文、比较过程和必要计算；高风险项必须人工复核。再合并同一根因、拆开混合根因。
8. 正式意见填写稳定 `issue_id`、连续 `display_order`、明确章节、引用模式和人工验证门禁。
9. 运行 `snapshot_review_integrity.py`，记录全部source、规则目录以及正式意见和技术闭环实际使用的规范哈希。
10. 运行 `audit_review_completeness.py`，清零开放项后运行 `validate_review_package.py`。
11. 通过后生成Word，完成内容校验、逐页渲染和视觉QA，最后复制到项目 `04_审图成果`。

`validation_log.csv` 的 `layout_check` 不代表最终Word视觉QA。生成前允许保持 `待检查`；最终门禁只认渲染后的 `report_qa.json`。
