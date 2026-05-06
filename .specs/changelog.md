# Changelog

> Global changelog for LiveSpec. One entry per feature/bugfix/refactor.
> Per-feature details live in `.specs/features/<feature-slug>/changelog.md`.
>
> Last updated: 2026-05-06

---

## 2026-05-06 -- [Feature 016] Implemented: Cross-Language Test Driver Architecture — 5 stories, 15 AC, 8 FR; 35 tests pass
## 2026-05-06 -- [Feature 034] Spec created: Preflight Auto-Install & Init via /spec.preflight --fix — 5 stories, 14 AC, 11 FR
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

[Feature 013] Spec created: State Model & Identity Resolution — 5 stories, 10 AC, 10 FR. Addresses the most critical defects from AUDIT.md: literal `NNN-feature-name` propagation in `/spec.feature`, log path incoherence, internal contradictions in `/spec.implement`, undefined `--resume` semantics on `Blocked`, absence of shared state-file frontmatter schema.

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

[Feature 011] Test: 11 feature integration tests passing; command-layer guards reviewed in `commands/migrate.md`; AC coverage report updated.

---

## 2026-04-17 -- Feature: Feature 011 implemented

[Feature 011] Implemented: Visual Migrate Integration -- sentinel output added to migrate-visual-tests.js, visual scaffolding step added to commands/migrate.md (unconditional, silent, graceful degradation), 11 integration tests (level_3a), fixture project with 4 features, and baseline placeholders for generated visual scaffolds.

---

## 2026-04-17 -- Plan: Feature 011 planned (regenerated)

[Feature 011] Plan regenerated: Visual Migrate Integration — 4 implementation steps (commands/migrate.md + migrate-visual-tests.js sentinel output + integration test fixture + tests/integration/test_migrate_visual.py), 1 sequence diagram, 1 state diagram, no API contracts. Visual scaffolding invoked unconditionally from command layer (including "already up to date" path), not from migrate.sh. Safe subprocess capture via set +e/set -e. Tests at tests/integration/test_migrate_visual.py for level_3a discovery.

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

[Feature 008] Implemented: Feature Seed — 2 files modified (commands/specify.md, spec-system.md), 7 FR, 11 AC all satisfied

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
