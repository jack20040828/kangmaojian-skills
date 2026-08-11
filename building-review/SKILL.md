---
name: building-review
description: Evidence-driven architectural construction-drawing technical review for Chinese building projects. Use when Codex must inspect architectural drawings and form new review conclusions for 总图审查、建筑单体审查、建筑专项审查、建筑施工图审查意见, using project facts, local standards, evidence screenshots, and Word reports. Do not use when reviewer-authored opinions already exist and only need consolidation or delivery; use review-opinion-delivery instead. Do not use for generic Word editing, administrative submission review, or technical review of structural, plumbing, electrical, or HVAC drawings. Split mixed review-and-delivery requests into separate phases.
---

# 建筑施工图审查

Review architectural construction drawings and form new technical conclusions. Keep the boundary, evidence chain, and delivery gates mandatory; load detailed rules only when their phase is active.

## Boundary

- Review architectural drawings and architecture-owned fire safety, accessibility, energy, green building, waterproofing, civil defense, curtain wall, decoration, food-service, and similar specialties.
- Do not review administrative submissions, permits, qualifications, stamps, signatures, or registered-professional seals.
- Do not technically review structural, plumbing, electrical, or HVAC drawings. Record only architecture-owned facts or coordination issues.
- If opinions already exist and the task is only to organize evidence and Word delivery, switch to `review-opinion-delivery` without changing conclusions.
- If a request asks for both new review and delivery, complete this skill's verified opinions first, then start the delivery workflow as a separate phase.

Read `references/scope-boundary.md` before accepting borderline or mixed work.

## Core Workflow

1. Create or identify a review workspace. For an existing project, pass `--root <项目>\03_审图过程` explicitly to `scripts/create_review_workspace.py`.
2. Inventory drawings before judging them. Complete `drawing_inventory.csv` and `fact_ledger.csv` from design notes, indexes, legends, title blocks, tables, and drawings. Classify every identifiable sheet and close it with a check that names the sheet and links at least one fact from that sheet; “图纸已提供”“大样覆盖完整” are not review conclusions.
3. Route applicable specialties with `scripts/route_specialties.py`; treat its output as candidates requiring confirmation against project facts.
4. Search A_审查要点 first, B_核心规范 for formal citations, C_疑难解析 for interpretation, and D_案例与截图 only as non-substitutive reference.
5. Build `check_matrix.csv` before `issue_candidates.csv`. Keep stable IDs separate from formal display order.
6. Decide screenshot strategy and record the exact evidence point, red-box target, and necessary context.
7. Snapshot project sources and used standards with `scripts/snapshot_review_integrity.py`.
8. Run `scripts/validate_review_package.py <workspace>`. Do not generate Word if it fails.
9. Generate the proper template report with `scripts/generate_review_report.py`; default output is `<workspace>\output`.
10. Run `scripts/validate_docx_content.py`, render every page, inspect every rendered page, record QA with `scripts/validate_report_qa.py`, then copy the final DOCX to the user-selected deliverables directory.

## Phase References

- Runtime dependencies and public configuration: `references/runtime-requirements.md`

- Intake and phase gates: `references/workflow.md`
- Scope and task handoff: `references/scope-boundary.md`
- Drawing facts: `references/evidence-ledger.md`
- Single-building sheet-family coverage: `references/single-building-coverage.md`
- Knowledge routing: `references/knowledge-map.md`
- Check-matrix construction: `references/checklist-rules.md`
- Candidate filtering: `references/opinion-rules.md`
- Screenshot evidence: `references/screenshot-protocol.md`
- Word structure: `references/report-format.md`
- Failure patterns before verification: `references/gotchas.md`
- Confirmed single-building retrospective: `references/single-building-retrospective.md`

## Mandatory Gates

- A formal issue must link drawing inventory, project fact, review judgment, and screenshot evidence when visual proof is needed. Technical requirements also require an applicable local source; narrowly defined design-depth issues may use the controlled `citation_mode=none` path.
- Never cite a standard from memory. Missing, stale, ambiguous, or changed sources stay `needs_review` or `需核验`; do not use `citation_mode=none` to bypass a missing technical basis.
- Do not generate Word while any identifiable sheet is unclassified or has `review_status=needs_review`.
- A `reviewed` sheet must link at least one substantive sheet-specific check. A broad check, a check that does not reference the sheet, or a presence-only statement cannot close coverage. Accessibility, waterproofing, roofs, guardrails, stands, rescue openings, and wet rooms require objective dimensions, quantities, locations, slopes, loads, performance levels, or equivalent drawing facts as applicable.
- A check whose applicability is still `需判断` or whose conclusion is `需核验` cannot support a `verified` issue.
- Do not verify graphical direction, symbol meaning, or missing-expression claims until the legend and relevant plan/section/detail context form a closed evidence chain.
- Never copy a case or high-frequency issue into the report without matching project facts and recording differences.
- Merge duplicates, reject weak items, and include only `verified` issues in Word.
- Scripts validate traceability and consistency; they do not prove professional judgment is technically correct.
- Never mark visual QA passed before opening and checking every rendered page.
- Do not add non-template report chapters.
- Run every AutoCAD or `accoreconsole` command through `scripts/run_cad_script_safely.py --timeout <seconds> -- <command...>`. Never invoke CAD directly when a generated script can change `FILEDIA` or `CMDDIA`; the wrapper must remain alive until the CAD child exits so its `finally` restoration runs.
- Any `.scr` that sets `FILEDIA` or `CMDDIA` to `0` must restore both to `1` before every `QUIT` and before script end. The safe runner must reject a script that fails this preflight gate.

## Defaults

- Set `BUILDING_REVIEW_KNOWLEDGE_BASE` or pass `--knowledge-base <path>` when building a private local index. This public package does not include standards, policies, cases, or project files.
- Set `BUILDING_REVIEW_INDEX_DIR` when building the index and `BUILDING_REVIEW_INDEX` when searching or snapshotting it; otherwise the scripts use `./building-review-index` under the current working directory.
- Set `BUILDING_REVIEW_PROJECT_ROOT` or pass `--root <path>` for workspace creation; otherwise the script uses `./building-review-projects` under the current working directory.
- Keep raw knowledge files and real project source files unchanged. Store indexes, ledgers, snapshots, screenshots, and drafts outside the raw knowledge base.
- Prefer local sources. Browse only when local sources cannot resolve a current standard or policy question, or the user explicitly asks for current official status.
- New single-building v1.2 reports default to `建筑单体施工图内审意见` and the confirmed internal-review section style; explicit report-title and output arguments may override the defaults.
