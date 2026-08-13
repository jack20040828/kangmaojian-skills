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

1. Create or identify a review workspace. New workspaces use schema v1.4. For an existing project, pass `--root <项目>\03_审图过程` explicitly to `scripts/create_review_workspace.py`.
2. Inventory every sheet and extract facts before judging. Complete `drawing_inventory.csv` and `fact_ledger.csv`; unresolved identity or version facts stay `needs_review`.
3. Read `references/project-profile.md`, complete `project_profile.json`, and obtain reviewer confirmation. Route specialties with `scripts/route_specialties.py --json`; confirm uncertain routes instead of trusting keywords.
4. Read `references/review-rule-schema.md`. Run `scripts/generate_project_checklist.py <workspace>` after classifying sheets. It expands the snapshotted rule catalog into unreviewed atomic checks; it never supplies compliance conclusions.
5. Review every atomic check from drawings. Search A_审查要点 for discovery, B_核心规范 for formal citations, C_疑难解析 for interpretation, and D_案例与截图 only for non-substitutive hints. Record applicability facts, drawing facts, comparison, calculations, conclusion, and reviewer gate. Use `scripts/review_calculations.py` for supported numeric comparisons; it never supplies missing inputs or an applicable limit.
6. Perform technical compliance, design-depth/internal-consistency, and supported-optimization discovery separately. Run `scripts/check_cross_sheet_consistency.py <workspace>` after recording repeated facts; resolve every reported conflict from the drawings. Keep high-risk uncertainty open; do not default it to compliant or discard it.
7. Build `issue_candidates.csv` only from resolved noncompliant checks. Decide screenshot strategy and record the exact evidence point, red-box target, and necessary context. v1.4 validation gates must be manually reviewer-confirmed.
8. Snapshot sources, the rule catalog, and every standard used by verified issues or resolved technical checks with `scripts/snapshot_review_integrity.py`.
9. Run `scripts/audit_review_completeness.py <workspace>`. Fix every open item. Run `scripts/validate_review_package.py <workspace>` only after the audit passes; any later ledger change makes the audit stale.
10. Generate Word with `scripts/generate_review_report.py`, validate content, render every page, inspect every rendered page, record QA, then copy the final DOCX to the user-selected deliverables directory.

## Phase References

- Runtime dependencies and public configuration: `references/runtime-requirements.md`
- Intake and phase gates: `references/workflow.md`
- Scope and task handoff: `references/scope-boundary.md`
- Drawing facts: `references/evidence-ledger.md`
- Single-building sheet-family coverage: `references/single-building-coverage.md`
- Knowledge routing: `references/knowledge-map.md`
- Check-matrix construction: `references/checklist-rules.md`
- Project facts and reviewer confirmation: `references/project-profile.md`
- Executable atomic-rule schema: `references/review-rule-schema.md`
- Candidate filtering: `references/opinion-rules.md`
- Screenshot evidence: `references/screenshot-protocol.md`
- Word structure: `references/report-format.md`
- Failure patterns before verification: `references/gotchas.md`
- Confirmed single-building retrospective: `references/single-building-retrospective.md`

## Mandatory Gates

- A formal issue must link drawing inventory, project fact, review judgment, and screenshot evidence when visual proof is needed. Technical requirements also require an applicable local source; narrowly defined design-depth issues may use the controlled `citation_mode=none` path.
- Never prefill `符合`, `reviewed`, validation `通过`, or reviewer confirmation. New checks start `unreviewed/需核验`; scripts may expand required work but may not close it.
- A v1.4 technical `符合` or `不符合` requires a rule ID resolving to an active B-source rule, sheet-specific facts, comparison record, and required calculation record. Design-depth rules cannot carry technical citations.
- A v1.4 report requires a reviewer-confirmed project profile, specialty route, three completed discovery tracks, all triggered atomic rules resolved, a current integrity snapshot, and a current passing completion audit.
- Never cite a standard from memory. Missing, stale, ambiguous, or changed sources stay `needs_review` or `需核验`; do not use `citation_mode=none` to bypass a missing technical basis.
- Do not generate Word while any identifiable sheet is unclassified or has `review_status=needs_review`.
- A v1.3 or v1.4 `reviewed` sheet must close every required sheet-family topic with matching atomic checks, evidence classes, drawing references, and facts. v1.4 additionally requires every profile-triggered executable rule for that sheet. A broad check, an unrelated number, a check that does not reference the sheet, or a presence-only statement cannot close coverage.
- Run a project-identity and scope-consistency pass across design notes, specialties, schedules, and title blocks. Treat wrong project names, functions, basement/elevator statements, and stale design bases as technical design-depth candidates rather than packaging noise.
- Complete function-triggered packets before Word generation. Dormitory, food-service, school, parking, elevator, photovoltaic/solar, wet-room, roof, and wall-detail facts must activate their corresponding topics; unresolved topics block the report.
- Discover and filter three tracks separately: mandatory noncompliance, design-depth/internal contradiction, and supported optimization advice. Do not let conservative filtering silently discard an unresolved high-risk item; retain it as `needs_review` until the evidence chain closes.
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
- New reviews use v1.4 atomic rules and retain the confirmed internal-review titles and section style. v1.1-v1.3 workspaces remain readable for compatibility, but legacy technical closures without precise standard fields are no longer accepted as complete.
