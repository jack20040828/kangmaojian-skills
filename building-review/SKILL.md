---
name: building-review
description: Evidence-driven architectural construction-drawing technical review for Chinese building projects. Use when Codex must inspect architectural drawings and form new review conclusions for 总图审查、建筑单体审查、建筑专项审查、建筑施工图审查意见, using project facts, local standards, evidence screenshots, and Word reports. Do not use when reviewer-authored opinions already exist and only need consolidation or delivery; use review-opinion-delivery instead. Do not use for generic Word editing, administrative submission review, or technical review of structural, plumbing, electrical, or HVAC drawings. Split mixed review-and-delivery requests into separate phases.
---

# 建筑施工图审查

Review architectural construction drawings, form new technical conclusions, and directly deliver a complete AI initial-review Word report. The AI runs every skill gate independently; human review belongs to a later external workflow and is neither requested nor represented here.

## Boundary

- Review architectural drawings and architecture-owned fire safety, accessibility, energy, green building, waterproofing, civil defense, curtain wall, decoration, food-service, and similar specialties.
- Do not review administrative submissions, permits, qualifications, stamps, signatures, or registered-professional seals.
- Do not technically review structural, plumbing, electrical, or HVAC drawings. Record only architecture-owned facts or coordination issues.
- If opinions already exist and the task is only to organize evidence and Word delivery, switch to `review-opinion-delivery` without changing conclusions.
- If a request asks for both new review and delivery, complete this skill's `ai_ready` opinions and formal AI-initial DOCX first. Use `review-opinion-delivery` only later, when reviewer-authored additions already exist and need consolidation.

Read `references/scope-boundary.md` before accepting borderline or mixed work.

## Core Workflow

1. Create or identify a review workspace. New workspaces use schema v1.7 with `review_stage: ai_initial`. For an existing project, pass `--root <项目>\03_审图过程` explicitly to `scripts/create_review_workspace.py`. Schemas v1.1-v1.6 remain readable compatibility formats; do not migrate an existing workspace in place.
2. Inventory every sheet and extract facts before judging. Complete `drawing_inventory.csv` and `fact_ledger.csv`; unresolved identity or version facts stay `needs_review`.
3. Read `references/project-profile.md`; the AI completes `project_profile.json`, records `ai_review_completed`, and closes specialty routing with `AI初审完成`. Route specialties with `scripts/route_specialties.py --json`; resolve uncertain routes from project facts and keep unsupported routes open rather than asking for a human confirmation gate.
4. Read `references/review-rule-schema.md`. Run `scripts/generate_project_checklist.py <workspace>` after classifying sheets. It expands the snapshotted rule catalog into unreviewed atomic checks plus v1.6 applicability and graphic-evidence placeholders; it never supplies compliance conclusions. For a residential single-building profile, ensure that `residential_core_v1` is present in full; missing drawings do not waive a packet rule and the package gate will block completion.
5. Review every atomic check from drawings and use all four local knowledge layers: A_审查要点 for discovery, B_核心规范 for formal citations, C_疑难解析 for applicability and interpretation, and D_案例与截图 for auxiliary comparison only. Record each layer's sources and use in `knowledge_snapshot.layers`; D never replaces drawing facts or B. Resolve every rule condition in `applicability_decisions.csv`. For dimension, direction, symbol, absence, location, detail, or cross-sheet claims, close `graphic_evidence_chain.csv` with the required drawing roles, exact location, observed fact, interpretation, source quality, screenshot, and—when ambiguity-sensitive—an alternative interpretation plus its elimination basis. Record comparison, calculations, conclusion, and `completion_gate=AI初审完成`. Use `scripts/review_calculations.py` for supported numeric comparisons; it never supplies missing inputs or an applicable limit.
6. Perform technical compliance, design-depth/internal-consistency, and supported-optimization discovery separately. Run `scripts/check_cross_sheet_consistency.py <workspace>` after recording repeated facts; resolve every reported conflict from the drawings. Keep high-risk uncertainty open; do not default it to compliant or discard it.
7. Build `issue_candidates.csv` only from resolved noncompliant checks. Mark a deliverable issue `ai_ready` only after every AI validation field passes with `gate_origin=agent` and `stage_completion=AI初审完成`. v1.6 does not create `independent_review_log.csv`, record reviewer names, request human confirmation, or perform human adjudication. Decide screenshot strategy and record the exact evidence point, red-box target, and necessary context in the process ledgers.
8. Snapshot sources, the rule catalog, all four knowledge-layer use records, and every standard used by `ai_ready` issues or resolved technical checks with `scripts/snapshot_review_integrity.py`.
9. Run `scripts/audit_review_completeness.py <workspace>`. Fix every open item. Run `scripts/validate_review_package.py <workspace>` only after the audit passes; any later ledger change makes the audit stale.
10. Generate Word with `scripts/generate_review_report.py`, validate it with `scripts/validate_docx_content.py`, render every page, inspect every rendered page, record QA, then copy only the final DOCX to the user-selected deliverables directory. The filename and one-line title are `【AI初审】{项目名称}建筑施工图审查意见.docx` for a single building and `【AI初审】{项目名称}建筑总图施工图审查意见.docx` for a site review.

