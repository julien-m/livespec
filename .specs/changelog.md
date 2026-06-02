# Changelog

> Global changelog for LiveSpec. One entry per feature/bugfix/refactor.
> Per-feature details live in `.specs/features/<feature-slug>/changelog.md`.
>
> Last updated: 2026-06-02

---

## 2026-06-02 — [Feature 055]: Implemented Spec Doctor Project Health — `livespec doctor`, `$spec-doctor` docs, stale mapping/test/runner/hook/lifecycle/visual audits, safe cleanup planning, JSON output, strict mode, and focused tests.

## 2026-06-01 — [Feature 056]: Spec created: Executable User Journeys — canonical YAML user journeys, ahead-of-time compilation to native test frameworks, distinct functional regression reporting, and Spec Doctor stale-artifact checks.

## 2026-06-01 — [Feature 055]: Spec created: Spec Doctor Project Health — project-level doctor command for stale mappings, missing tests, runner inclusion, hooks, lifecycle drift, visual evidence, and future journey health.

## 2026-06-01 — [Feature 054]: Implemented metadata-aware migration planning and Migration 17 Penflow backfill reporting; `/spec-migrate` now documents planner-first execution, restore-point invalidation, and safe non-generation when runtime UI is unavailable.

## 2026-06-01 — [Feature 053]: Implemented goal task convention replay; every rendered goal task records required conventions and `livespec goal prove` rejects evidence missing convention usage.

## 2026-05-26 — [Feature 051 Fix]: LiveSpec now treats root `penflow/ui.pen` as the only allowed `.pen`, imports explicit Brainstorm `penflow/` sources, blocks duplicate `.pen` files, and removes `.specs/design/ui.pen` requirements from active command/docs paths.

## 2026-05-26 — [Feature 051 Check]: Single `penflow/ui.pen` contract verified against real Brainstorm project `/Users/julienm/projects/project-brainstorm/projects/orch-single-uipen-20260526T152606Z`; virgin LiveSpec import produced only `penflow/ui.pen`.

## 2026-05-23 — [Feature 052 Fix]: Visual goal proof now requires a deterministic `visual_evidence_receipt_path`; `visual-gate certify` writes verified PNG hash/diff receipts and visual commands validate receipts instead of worker-declared diffs.

## 2026-05-23 — [Feature 004 Fix]: Visual gate now enforces legacy `baseline.manifest.yml` mockup evidence, supports `mockup_path` for runtime-state screenshots, and blocks missing/stale design mockups before PASS.

## 2026-05-23 — [Feature 052 Fix]: Internal `/spec-*` subagent invocations now propagate the current LiveSpec project root/cwd and command audit rejects missing workdir guards.

## 2026-05-23 — [Feature 052 Fix]: Goal rendering now ignores documentary `/spec-*` examples/recovery hints, skips Markdown checkboxes inside `Execution Tasks`, exposes top-level `worker_may_mark_tasks_complete=false`, and adds machine Goal Lock tasks to `/spec-status` + `/spec-explain`.

## 2026-05-23 — [Feature 052 Fix]: Deterministic command goals now write `contract.json` + `state.json`, require `livespec goal prove/status`, and reject visual design-fidelity completion when mockup/baseline/runtime PNG proof is missing.

## 2026-05-21 — [Feature 052] Fix: 4/4 anchor gaps closed — FR-011/012/014/015 `@spec` annotations added (100% FR verified)

## 2026-05-21 — [Feature 052] Check: 73% FR verified (11/15), 100% AC verified (13/13), 4 FR with anchor gaps only — code complete, tests 12/12

## 2026-05-21 — [Feature 052 Fix]: Deterministic command goals now embed applicable `.conventions/index.md` domains, including code conventions by default and design conventions for UI/mockup/visual tasks.

## 2026-05-21 — [Feature 052]: Implemented: Deterministic Command Goal Contracts — `livespec goal render/verify`, canonical hashable goal payloads, expectation-backed completion gates, and shared anti-drift goal protocol.

