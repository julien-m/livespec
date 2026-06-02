# .specs — LiveSpec

> Specification registry for LiveSpec. All artifacts produced by LiveSpec are indexed here.
>
> Last updated: 2026-06-01


---

## System Files

| Document | Description |
|---|---|
| [spec-system.md](spec-system.md) | Universal spec rules (read first) |
| [constitution.md](constitution.md) | Architecture principles |
| [project.md](project.md) | Project profile (vision, users, constraints) |
| [stacks/_default.md](stacks/_default.md) | Current tech stack |
| [testing/strategy.md](testing/strategy.md) | Testing strategy |
| [changelog.md](changelog.md) | Global changelog |
| [roadmap.md](roadmap.md) | Feature backlog (Implemented / MVP / Post-MVP / Future) |

---

## Design

| Document | Description |
|---|---|
| [design/](design/) | UI mockups and screen references (none — CLI tool) |
| [design/changelog.md](design/changelog.md) | Design change history |

---

## Features

<!-- readme:features:start -->
| # | Feature | Status | Created | Updated | Spec |
|---|---|---|---|---|---|
| 001 | Auto LLM Review | Implemented | 2026-04-13 | 2026-04-13 | [spec](features/001-auto-llm-review/spec.md) |
| 002 | Layer 3 CLI Surface | Implemented | 2026-04-13 | 2026-04-14 | [spec](features/002-layer-3-cli-surface/spec.md) |
| 003 | Visual Testing Fidelity | Implemented | 2026-04-14 | 2026-04-14 | [spec](features/003-visual-testing-fidelity/spec.md) |
| 004 | Visual Testing Governance | Implemented | 2026-04-14 | 2026-04-14 | [spec](features/004-visual-testing-governance/spec.md) |
| 005 | UI Behavioral Testing | Implemented | 2026-04-14 | 2026-04-14 | [spec](features/005-ui-behavioral-testing/spec.md) |
| 006 | Taxonomy Testing Infrastructure | Implemented | 2026-04-15 | 2026-04-15 | [spec](features/006-taxonomy-testing-infra/spec.md) |
| 007 | Structured Signal Extraction | Implemented | 2026-04-15 | 2026-04-17 | [spec](features/007-structured-signal-extraction/spec.md) |
| 008 | Feature Seed | Implemented | 2026-04-16 | 2026-04-16 | [spec](features/008-feature-seed/spec.md) |
| 009 | Visual State Baselines | Implemented | 2026-04-17 | 2026-04-17 | [spec](features/009-visual-state-baselines/spec.md) |
| 005.1 | Behavioral TDD Audit | Implemented | 2026-04-17 | 2026-04-17 | [spec](features/005.1-behavioral-tdd-audit/spec.md) |
| 005.2 | Taxonomy Complete Expansion | Implemented | 2026-04-17 | 2026-04-17 | [spec](features/005.2-taxonomy-complete-expansion/spec.md) |
| 010 | Visual Testing Complete | Implemented | 2026-04-17 | 2026-04-17 | [spec](features/010-visual-testing-complete/spec.md) |
| 011 | Visual Migrate Integration | Implemented | 2026-04-17 | 2026-04-17 | [spec](features/011-visual-migrate-integration/spec.md) |
| 013 | State Model & Identity Resolution | Implemented | 2026-05-03 | 2026-05-04 | [spec](features/013-state-model-identity-resolution/spec.md) |
| 014 | Supervisor↔Subagent Return Contracts | Implemented | 2026-05-03 | 2026-05-04 | [spec](features/014-supervisor-contracts/spec.md) |
| 015 | Global Write Locks & Atomic NNN Reservation | Implemented | 2026-05-03 | 2026-05-04 | [spec](features/015-global-write-locks/spec.md) |
| 016 | Cross-Language Test Driver Architecture | Implemented | 2026-05-06 | 2026-05-06 | [spec](features/016-cross-language-test-driver-architecture/spec.md) |
| 017 | Driver Python | Implemented | 2026-05-06 | 2026-05-06 | [spec](features/017-driver-python/spec.md) |
| 018 | Driver TypeScript/JavaScript | Implemented | 2026-05-06 | 2026-05-06 | [spec](features/018-driver-typescript-javascript/spec.md) |
| 019 | Driver Swift | Implemented | 2026-05-06 | 2026-05-07 | [spec](features/019-driver-swift/spec.md) |
| 020 | Driver Go | Implemented | 2026-05-06 | 2026-05-06 | [spec](features/020-driver-go/spec.md) |
| 021 | Driver Rust | Implemented | 2026-05-06 | 2026-05-06 | [spec](features/021-driver-rust/spec.md) |
| 022 | Driver JVM (Java + Kotlin) | Implemented | 2026-05-06 | 2026-05-06 | [spec](features/022-driver-jvm/spec.md) |
| 023 | Driver Custom Scaffolding & Graceful Degradation | Implemented | 2026-05-06 | 2026-05-06 | [spec](features/023-driver-custom-scaffolding/spec.md) |
| 024 | Patch Coverage Local Computation | Implemented | 2026-05-06 | 2026-05-06 | [spec](features/024-patch-coverage-local/spec.md) |
| 025 | Mutation Testing On-Demand | Implemented | 2026-05-06 | 2026-05-06 | [spec](features/025-mutation-testing-on-demand/spec.md) |
| 026 | Conventions Propagation by Stack | Implemented | 2026-05-06 | 2026-05-06 | [spec](features/026-conventions-propagation-by-stack/spec.md) |
| 027 | UI Runner Architecture | Draft | 2026-05-06 | 2026-05-06 | [spec](features/027-ui-runner-architecture/spec.md) |
| 028 | UI Runner Web (Playwright Refactor) | Draft | 2026-05-06 | 2026-05-06 | [spec](features/028-ui-runner-web/spec.md) |
| 029 | UI Runner Tauri | Implemented | 2026-05-06 | 2026-05-06 | [spec](features/029-ui-runner-tauri/spec.md) |
| 030 | UI Runner iOS / watchOS | Draft | 2026-05-06 | 2026-05-06 | [spec](features/030-ui-runner-ios-watchos/spec.md) |
| 031 | UI Runner Android | Draft | 2026-05-06 | 2026-05-06 | [spec](features/031-ui-runner-android/spec.md) |
| 032 | Pre-commit / Pre-push Test Hooks | Draft | 2026-05-06 | 2026-05-06 | [spec](features/032-test-hooks-pre-commit-pre-push/spec.md) |
| 033 | Smart Test Selection | Draft | 2026-05-06 | 2026-05-06 | [spec](features/033-smart-test-selection/spec.md) |
| 034 | Preflight Auto-Install & Init | Draft | 2026-05-06 | 2026-05-06 | [spec](features/034-preflight-autofix/spec.md) |
<!-- Note: NNN=012 reserved for in-flight feature/012-brainstorm-ingestion (separate branch) -->
| 035 | Unified CLI Surface | Implemented | 2026-05-07 | 2026-05-07 | [spec](features/035-unified-cli-surface/spec.md) |
| 036 | Multi-Surface Detection and Migration | Planned | 2026-05-07 | 2026-05-07 | [spec](features/036-multi-surface-detection-and-migration/spec.md) |
| 037 | Test Multi-Runner Integration | Implemented | 2026-05-08 | 2026-05-08 | [spec](features/037-test-multi-runner-integration/spec.md), [plan](features/037-test-multi-runner-integration/plan.md), [implementation](features/037-test-multi-runner-integration/implementation.md) |
| 041 | Brainstorm Flow & Screen Specs Ingestion | Draft | 2026-05-13 | 2026-05-14 | [spec](features/041-spec-init-flow-specs-ingestion/spec.md) |
| 042 | `/spec-specify` Derives from Imported Brainstorm Flows | Draft | 2026-05-13 | 2026-05-14 | [spec](features/042-spec-specify-from-brainstorm/spec.md) |
| 043 | `/spec.sync-brainstorm` — Living Bridge to Brainstorm | Draft | 2026-05-13 | 2026-05-14 | [spec](features/043-spec-sync-brainstorm/spec.md) |
| 046 | Visual Implementation Gate | Implemented | 2026-05-17 | 2026-05-17 | [spec](features/046-visual-implementation-gate/spec.md), [plan](features/046-visual-implementation-gate/plan.md), [implementation](features/046-visual-implementation-gate/implementation.md) |
| 047 | Design Alignment Gate | Implemented | 2026-05-17 | 2026-05-17 | [spec](features/047-design-alignment-gate/spec.md), [plan](features/047-design-alignment-gate/plan.md), [implementation](features/047-design-alignment-gate/implementation.md) |
| 048 | Command Validation Hardening | Implemented | 2026-05-18 | 2026-05-18 | [spec](features/048-command-validation-hardening/spec.md), [plan](features/048-command-validation-hardening/plan.md), [implementation](features/048-command-validation-hardening/implementation.md) |
| 049 | Command Naming Normalization | Implemented | 2026-05-18 | 2026-05-18 | [spec](features/049-command-naming-normalization/spec.md), [plan](features/049-command-naming-normalization/plan.md), [implementation](features/049-command-naming-normalization/implementation.md) |
| 050 | Agent Sync Migration | Implemented | 2026-05-18 | 2026-05-18 | [spec](features/050-agent-sync-migration/spec.md), [plan](features/050-agent-sync-migration/plan.md), [implementation](features/050-agent-sync-migration/implementation.md) |
| 051 | Integrate Penflow as LiveSpec Primary UI Contract | Implemented | 2026-05-21 | 2026-05-26 | [spec](features/051-integrate-penflow-primary-ui-contract/spec.md), [plan](features/051-integrate-penflow-primary-ui-contract/plan.md), [implementation](features/051-integrate-penflow-primary-ui-contract/implementation.md) |
| 052 | Deterministic Command Goal Contracts | Implemented | 2026-05-21 | 2026-05-23 | [spec](features/052-deterministic-command-goal-contracts/spec.md), [plan](features/052-deterministic-command-goal-contracts/plan.md), [implementation](features/052-deterministic-command-goal-contracts/implementation.md) |
| 053 | Goal Tasks Replay Required Conventions Per Step | Implemented | 2026-06-01 | 2026-06-01 | [spec](features/053-goal-tasks-replay-required-conventions-per-step/spec.md), [plan](features/053-goal-tasks-replay-required-conventions-per-step/plan.md), [implementation](features/053-goal-tasks-replay-required-conventions-per-step/implementation.md) |
| 054 | Migration Planner and Penflow Backfill | Implemented | 2026-06-01 | 2026-06-01 | [spec](features/054-migration-planner-penflow-backfill/spec.md), [plan](features/054-migration-planner-penflow-backfill/plan.md), [implementation](features/054-migration-planner-penflow-backfill/implementation.md) |
| 055 | Spec Doctor Project Health | Draft | 2026-06-01 | 2026-06-01 | [spec](features/055-spec-doctor-project-health/spec.md) |
| 056 | Executable User Journeys | Draft | 2026-06-01 | 2026-06-01 | [spec](features/056-executable-user-journeys/spec.md) |
<!-- readme:features:end -->

