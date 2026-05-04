# .specs — LiveSpec

> Specification registry for LiveSpec. All artifacts produced by LiveSpec are indexed here.
>
> Last updated: 2026-05-03


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
| 002 | Layer 3 CLI Surface | Planned | 2026-04-13 | 2026-04-13 | [spec](features/002-layer-3-cli-surface/spec.md) |
| 003 | Visual Testing Fidelity | Implemented | 2026-04-14 | 2026-04-14 | [spec](features/003-visual-testing-fidelity/spec.md) |
| 004 | Visual Testing Governance | Implemented | 2026-04-14 | 2026-04-14 | [spec](features/004-visual-testing-governance/spec.md) |
| 005 | UI Behavioral Testing | Planned | 2026-04-14 | 2026-04-14 | [spec](features/005-ui-behavioral-testing/spec.md) |
| 006 | Taxonomy Testing Infrastructure | Planned | 2026-04-15 | 2026-04-15 | [spec](features/006-taxonomy-testing-infra/spec.md) |
| 007 | Structured Signal Extraction | Planned | 2026-04-15 | 2026-04-15 | [spec](features/007-structured-signal-extraction/spec.md) |
| 008 | Feature Seed | Draft | 2026-04-16 | 2026-04-16 | [spec](features/008-feature-seed/spec.md) |
| 009 | Visual State Baselines | Planned | 2026-04-17 | 2026-04-17 | [spec](features/009-visual-state-baselines/spec.md) |
| 005.1 | Behavioral TDD Audit | Draft | 2026-04-17 | 2026-04-17 | [spec](features/005.1-behavioral-tdd-audit/spec.md) |
| 005.2 | Taxonomy Complete Expansion | Draft | 2026-04-17 | 2026-04-17 | [spec](features/005.2-taxonomy-complete-expansion/spec.md) |
| 010 | Visual Testing Complete | Implemented | 2026-04-17 | 2026-04-17 | [spec](features/010-visual-testing-complete/spec.md) |
| 011 | Visual Migrate Integration | Implemented | 2026-04-17 | 2026-04-17 | [spec](features/011-visual-migrate-integration/spec.md) |
| 013 | State Model & Identity Resolution | Draft | 2026-05-03 | 2026-05-03 | [spec](features/013-state-model-identity-resolution/spec.md) |
| 014 | Supervisor↔Subagent Return Contracts | Draft | 2026-05-03 | 2026-05-03 | [spec](features/014-supervisor-contracts/spec.md) |
| 015 | Global Write Locks & Atomic NNN Reservation | Draft | 2026-05-03 | 2026-05-03 | [spec](features/015-global-write-locks/spec.md) |
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
| 2026-05-03 | Spec | [Feature 015] Spec created: Global Write Locks & Atomic NNN Reservation — 5 stories, 10 AC, 10 FR |
| 2026-05-03 | Spec | [Feature 014] Spec created: Supervisor↔Subagent Return Contracts — 5 stories, 10 AC, 10 FR |
| 2026-05-03 | Spec | [Feature 013] Spec created: State Model & Identity Resolution — 5 stories, 10 AC, 10 FR |
| 2026-04-17 | Feature | [Feature 011] Implemented: Visual Migrate Integration — 11 integration tests, command-layer guards documented |
| 2026-04-17 | Spec | [Feature 011] Spec created: Visual Migrate Integration — 4 stories, 12 AC, 11 FR |
| 2026-04-17 | Feature | [Feature 010] Implemented: Visual Testing Complete — downstream Playwright scaffolding added; pytest suite remains green |
| 2026-04-17 | Plan | [Feature 010] Plan created: Visual Testing Complete — 8 steps, 4 TS templates, 3 scripts, 8 docs, 1 CI workflow |
| 2026-04-17 | Spec | [Feature 010] Spec created: Visual Testing Complete — 7 stories, 30 AC, 25 FR |
| 2026-04-17 | Spec | [Feature 005.2] Spec created: Taxonomy Complete Expansion — 5 stories, 20 AC, 12 FR |
| 2026-04-17 | Spec | [Feature 009] Spec created: Visual State Baselines — 5 stories, 15 AC, 11 FR |
| 2026-04-16 | Spec | [Feature 008] Spec created: Feature Seed — 5 stories, 11 AC, 7 FR |
| 2026-04-15 | Plan | [Feature 007] Plan created: Structured Signal Extraction — 3 implementation steps, 1 diagram |
| 2026-04-15 | Spec | [Feature 007] Spec created: Structured Signal Extraction — 4 stories, 8 AC, 7 FR |
| 2026-04-15 | Spec | [Feature 006] Spec created: Taxonomy Testing Infrastructure — 4 stories, 15 AC, 8 FR |
| 2026-04-14 | Plan | [Feature 005] Plan created: UI Behavioral Testing — 5 steps, 4 diagrams |
| 2026-04-14 | Spec | [Feature 005] Spec created: UI Behavioral Testing — 5 stories, 13 AC, 9 FR |
| 2026-04-14 | Feature | [Feature 004] Implemented: Visual Testing Governance — 4 new files, 2 modified, 41 new tests, 406 total pass |
| 2026-04-14 | Plan | [Feature 004] Plan created: Visual Testing Governance — 7 steps, 4 diagrams |
| 2026-04-14 | Feature | [Feature 003] Implemented: Visual Testing Fidelity — 6 files modified, 2 created, 14/14 AC |
| 2026-04-14 | Plan | [Feature 003] Plan created: Visual Testing Fidelity — 8 steps, 3 diagrams |
| 2026-04-14 | Spec | [Feature 004] Spec created: Visual Testing Governance — 4 stories, 12 AC, 8 FR |
| 2026-04-14 | Spec | [Feature 003] Spec created: Visual Testing Fidelity — 6 stories, 14 AC, 10 FR |
| 2026-04-13 | Plan | [Feature 002] Plan created: Layer 3 CLI Surface -- 7 steps, 3 diagrams |
| 2026-04-13 | Spec | [Feature 002] Spec created: Layer 3 CLI Surface -- 4 stories, 10 AC, 9 FR |
| 2026-04-13 | Feature | [Feature 001] Implemented: Auto LLM Review -- 4 new files, 3 modified, 36 new tests |
| 2026-04-13 | Plan | [Feature 001] Plan created: Auto LLM Review -- 6 implementation steps, 3 diagrams |
| 2026-04-13 | Setup | LiveSpec initialized via spec.init --from-code |
<!-- readme:activity:end -->

---

*Maintained automatically by LiveSpec commands. Do not remove section markers.*