## 2026-05-21 — [Feature 051 Bugfix]: Penflow actual-tree absence now reports `ABSENT` for from-scratch/non-UI runs and `BLOCKED` when UI runtime comparison requires `actual-ui-tree.json`; command expectations now include Penflow verdict outputs.

## 2026-05-21 — [Feature 051]: Implemented: Integrate Penflow as LiveSpec primary UI contract — root `penflow/` workspace helper + CLI, command docs for init/specify/plan/implement/test/check, Penflow contract gate workflow, and screenshot regression gates preserved.

## 2026-05-20 — [Bugfix]: Agent-sync project rule sync now links individual LiveSpec rule files before `cc-hub rule build`, so newly initialized projects receive usable `.agent-sync/rules/*.md` and provider rule outputs alongside the 20 `spec-*` skills and 4 `livespec-*` agents.

## 2026-05-20 — [Bugfix]: Downstream LiveSpec links now install under `.agent-sync.local/` instead of project `.agent-sync/`, preserving `.agent-sync/` for global/shared project assets while provider outputs still resolve through `cc-hub`.

## 2026-05-18 — [Bugfix]: Completed command-name normalization leftovers — active docs, agent-sync skills/agents, CLI help, state-file schema, and project state files now use canonical `spec-*`; state-file migration now rewrites legacy dotted `owner_command` values and validates them; agent-sync migration now ignores provider outputs and removes relative legacy command symlinks.

## 2026-05-18 — [Bugfix]: Global bootstrap now installs only `spec-init` and `spec-migrate` — `scripts/install.sh` no longer links LiveSpec rules globally; project rules remain synced by `/spec-init` through `.agent-sync` and `cc-hub`.

## 2026-05-18 — [Feature 050]: Implemented: Agent Sync Migration — moved commands, expectations, agents, and routing rules to `.agent-sync`; init/install/migration now sync through `cc-hub`; legacy `commands/`, `agents/`, and tracked `.claude/rules/livespec-*` sources removed; Migration 16 added; command-audit reports 20/20 commands at score 5.

## 2026-05-18 — [Feature 049]: Implemented: Command Naming Normalization — `/spec-*` is now canonical across registry, docs, local/bootstrap links, hooks, integrations, command-audit, verify-output, and run finalization; dotted `/spec.*` links remain as legacy aliases; Migration 15 added; full suite 1506 passed, 32 skipped.

## 2026-05-18 — [Feature 048]: Implemented: Command Validation Hardening — added canonical command registry, `livespec command-audit`, strengthened expectations guard checks, `livespec run finalize`, deterministic `status`/`play-coverage`/`conventions refresh` backends, audit-backed coherence script, Migration 14, and tests; command-audit reports 20/20 commands at score 5.

## 2026-05-18 — [Feature 049]: Spec created: Command Naming Normalization — canonical slash commands move from dotted `/spec.*` names to hyphenated `/spec-*` names after Feature 048; dotted names remain backward-compatible aliases during migration; registry, docs, hooks, verify-output, and migration tooling must agree on canonical names.

## 2026-05-18 — [Feature 048]: Spec created: Command Validation Hardening — plan created for 5/5 command validation: canonical command registry, deterministic command audit, mandatory run finalization for state-changing commands, fresh coherence checks, script-backed validation for status/play-coverage/refresh-conventions, and migration v14.

## 2026-05-17 -- [Feature 047] Implemented: Design Alignment Gate — global `ui.pen` → runtime alignment protocol, support-quality contract, manifest schema, reusable Python comparator, `livespec design-alignment compare`, `/spec-test --visual` Phase 4.5.0 integration, +8 regression tests.

## 2026-05-17 -- [Feature 046] Implemented: Visual Implementation Gate — `/spec-implement` now requires `/spec-test <feature> --auto --visual` before finalizing UI features; visual tooling failures and `--no-visual` keep status `In Progress`; `/spec-test` emits `Visual Gate Verdict: PASS | FAIL | BLOCKED`; +5 regression tests.