---

## Architecture Decisions

<!-- readme:decisions:start -->
| ADR | Decision | Date | Status |
|---|---|---|---|
| ADR-001 | Python 3.11+ as primary language | 2026-04-13 | Active |
| ADR-002 | Typer + Pydantic as CLI and validation frameworks | 2026-04-13 | Active |
| ADR-003 | Ruff + Pyright for code quality | 2026-04-13 | Active |
<!-- readme:decisions:end -->

---

## Recent Activity

> Latest entries from [changelog.md](changelog.md).

<!-- readme:activity:start -->
| Date | Type | Description |
|---|---|---|
| 2026-06-01 | Spec | [Feature 056] Spec created: Executable User Journeys — YAML canonical user journeys compiled ahead-of-time to native tests and audited by Spec Doctor |
| 2026-06-01 | Spec | [Feature 055] Spec created: Spec Doctor Project Health — project-level health audit for stale mappings, missing tests, unenforced hooks, runners, visual evidence, and journeys |
| 2026-06-01 | Feature | [Feature 054] Implemented: metadata-aware migration planning, restore-point invalidation reporting, and Migration 17 Penflow backfill reports |
| 2026-06-01 | Feature | [Feature 053] Implemented: goal tasks replay required conventions and proof validation rejects missing convention evidence |
| 2026-05-26 | Bugfix | [Feature 051] Single Penflow source contract: root `penflow/ui.pen` only, explicit Brainstorm `penflow/` import, duplicate `.pen` blocking, and no `.specs/design/ui.pen` requirement |
| 2026-05-23 | Bugfix | [Feature 052] Internal `/spec-*` subagent invocations propagate current LiveSpec project root/cwd and command audit rejects missing workdir guards |
| 2026-05-23 | Bugfix | [Feature 052] Goal rendering ignores documentary `/spec-*` examples/recovery hints, skips Markdown checkboxes inside `Execution Tasks`, exposes top-level `worker_may_mark_tasks_complete=false`, and adds machine Goal Lock tasks to `/spec-status` + `/spec-explain` |
| 2026-05-23 | Bugfix | [Feature 052] Deterministic command goals write `contract.json` + `state.json`, require `livespec goal prove/status`, and reject visual design-fidelity completion when PNG proof is missing |
| 2026-05-21 | Bugfix | [Feature 052] Deterministic command goals now embed applicable `.conventions/index.md` domains for code and UI/mockup/visual work |
| 2026-05-21 | Feature | [Feature 052] Implemented: Deterministic Command Goal Contracts — `livespec goal render/verify`, canonical hashable goal payloads, and expectation-backed completion gates |
| 2026-05-21 | Feature | [Feature 051] Implemented: Integrate Penflow as LiveSpec primary UI contract — root `penflow/` helper/CLI and command docs while preserving screenshot gates |
| 2026-05-18 | Feature | [Feature 050] Implemented: Agent Sync Migration — `.agent-sync` is now the canonical source for commands, agents, and rules; cc-hub syncs Claude/Codex outputs |
| 2026-05-18 | Feature | [Feature 049] Implemented: Command Naming Normalization — canonical `/spec-*` slash commands with dotted aliases |
| 2026-05-18 | Feature | [Feature 048] Implemented: Command Validation Hardening — command-audit score 5/5, run finalization, deterministic utility backends |
| 2026-05-18 | Spec | [Feature 049] Spec created: Command Naming Normalization — canonical `/spec-*` names, dotted aliases, migration after Feature 048 |
| 2026-05-18 | Spec | [Feature 048] Spec created: Command Validation Hardening — 5/5 command audit, deterministic backends, mandatory run finalization |
| 2026-05-17 | Feature | [Feature 047] Implemented: Design Alignment Gate — reusable `ui.pen` → runtime alignment gate for `/spec-test --visual` |
| 2026-05-17 | Feature | [Feature 046] Implemented: Visual Implementation Gate — mandatory `/spec-test --auto --visual` before UI feature finalization |
| 2026-05-13 | Spec | [Feature 043] Spec created: `/spec.sync-brainstorm` — Living Bridge to Brainstorm — 5 stories, 17 AC, 18 FR |
| 2026-05-13 | Spec | [Feature 042] Spec created: `/spec-specify` Derives from Imported Brainstorm Flows — 3 stories, 13 AC, 13 FR |
| 2026-05-13 | Spec | [Feature 041] Spec created: Brainstorm Flow & Screen Specs Ingestion — 3 stories, 14 AC, 12 FR |
| 2026-05-13 | Update | [Migration v13] Backfill command-expectations wiring — re-link `.claude/commands/`, install `last_reviewed` hook, wire `/spec-verify-output` and ignore `.specs/.runs/` + `.specs/.previews/` |
| 2026-05-12 | Feature | [Feature 040] Implemented: Rich Expectations Format & Verify Preview — Section 13 mandatory, preview mode added, +15 tests, 0 regressions |
| 2026-05-12 | Feature | [Feature 039] Implemented: Command Expectations & /spec-verify-output — 20 builtin expectations files, verify-output CLI + slash-command |
| 2026-05-08 | Feature | [Feature 037] Implemented: Test Multi-Runner Integration — runner-aware dispatcher, `--visual` flag documented, 0 regressions |
| 2026-05-08 | Spec | [Feature 037] Spec created: Test Multi-Runner Integration — 5 stories, 15 AC, 15 FR |
<!-- readme:activity:end -->

---

*Maintained automatically by LiveSpec commands. Do not remove section markers.*