## Phase References

- Runtime dependencies and public configuration: `references/runtime-requirements.md`
- For every v1.7 review, read `references/judgment-evidence-v17.md` before closing checks or screening issues. Complete obligation-level comparisons, room-window associations when required, counterevidence searches, and responsibility/value screening in `judgment_evidence.json`; package validation and the completion audit enforce this ledger. Neither missing issue IDs nor populated prose fields prove compliance.

- Intake and phase gates: `references/workflow.md`
- Scope and task handoff: `references/scope-boundary.md`
- Drawing facts: `references/evidence-ledger.md`
- Single-building sheet-family coverage: `references/single-building-coverage.md`
- Knowledge routing: `references/knowledge-map.md`
- Check-matrix construction: `references/checklist-rules.md`
- AI-completed project facts and routing: `references/project-profile.md`
- Executable atomic-rule schema: `references/review-rule-schema.md`
- Candidate filtering: `references/opinion-rules.md`
- Screenshot evidence: `references/screenshot-protocol.md`
- Word structure: `references/report-format.md`
- Failure patterns before verification: `references/gotchas.md`
- Confirmed single-building retrospective: `references/single-building-retrospective.md`

## Mandatory Gates

- An `ai_ready` issue must link drawing inventory, project fact, review judgment, and screenshot evidence when visual proof is needed. Technical requirements also require an applicable local B source; narrowly defined design-depth issues may use the controlled `citation_mode=none` path.
- Never prefill `符合`, `reviewed`, validation `通过`, `ai_ready`, or `AI初审完成`. New checks start `unreviewed/需核验`; scripts may expand required work but may not close it. The AI may set completion values only after actually performing the corresponding checks.
- A v1.6 technical `符合` or `不符合` requires a rule ID resolving to an active B-source rule, sheet-specific facts, structured applicability decisions, comparison record, required calculation record, and any rule-required graphic evidence chain. Design-depth rules cannot carry technical citations.
- A v1.6 report requires an AI-completed project profile and specialty route, three completed discovery tracks, all triggered atomic rules resolved, all graphic and applicability gates closed, all four knowledge layers recorded, a current integrity snapshot, and a current passing completion audit. It must not contain human names, legacy human confirmation fields, an independent-review ledger, or artificial review claims.
- Never cite a standard from memory. Missing, stale, ambiguous, or changed sources stay `needs_review` or `需核验`; do not use `citation_mode=none` to bypass a missing technical basis.
- Do not generate Word while any identifiable sheet is unclassified or has `review_status=needs_review`.
- A v1.3+ `reviewed` sheet must close every required sheet-family topic with matching atomic checks, evidence classes, drawing references, and facts. v1.4+ additionally requires every profile-triggered executable rule for that sheet; v1.6 adds AI-completed structured applicability and graphic-evidence gates without an independent-human-review gate. A broad check, an unrelated number, a check that does not reference the sheet, or a presence-only statement cannot close coverage.
- Run a project-identity and scope-consistency pass across design notes, specialties, schedules, and title blocks. Treat wrong project names, functions, basement/elevator statements, and stale design bases as technical design-depth candidates rather than packaging noise.
- Complete function-triggered packets before Word generation. Dormitory, food-service, school, parking, elevator, photovoltaic/solar, wet-room, roof, and wall-detail facts must activate their corresponding topics; unresolved topics block the report.
- Discover and filter three tracks separately: mandatory noncompliance, design-depth/internal contradiction, and supported optimization advice. Do not let conservative filtering silently discard an unresolved high-risk item; retain it as `needs_review` until the evidence chain closes.
- A check whose applicability is still `需判断` or whose conclusion is `需核验` cannot support an `ai_ready` issue. Conditional wording such as “如适用”“需核验”“需确认规范适用时间” may remain in a technically supported opinion, but workflow statuses never appear in Word.
- Do not verify graphical direction, symbol meaning, missing-expression, or cross-sheet claims until required evidence roles are present. Raster-limited evidence alone cannot close a claim; ambiguity-sensitive claims must record and eliminate at least one plausible alternative interpretation.
- Never copy a case or high-frequency issue into the report without matching project facts and recording differences.
- When maintaining the executable catalog from high-frequency or case materials, use those materials only for discovery and priority. Keep the complete source mapping outside the public package, resolve every formal technical rule to an active local B source, and run `scripts/audit_high_frequency_rule_sources.py --mapping <private-map.json> --catalog generated/review-rules.json` before synchronization.
- Merge duplicates, reject weak items, retain evidence-insufficient candidates in process ledgers, and include only `ai_ready` issues in a v1.6 Word report.
- Scripts validate traceability and consistency; they do not prove professional judgment is technically correct.
- Never mark visual QA passed before opening and checking every rendered page.
- Report evidence screenshots with red boxes must follow `references/screenshot-protocol.md`: use the combined red-box envelope, keep an already locatable crop unchanged when its width and height are each at least 2 times the envelope, and expand only deficient axes to about 2.5 times. Preserve the red box's source coordinates and size, and confirm the locating context during rendered-page visual QA.
- Do not add a cover or non-template report chapters. The title is the only visible AI-stage marker. Follow `references/report-format.md` exactly, including empty-section wording and the formal 12-type note.
- Run every AutoCAD or `accoreconsole` command through `scripts/run_cad_script_safely.py --timeout <seconds> -- <command...>`. Never invoke CAD directly when a generated script can change `FILEDIA` or `CMDDIA`; the wrapper must remain alive until the CAD child exits so its `finally` restoration runs.
- Any `.scr` that sets `FILEDIA` or `CMDDIA` to `0` must restore both to `1` before every `QUIT` and before script end. The safe runner must reject a script that fails this preflight gate.

## Defaults

- Set `BUILDING_REVIEW_KNOWLEDGE_BASE` or pass `--knowledge-base <path>` when building a private local index. This public package does not include standards, policies, cases, or project files.
- Set `BUILDING_REVIEW_INDEX_DIR` when building the index and `BUILDING_REVIEW_INDEX` when searching or snapshotting it; otherwise the scripts use `./building-review-index` under the current working directory.
- Set `BUILDING_REVIEW_PROJECT_ROOT` or pass `--root <path>` for workspace creation; otherwise the script uses `./building-review-projects` under the current working directory.
- Keep raw knowledge files and real project source files unchanged. Store indexes, ledgers, snapshots, screenshots, and drafts outside the raw knowledge base.
- Prefer local sources. Browse only when local sources cannot resolve a current standard or policy question, or the user explicitly asks for current official status.
- New reviews use schema v1.7 and directly deliver a formal-format AI initial-review DOCX. v1.1-v1.6 workspaces remain readable for compatibility, but new workspaces never wait for or fabricate human confirmation, review, or adjudication.