## 2026-05-13 -- [Feature 043] Spec created: `/spec.sync-brainstorm` — Living Bridge to Brainstorm — 5 stories, 17 AC, 18 FR (new slash-command detecting stale/orphaned/manual flows; Mode A re-pull for flows with `--apply` + per-file confirmation; Mode B inviolable for derived feature AC/FR; `--prune-orphaned` with explicit confirmation; integrates 4 new gap categories into `/spec-check`)
## 2026-05-13 -- [Feature 042] Spec created: `/spec-specify` Derives from Imported Brainstorm Flows — 3 stories, 13 AC, 13 FR (transcribes Mermaid + AC + FR from `.specs/flows/<slug>.md` produced by Feature 041; Mode B locking; classic-fallback when no flow matches)
## 2026-05-13 -- [Feature 041] Spec created: Brainstorm Flow & Screen Specs Ingestion — 3 stories, 14 AC, 12 FR (extends `spec.init` Step 3.6 to ingest `.brainstorm/specs/{flows,screens}/*.md` produced by brainstorm `specify-flows`)
## 2026-05-13 -- [Migration v13] Backfill command-expectations wiring — re-link `.claude/commands/` (drops orphan `spec.*.expectations.md` symlinks left by pre-fix `link-local.sh`, adds `/spec-verify-output`), install `last_reviewed` pre-commit hook, append `.specs/.runs/` and `.specs/.previews/` to `.gitignore`; `install-hooks.sh` accepts `<project> <livespec>` args; `/spec-init` now wires the hook automatically (features 039, 040)
## 2026-05-12 -- [Feature 040] Implemented: Rich Expectations Format & Verify Preview — Section 13 (Demo Session) mandatory across the 20 builtin expectations files, new `livespec verify-output --preview [--save]` mode that resolves placeholders from `.specs/stacks/_default.md`, `.specs/features/`, `.specs/design/screens/`, `.conventions/manifest.yaml`; +15 tests, 0 regressions (depends on feature 039)
## 2026-05-12 -- [Feature 039] Implemented: Command Expectations & /spec-verify-output — 20 builtin expectations files, RunArtifact JSON schema, verify-output CLI + slash-command, pre-commit last_reviewed hook, override resolver, 4-state outcome classifier (no-short-circuit invariant)
## 2026-05-08 -- [Feature 037] Implemented: Test Multi-Runner Integration — runner-aware Phase 4.5 dispatcher, multi-target Xcode pbxproj parsing, --visual flag documented; +32 Python tests +5 JS tests, 0 regressions
## 2026-05-08 -- [Feature 037] Plan created: Test Multi-Runner Integration — 17 implementation steps, 4 diagrams (sequence + flow + state + ER), 15+ files
## 2026-05-08 -- [Feature 037] Spec created: Test Multi-Runner Integration — 5 stories, 15 AC, 15 FR
## 2026-05-07 -- [Feature 036] Test: 92% AC covered (11/12), 906 tests passing (22 JS + 884 Python), 0 generated
## 2026-05-07 -- [Feature 036] Plan created: Multi-Surface Detection and Migration — 5 implementation steps, 2 diagrams (sequence + state), 4 files
## 2026-05-07 -- [Feature 036] Spec created: Multi-Surface Detection and Migration — 4 stories, 12 AC, 8 FR
## 2026-05-07 -- [Feature 033] In progress: Smart Test Selection — core selector module + 22 unit tests; selector logic landed, hook/CLI/migration work still pending
## 2026-05-07 -- [Feature 028] In progress: UI Runner Web (Playwright Refactor) — added web.yaml manifest and Playwright handler scaffold
## 2026-05-07 -- [Feature 026] Implemented: Conventions Propagation by Stack — 3 stories, 8 AC, 7 FR; 43 new tests pass (917 total)
## 2026-05-07 -- [Feature 025] Implemented: Mutation Testing On-Demand — 2 stories, 7 AC, 6 FR; 15 new tests pass (874 total)
## 2026-05-07 -- [Feature 019] Implemented: Driver Swift — 4 stories, 10 AC, 6 FR; 31 new tests pass (723 total)
## 2026-05-06 -- [Feature 016] Implemented: Cross-Language Test Driver Architecture — 5 stories, 15 AC, 8 FR; 35 tests pass
## 2026-05-06 -- [Feature 034] Spec created: Preflight Auto-Install & Init via /spec-preflight --fix — 5 stories, 14 AC, 11 FR
## 2026-05-06 -- [Feature 033] Spec created: Smart Test Selection — 4 stories, 12 AC, 10 FR
## 2026-05-06 -- [Feature 032] Spec created: Pre-commit / Pre-push Test Hooks — 5 stories, 13 AC, 10 FR
## 2026-05-06 -- [Feature 031] Spec created: UI Runner Android (Maestro) — 3 stories, 13 AC, 8 FR
## 2026-05-06 -- [Feature 030] Spec created: UI Runner iOS / watchOS (XCUITest) — 4 stories, 14 AC, 9 FR
## 2026-05-06 -- [Feature 029] Spec created: UI Runner Tauri — 3 stories, 12 AC, 7 FR
## 2026-05-06 -- [Feature 028] Spec created: UI Runner Web (Playwright Refactor) — 2 stories, 8 AC, 5 FR
## 2026-05-06 -- [Feature 027] Spec created: UI Runner Architecture — 4 stories, 12 AC, 8 FR
## 2026-05-06 -- [Features 013, 014, 015] Fix: implementation.md created (post-merge bookkeeping for Chantiers 4/2/3)
## 2026-05-06 -- [Feature 026] Spec created: Conventions Propagation by Stack — 3 stories, 8 AC, 7 FR
## 2026-05-06 -- [Feature 025] Spec created: Mutation Testing On-Demand — 2 stories, 7 AC, 6 FR
## 2026-05-06 -- [Feature 024] Spec created: Patch Coverage Local Computation — 2 stories, 9 AC, 6 FR
## 2026-05-06 -- [Feature 023] Spec created: Driver Custom Scaffolding & Graceful Degradation — 3 stories, 10 AC, 6 FR
## 2026-05-06 -- [Feature 022] Spec created: Driver JVM (Java + Kotlin) — 4 stories, 11 AC, 6 FR
## 2026-05-06 -- [Feature 021] Spec created: Driver Rust — 4 stories, 10 AC, 5 FR
## 2026-05-06 -- [Feature 020] Spec created: Driver Go — 4 stories, 9 AC, 5 FR
## 2026-05-06 -- [Feature 019] Spec created: Driver Swift — 4 stories, 10 AC, 6 FR
## 2026-05-06 -- [Feature 018] Spec created: Driver TypeScript/JavaScript — 4 stories, 12 AC, 6 FR
## 2026-05-06 -- [Feature 017] Spec created: Driver Python — 4 stories, 12 AC, 7 FR
## 2026-05-06 -- [Feature 016] Spec created: Cross-Language Test Driver Architecture — 5 stories, 15 AC, 8 FR

