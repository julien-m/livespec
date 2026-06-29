# .specs — LiveSpec

> Specification registry for LiveSpec. All artifacts produced by LiveSpec are indexed here.
>
> Last updated: 2026-06-29


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
| 001 | Auto LLM Review | Implemented | 2026-04-13 | 2026-06-10 | [spec](features/001-auto-llm-review/spec.md) |
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
| 038 | Runner Config Wiring | Implemented | 2026-05-08 | 2026-06-08 | [spec](features/038-runner-config-wiring/spec.md), [plan](features/038-runner-config-wiring/plan.md), [implementation](features/038-runner-config-wiring/implementation.md) |
| 039 | Command Expectations and Verify Output | Implemented | 2026-05-12 | 2026-06-08 | [spec](features/039-command-expectations-and-verify-output/spec.md), [implementation](features/039-command-expectations-and-verify-output/implementation.md) |
| 039.1 | Goal Archive & Run Artifacts v2 | Implemented | 2026-06-10 | 2026-06-10 | [spec](features/039.1-goal-archive-run-artifacts/spec.md), [plan](features/039.1-goal-archive-run-artifacts/plan.md), [implementation](features/039.1-goal-archive-run-artifacts/implementation.md) |
| 040 | Expectations Rich and Verify Preview | Implemented | 2026-05-12 | 2026-06-08 | [spec](features/040-expectations-rich-and-verify-preview/spec.md), [implementation](features/040-expectations-rich-and-verify-preview/implementation.md) |
| 041 | Brainstorm Flow & Screen Specs Ingestion | Draft | 2026-05-13 | 2026-05-14 | [spec](features/041-spec-init-flow-specs-ingestion/spec.md) |
| 042 | `/spec-specify` Derives from Imported Brainstorm Flows | Draft | 2026-05-13 | 2026-05-14 | [spec](features/042-spec-specify-from-brainstorm/spec.md) |
| 043 | `/spec.sync-brainstorm` — Living Bridge to Brainstorm | Draft | 2026-05-13 | 2026-05-14 | [spec](features/043-spec-sync-brainstorm/spec.md) |
| 044 | Behavioral Grammar v1.0 Shared | Implemented | 2026-05-14 | 2026-06-08 | [spec](features/044-behavioral-grammar-v1-shared/spec.md), [implementation](features/044-behavioral-grammar-v1-shared/implementation.md) |
| 045 | Native Behavioral Specs | Implemented | 2026-05-14 | 2026-06-08 | [spec](features/045-native-behavioral-specs/spec.md), [implementation](features/045-native-behavioral-specs/implementation.md) |
| 046 | Visual Implementation Gate | Implemented | 2026-05-17 | 2026-05-17 | [spec](features/046-visual-implementation-gate/spec.md), [plan](features/046-visual-implementation-gate/plan.md), [implementation](features/046-visual-implementation-gate/implementation.md) |
| 047 | Design Alignment Gate | Implemented | 2026-05-17 | 2026-05-17 | [spec](features/047-design-alignment-gate/spec.md), [plan](features/047-design-alignment-gate/plan.md), [implementation](features/047-design-alignment-gate/implementation.md) |
| 048 | Command Validation Hardening | Implemented | 2026-05-18 | 2026-05-18 | [spec](features/048-command-validation-hardening/spec.md), [plan](features/048-command-validation-hardening/plan.md), [implementation](features/048-command-validation-hardening/implementation.md) |
| 049 | Command Naming Normalization | Implemented | 2026-05-18 | 2026-05-18 | [spec](features/049-command-naming-normalization/spec.md), [plan](features/049-command-naming-normalization/plan.md), [implementation](features/049-command-naming-normalization/implementation.md) |
| 050 | Agent Sync Migration | Implemented | 2026-05-18 | 2026-05-18 | [spec](features/050-agent-sync-migration/spec.md), [plan](features/050-agent-sync-migration/plan.md), [implementation](features/050-agent-sync-migration/implementation.md) |
| 051 | Integrate Penflow as LiveSpec Primary UI Contract | Implemented | 2026-05-21 | 2026-05-26 | [spec](features/051-integrate-penflow-primary-ui-contract/spec.md), [plan](features/051-integrate-penflow-primary-ui-contract/plan.md), [implementation](features/051-integrate-penflow-primary-ui-contract/implementation.md) |
| 052 | Deterministic Command Goal Contracts | Implemented | 2026-05-21 | 2026-06-25 | [spec](features/052-deterministic-command-goal-contracts/spec.md), [plan](features/052-deterministic-command-goal-contracts/plan.md), [implementation](features/052-deterministic-command-goal-contracts/implementation.md) |
| 053 | Goal Tasks Replay Required Conventions Per Step | Implemented | 2026-06-01 | 2026-06-01 | [spec](features/053-goal-tasks-replay-required-conventions-per-step/spec.md), [plan](features/053-goal-tasks-replay-required-conventions-per-step/plan.md), [implementation](features/053-goal-tasks-replay-required-conventions-per-step/implementation.md) |
| 054 | Migration Planner and Penflow Backfill | Implemented | 2026-06-01 | 2026-06-01 | [spec](features/054-migration-planner-penflow-backfill/spec.md), [plan](features/054-migration-planner-penflow-backfill/plan.md), [implementation](features/054-migration-planner-penflow-backfill/implementation.md) |
| 055 | Spec Doctor Project Health | Implemented | 2026-06-01 | 2026-06-02 | [spec](features/055-spec-doctor-project-health/spec.md), [plan](features/055-spec-doctor-project-health/plan.md), [implementation](features/055-spec-doctor-project-health/implementation.md) |
| 056 | Executable User Journeys | Implemented | 2026-06-01 | 2026-06-02 | [spec](features/056-executable-user-journeys/spec.md), [plan](features/056-executable-user-journeys/plan.md), [implementation](features/056-executable-user-journeys/implementation.md) |
| 057 | Cross-Feature User Journeys v2 | Implemented | 2026-06-04 | 2026-06-09 | [spec](features/057-cross-feature-user-journeys-v2/spec.md), [plan](features/057-cross-feature-user-journeys-v2/plan.md), [implementation](features/057-cross-feature-user-journeys-v2/implementation.md) |
| 058 | Deterministic Finalization | Implemented | 2026-06-10 | 2026-06-10 | [spec](features/058-deterministic-finalization/spec.md), [plan](features/058-deterministic-finalization/plan.md), [implementation](features/058-deterministic-finalization/implementation.md) |
| 059 | Pipeline Verify Phase | Implemented | 2026-06-11 | 2026-06-11 | [spec](features/059-pipeline-verify-phase/spec.md), [plan](features/059-pipeline-verify-phase/plan.md), [implementation](features/059-pipeline-verify-phase/implementation.md) |
| 060 | Journey Fixture Bootstrap Contract | Implemented | 2026-06-11 | 2026-06-11 | [spec](features/060-journey-fixture-bootstrap-contract/spec.md), [plan](features/060-journey-fixture-bootstrap-contract/plan.md), [implementation](features/060-journey-fixture-bootstrap-contract/implementation.md) |
| 061 | Conventions Gates Engine | Implemented | 2026-06-12 | 2026-06-25 | [spec](features/061-conventions-gates-engine/spec.md) |
| 062 | Conventions Rulebook Semantic | Implemented | 2026-06-12 | 2026-06-12 | [spec](features/062-conventions-rulebook-semantic/spec.md), [plan](features/062-conventions-rulebook-semantic/plan.md), [implementation](features/062-conventions-rulebook-semantic/implementation.md) |
| 063 | Conventions Blocking Pipeline | Implemented | 2026-06-13 | 2026-06-13 | [spec](features/063-conventions-blocking-pipeline/spec.md), [plan](features/063-conventions-blocking-pipeline/plan.md), [implementation](features/063-conventions-blocking-pipeline/implementation.md) |
| 064 | Conventions Bootstrap Remediation | Implemented | 2026-06-13 | 2026-06-13 | [spec](features/064-conventions-bootstrap-remediation/spec.md), [plan](features/064-conventions-bootstrap-remediation/plan.md), [implementation](features/064-conventions-bootstrap-remediation/implementation.md) |
| 065 | Conventions Migration Docs | Implemented | 2026-06-13 | 2026-06-13 | [spec](features/065-conventions-migration-docs/spec.md), [plan](features/065-conventions-migration-docs/plan.md), [implementation](features/065-conventions-migration-docs/implementation.md) |
| 066 | Handoff Input Compatibility | Implemented | 2026-06-15 | 2026-06-15 | [spec](features/066-handoff-input-compatibility/spec.md), [plan](features/066-handoff-input-compatibility/plan.md), [implementation](features/066-handoff-input-compatibility/implementation.md) |
| 067 | Visual Preview Proof Publishing | Implemented | 2026-06-25 | 2026-06-25 | [spec](features/067-visual-preview-proof-publishing/spec.md), [plan](features/067-visual-preview-proof-publishing/plan.md), [implementation](features/067-visual-preview-proof-publishing/implementation.md) |
| 068 | Evidence-First Retry Contract | Implemented | 2026-06-26 | 2026-06-26 | [spec](features/068-evidence-first-retry-contract/spec.md), [plan](features/068-evidence-first-retry-contract/plan.md), [implementation](features/068-evidence-first-retry-contract/implementation.md) |
| 069 | Clarify Gate | Implemented | 2026-06-27 | 2026-06-27 | [spec](features/069-clarify-gate/spec.md), [plan](features/069-clarify-gate/plan.md), [implementation](features/069-clarify-gate/implementation.md) |
| 070 | Analyze Gate | Implemented | 2026-06-27 | 2026-06-27 | [spec](features/070-analyze-gate/spec.md), [plan](features/070-analyze-gate/plan.md), [implementation](features/070-analyze-gate/implementation.md) |
| 071 | QE Analysis Native Module | Implemented | 2026-06-27 | 2026-06-27 | [spec](features/071-qe-analysis-native-module/spec.md), [plan](features/071-qe-analysis-native-module/plan.md), [implementation](features/071-qe-analysis-native-module/implementation.md) |
| 072 | Conventions AST Rule Engine | Implemented | 2026-06-29 | 2026-06-29 | [spec](features/072-conventions-ast-rule-engine/spec.md), [plan](features/072-conventions-ast-rule-engine/plan.md), [implementation](features/072-conventions-ast-rule-engine/implementation.md) |
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
| 2026-06-29 | Feature | [Feature 072] /spec-feature complete: AST conventions rollout engine — implement/test/audit all green, full pytest 2281 passed, conventions receipt PASS |
| 2026-06-29 | Feature | [Feature 072] Test: 100% AC covered (17/17), 0 tests generated — targeted Ruff, pytest 177 passed, `.specs` validation, and conventions receipt PASS |
| 2026-06-29 | Feature | [Feature 072] Implemented: Conventions AST Rule Engine — v1/v2 gates, AST observe/enforce engine, v2 receipts, mode-aware policy, active ast/high catalogue, and scoped conventions receipt repair |
| 2026-06-29 | Plan | [Feature 072] Plan created: Conventions AST Rule Engine — phased AST conventions rollout with v1/v2 gates, receipts, backend, doctor/spec-check, and catalogue activation |
| 2026-06-29 | Spec | [Feature 072] Spec created: Conventions AST Rule Engine — 4 stories, 17 AC, 18 FR |
| 2026-06-27 | Check | [Feature 071] Check: 100% FR/AC verified; implementation and conventions PASS; AC format warning remains |
| 2026-06-27 | Feature | [Feature 071] Implemented: QE Analysis Native Module — native QE context, `qe.analysis` goal task, structured evidence validation, additive user hooks |
| 2026-06-27 | Feature | [Feature 070] Analyze Gate — retroactive spec+plan+mapping for read-only pre-impl gate; dogfooded Clarify (empty queue) + Analyze (0 CRITICAL/HIGH, exit 0) |
| 2026-06-27 | Plan | [Feature 069] Plan created: Clarify Gate — 7 implementation steps (retroactive, maps to existing code), 1 state diagram |
<!-- readme:activity:end -->

