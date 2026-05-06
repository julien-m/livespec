# .specs — LiveSpec

> Specification registry for LiveSpec. All artifacts produced by LiveSpec are indexed here.
>
> Last updated: 2026-05-06


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
| 016 | Cross-Language Test Driver Architecture | Draft | 2026-05-06 | 2026-05-06 | [spec](features/016-cross-language-test-driver-architecture/spec.md) |
| 017 | Driver Python | Draft | 2026-05-06 | 2026-05-06 | [spec](features/017-driver-python/spec.md) |
| 018 | Driver TypeScript/JavaScript | Draft | 2026-05-06 | 2026-05-06 | [spec](features/018-driver-typescript-javascript/spec.md) |
| 019 | Driver Swift | Draft | 2026-05-06 | 2026-05-06 | [spec](features/019-driver-swift/spec.md) |
| 020 | Driver Go | Draft | 2026-05-06 | 2026-05-06 | [spec](features/020-driver-go/spec.md) |
| 021 | Driver Rust | Draft | 2026-05-06 | 2026-05-06 | [spec](features/021-driver-rust/spec.md) |
| 022 | Driver JVM (Java + Kotlin) | Draft | 2026-05-06 | 2026-05-06 | [spec](features/022-driver-jvm/spec.md) |
| 023 | Driver Custom Scaffolding & Graceful Degradation | Draft | 2026-05-06 | 2026-05-06 | [spec](features/023-driver-custom-scaffolding/spec.md) |
| 024 | Patch Coverage Local Computation | Draft | 2026-05-06 | 2026-05-06 | [spec](features/024-patch-coverage-local/spec.md) |
| 025 | Mutation Testing On-Demand | Draft | 2026-05-06 | 2026-05-06 | [spec](features/025-mutation-testing-on-demand/spec.md) |
| 026 | Conventions Propagation by Stack | Draft | 2026-05-06 | 2026-05-06 | [spec](features/026-conventions-propagation-by-stack/spec.md) |
| 027 | UI Runner Architecture | Draft | 2026-05-06 | 2026-05-06 | [spec](features/027-ui-runner-architecture/spec.md) |
| 028 | UI Runner Web (Playwright Refactor) | Draft | 2026-05-06 | 2026-05-06 | [spec](features/028-ui-runner-web/spec.md) |
| 029 | UI Runner Tauri | Draft | 2026-05-06 | 2026-05-06 | [spec](features/029-ui-runner-tauri/spec.md) |
| 030 | UI Runner iOS / watchOS | Draft | 2026-05-06 | 2026-05-06 | [spec](features/030-ui-runner-ios-watchos/spec.md) |
| 031 | UI Runner Android | Draft | 2026-05-06 | 2026-05-06 | [spec](features/031-ui-runner-android/spec.md) |
| 032 | Pre-commit / Pre-push Test Hooks | Draft | 2026-05-06 | 2026-05-06 | [spec](features/032-test-hooks-pre-commit-pre-push/spec.md) |
| 033 | Smart Test Selection | Draft | 2026-05-06 | 2026-05-06 | [spec](features/033-smart-test-selection/spec.md) |
| 034 | Preflight Auto-Install & Init | Draft | 2026-05-06 | 2026-05-06 | [spec](features/034-preflight-autofix/spec.md) |
<!-- Note: NNN=012 reserved for in-flight feature/012-brainstorm-ingestion (separate branch) -->
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
| 2026-05-06 | Spec | [Feature 034] Spec created: Preflight Auto-Install & Init via /spec.preflight --fix — 5 stories, 14 AC, 11 FR |
| 2026-05-06 | Spec | [Feature 033] Spec created: Smart Test Selection — 4 stories, 12 AC, 10 FR |
| 2026-05-06 | Spec | [Feature 032] Spec created: Pre-commit / Pre-push Test Hooks — 5 stories, 13 AC, 10 FR |
| 2026-05-06 | Spec | [Feature 031] Spec created: UI Runner Android (Maestro) — 3 stories, 13 AC, 8 FR |
| 2026-05-06 | Spec | [Feature 030] Spec created: UI Runner iOS / watchOS (XCUITest) — 4 stories, 14 AC, 9 FR |
| 2026-05-06 | Spec | [Feature 029] Spec created: UI Runner Tauri — 3 stories, 12 AC, 7 FR |
| 2026-05-06 | Spec | [Feature 028] Spec created: UI Runner Web (Playwright Refactor) — 2 stories, 8 AC, 5 FR |
| 2026-05-06 | Spec | [Feature 027] Spec created: UI Runner Architecture — 4 stories, 12 AC, 8 FR |
| 2026-05-06 | Fix | [Features 013, 014, 015] Fix: implementation.md created (post-merge bookkeeping for Chantiers 4/2/3) |
| 2026-05-06 | Spec | [Feature 026] Spec created: Conventions Propagation by Stack — 3 stories, 8 AC, 7 FR |
<!-- readme:activity:end -->

---

*Maintained automatically by LiveSpec commands. Do not remove section markers.*