## 2026-05-04 -- Fix: Feature 010 monorepo path resolution

[Feature 010] Fix: 2/2 gaps closed — generated test templates now resolve `MOCKUP_DIR` from `import.meta.url` (parent walker for `.specs/`) instead of `process.cwd()`, and `detectRoutesDir()` consults surface-aware paths from `surfaces.yaml` before falling back to repo-root scan. Unblocks Playwright runs from sub-apps in monorepos.

---

## 2026-05-03 -- Spec: Feature 015 Global Write Locks & Atomic NNN Reservation

[Feature 015] Spec created: Global Write Locks & Atomic NNN Reservation — 5 stories, 10 AC, 10 FR. Implements file locks on shared .specs files + post-write re-read assertions + atomic NNN reservation for spec.specify to prevent race conditions and silent data corruption.

---

## 2026-05-03 -- Spec: Feature 014 Supervisor↔Subagent Return Contracts

[Feature 014] Spec created: Supervisor↔Subagent Return Contracts — 5 stories, 10 AC, 10 FR. Defines typed JSON schemas (PHASE_RESULT, SHIP_RESULT, Superpowers return) + regex-anchored parsers + active filesystem verification in Activation Contracts to harden supervisor↔subagent communication.

---

## 2026-05-03 -- Spec: Feature 013 State Model & Identity Resolution (Chantier 4)