---

*Maintained automatically by LiveSpec commands. Do not remove section markers.*

<!-- finalize:spec-implement:2026-06-10:9a1dbf71 -->

<!-- finalize:spec-feature:2026-06-10:96deb6de -->

<!-- finalize:spec-fix:2026-06-10:24ee3265 -->

<!-- finalize:spec-specify:2026-06-10:de700238 -->

<!-- finalize:spec-plan:2026-06-10:362ef347 -->

<!-- finalize:spec-implement:2026-06-10:2395e303 -->

<!-- finalize:spec-test:2026-06-10:cea2d0c7 -->

<!-- finalize:spec-feature:2026-06-10:645cecd3 -->

<!-- finalize:spec-specify:2026-06-11:799a2740 -->

<!-- finalize:spec-plan:2026-06-11:79911967 -->

<!-- finalize:spec-implement:2026-06-11:0cb1ffd0 -->

<!-- finalize:spec-test:2026-06-11:58a3c008 -->

<!-- finalize:spec-feature:2026-06-11:4089ae8a -->

<!-- finalize:spec-specify:2026-06-11:15d1d511 -->

<!-- finalize:spec-plan:2026-06-11:8bbd6ff2 -->

<!-- finalize:spec-implement:2026-06-11:b2cd1c13 -->

<!-- finalize:spec-feature:2026-06-11:61c37125 -->

<!-- finalize:spec-feature:2026-06-12:a140dc75 -->

<!-- finalize:spec-implement:2026-06-12:3e197383 -->

<!-- finalize:spec-specify:2026-06-27:6ceeb87f -->

<!-- finalize:spec-plan:2026-06-27:d8275811 -->

<!-- finalize:spec-specify:2026-06-29:4d481d61 -->

<!-- finalize:spec-plan:2026-06-29:fdbed7ea -->

<!-- finalize:spec-implement:2026-06-29:7d37e57a -->

<!-- finalize:spec-feature:2026-06-29:3ef3e24f -->