[Feature 013] Spec created: State Model & Identity Resolution — 5 stories, 10 AC, 10 FR. Addresses the most critical defects from AUDIT.md: literal `NNN-feature-name` propagation in `/spec-feature`, log path incoherence, internal contradictions in `/spec-implement`, undefined `--resume` semantics on `Blocked`, absence of shared state-file frontmatter schema.

---

## 2026-04-18 -- Fix: Feature 011 generator template quality (3 issues)

[Feature 011] Fix: 3 template quality issues in `scripts/migrate-visual-tests.js` — (1) mockup comparison no longer creates wrong auto-baseline (now documents as reference); (2) header selector extracted from existing project tests instead of generic fallback; (3) empty-state test uses detected `mockEmpty*` fixture from `fixtures.ts` instead of hardcoded inline routes. 11/11 tests pass.

---

## 2026-04-18 -- Fix: Feature 010 generated test template upgraded

[Feature 010] Fix: Playwright API bug fixed (`toMatchSnapshot` → Playwright `toHaveScreenshot` assertions), generated E2E tests now exhaustive (4 state-based tests: full data, empty state, header, mobile), fixtures detection auto-imports `mockAuthenticatedAPIs`/`mockEmptyDashboardAPIs`, bad route inference corrected for 003/006/007.

---

## 2026-04-18 -- Fix: Feature 010 migration tool architecture corrected

[Feature 010] Fix: Migration tool now uses adaptive detection — `frontend/tests/e2e/` mode targets correct dirs (frontend/tests/e2e/, .specs/design/screens/ Pencil mockups, frontend/playwright.config.ts); legacy fallback unchanged. Legacy config cleanup preserved. 205/205 meta-tests pass.

---

## 2026-04-17 -- Fix: Feature 010 migration tool gaps closed

[Feature 010] Fix: 4/4 gaps closed — `playwright.visual.config.ts` auto-generated on `--generate`, test templates improved (route inference, page screenshots, fullpage+responsive tests), completion report printed. 11 integration tests still pass.

---

## 2026-04-17 -- Test: Feature 011 validated

[Feature 011] Test: 11 feature integration tests passing; command-layer guards reviewed in `commands/spec-migrate.md`; AC coverage report updated.

---

## 2026-04-17 -- Feature: Feature 011 implemented

[Feature 011] Implemented: Visual Migrate Integration -- sentinel output added to migrate-visual-tests.js, visual scaffolding step added to commands/spec-migrate.md (unconditional, silent, graceful degradation), 11 integration tests (level_3a), fixture project with 4 features, and baseline placeholders for generated visual scaffolds.

---

## 2026-04-17 -- Plan: Feature 011 planned (regenerated)

[Feature 011] Plan regenerated: Visual Migrate Integration — 4 implementation steps (commands/spec-migrate.md + migrate-visual-tests.js sentinel output + integration test fixture + tests/integration/test_migrate_visual.py), 1 sequence diagram, 1 state diagram, no API contracts. Visual scaffolding invoked unconditionally from command layer (including "already up to date" path), not from migrate.sh. Safe subprocess capture via set +e/set -e. Tests at tests/integration/test_migrate_visual.py for level_3a discovery.

---

## 2026-04-17 -- Spec: Feature 011 created

[Feature 011] Spec created: Visual Migrate Integration — 4 stories, 12 AC, 11 FR. Automatic visual test scaffolding during spec.migrate: silent generation of Playwright test files + baseline directories for all UI features, idempotent, with post-migration summary and graceful degradation.

---

## 2026-04-17 -- Implement: Feature 010 implemented

[Feature 010] Implemented: Visual Testing Complete — downstream Playwright scaffolding added across templates, scripts, documentation, workflow artifacts, and baseline placeholders. Python regression suite remains green at 464 passed. No Python modules modified.

---

## 2026-04-17 -- Plan: Feature 010 planned

[Feature 010] Plan created: Visual Testing Complete — 8 steps (Step 0–7), 4 TS test templates, 3 Node.js scripts, 8 Markdown guides, 1 CI workflow, 1 meta-test suite. Artifacts are framework tooling for downstream projects; no Python modules modified; meta-tests validate artifact existence only (constitution "No Visual Testing" preserved).

---

## 2026-04-17 -- Spec: Feature 010 created

[Feature 010] Spec created: Visual Testing Complete — 7 stories, 30 AC, 25 FR. Framework tooling and templates for downstream projects: mockup-driven baselines, full-page layout validation, responsive (3 viewports), cross-browser (3 engines), animation keyframes, migration tool, CI/CD visual diff PR workflow.

---

## 2026-04-17 -- Implement: Feature 005.2 implemented

[Feature 005.2] Implemented: Taxonomy Complete Expansion -- 17 new traits (22 total), 3 new transversal patterns (6 total), taxonomy v2.0.0. 478 tests passing (18 new detection tests). 100% classification on 15-component crash test. Parser required no code changes (additive schema).

---

## 2026-04-17 -- Plan: Feature 005.2 planned

[Feature 005.2] Plan created: Taxonomy Complete Expansion -- 6 implementation steps, 15 new traits + 3 transversal patterns + 15 detection tests + crash test + parser validation + docs. All 12 FR covered.

---

## 2026-04-17 -- Spec: Feature 005.2 created

[Feature 005.2] Spec created: Taxonomy Complete Expansion — 5 stories, 20 AC, 12 FR. Adds 15 new behavioral traits across 5 categories, 3 new transversal patterns, taxonomy v2.0.0 targeting >95% coverage.

---

## 2026-04-17 -- Fix: Feature 005.1 gaps closed

[Feature 005.1] Fix: 4/4 gaps closed (100% → 100% alignment) — crash test report created, AC-012/013/014/015 validated

---

## 2026-04-17 -- Test: Feature 009 spec.md corrected + full suite revalidated

[Feature 009] Test (run 2): 3/3 Python-testable ACs (100%), 446 unit tests passing, spec.md status Draft → Implemented, --regenerate-missing scan: EC-004 (0 features missing tests)

---

## 2026-04-17 -- Test: Feature 009 test validation

[Feature 009] Test: 3/3 Python-testable ACs covered (100%), 441 unit tests passing, 0 tests generated (EC-004: nothing to regenerate)

---

## 2026-04-17 -- Plan: Feature 009 planned

[Feature 009] Plan created: Visual State Baselines — 6 implementation steps, 2 diagrams (ER + state), M-size scope

---

## 2026-04-17 -- Spec: Feature 009 created

[Feature 009] Spec created: Visual State Baselines — 5 stories, 15 AC, 11 FR

---

## 2026-04-16 -- Feature: Feature 008 implemented

[Feature 008] Implemented: Feature Seed — 2 files modified (commands/spec-specify.md, spec-system.md), 7 FR, 11 AC all satisfied

---

## 2026-04-16 -- Plan: Feature 008 planned

[Feature 008] Plan created: Feature Seed — 5 implementation steps, 3 diagrams

---

## 2026-04-16 -- Spec: Feature 008 created

[Feature 008] Spec created: Feature Seed — 5 stories, 11 AC, 7 FR

---

## 2026-04-15 -- Plan: Feature 007 planned

[Feature 007] Plan created: Structured Signal Extraction — 3 implementation steps, 1 diagram

---

## 2026-04-15 -- Spec: Feature 007 regenerated (9 review findings addressed)

[Feature 007] Spec regenerated: Structured Signal Extraction — 4 stories, 11 AC, 7 FR. Addressed F-001 through F-009: added AC-009/AC-010/AC-011, fixed drawer scenario, replaced spec_specify() with detect_traits() contract tests, added Step 5.7 refactoring map.

---

## 2026-04-15 -- Spec: Feature 007 created

[Feature 007] Spec created: Structured Signal Extraction — 4 stories, 8 AC, 7 FR

---

## 2026-04-15 -- Plan: Feature 006 planned

[Feature 006] Plan created: Taxonomy Testing Infrastructure — 3 implementation steps, 2 diagrams

---

## 2026-04-15 -- Spec: Feature 006 created

[Feature 006] Spec created: Taxonomy Testing Infrastructure — 4 stories, 15 AC, 8 FR

---

## 2026-04-14 -- Check: Feature 005 checked

[Feature 005] Check: 100% verified (9/9 FR, 13/13 AC) — Healthy. All plan-review mandatory findings satisfied.

---

## 2026-04-14 -- Plan: Feature 005 plan created

[Feature 005] Plan created: UI Behavioral Testing — 5 implementation steps, 4 diagrams

---

## 2026-04-14 -- Spec: Feature 005 created

[Feature 005] Spec created: UI Behavioral Testing — 5 stories, 13 AC, 9 FR

---

## 2026-04-14 -- Feature: Feature 004 implemented

[Feature 004] Implemented: Visual Testing Governance — 4 new files created, 2 modified, 41 tests added, 406 total pass

---

## 2026-04-14 -- Plan: Feature 004 planned

[Feature 004] Plan created: Visual Testing Governance — 7 implementation steps, 4 diagrams

---

## 2026-04-14 -- Spec: Feature 004 created

[Feature 004] Spec created: Visual Testing Governance — 4 stories, 12 AC, 8 FR

---

## 2026-04-14 -- Feature: Feature 003 implemented

[Feature 003] Implemented: Visual Testing Fidelity — 6 files modified, 2 files created, 14/14 AC implemented

---

## 2026-04-14 -- Plan: Feature 003 planned

[Feature 003] Plan created: Visual Testing Fidelity — 8 implementation steps, 3 diagrams, 2 new files + 5 modified

---

## 2026-04-14 -- Spec: Feature 003 created

[Feature 003] Spec created: Visual Testing Fidelity — 6 stories, 14 AC, 10 FR

---

## 2026-04-13 -- Fix: Feature 002 anchors fixed

[Feature 002] Fix: Added 3 missing @spec anchors (FR-006, FR-007, FR-009), normalized all to single-line convention — 100% anchor alignment (9/9)

---

## 2026-04-13 -- Check: Feature 002 checked

[Feature 002] Check: 100% functional (9/9 FR, 10/10 AC), 67% anchors (6/9) — 3 missing @spec anchors

---

## 2026-04-13 -- Plan: Feature 002 planned

[Feature 002] Plan created: Layer 3 CLI Surface -- 7 implementation steps, 3 diagrams, 1 new file + 2 modified + 2 test files

---

## 2026-04-13 -- Spec: Feature 002 created

[Feature 002] Spec created: Layer 3 CLI Surface -- 4 stories, 10 AC, 9 FR

---

## 2026-04-13 -- Check: Feature 001 aligned

[Feature 001] Check: 100% verified (11/11 FR, 14/14 AC) — ✅ Healthy

---

## 2026-04-13 -- Feature: Feature 001 implemented

[Feature 001] Implemented: Auto LLM Review -- 4 new files, 3 modified, 36 new tests, 331 total pass

---

## 2026-04-13 -- Plan: Feature 001 planned

[Feature 001] Plan created: Auto LLM Review -- 6 implementation steps, 3 diagrams

---

## 2026-04-13 -- Spec: Feature 001 created

[Feature 001] Spec created: Auto LLM Review -- 4 stories, 14 AC, 11 FR

---

## 2026-04-13 -- Setup: LiveSpec initialized via spec.init --from-code

- **Type:** Setup
- **Scope:** Project-wide
- **Description:** LiveSpec initialized on existing codebase. Reverse-engineered project profile, stack (Python/Typer/Pydantic/pytest/ruff/pyright), 3 ADRs, testing strategy, and roadmap from codebase scan.
- **Author:** spec.init --from-code

---
