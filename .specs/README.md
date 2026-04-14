# .specs — LiveSpec

> Specification registry for LiveSpec. All artifacts produced by LiveSpec are indexed here.
>
> Last updated: 2026-04-13

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
| 003 | Visual Testing Fidelity | Draft | 2026-04-14 | 2026-04-14 | [spec](features/003-visual-testing-fidelity/spec.md) |
| 004 | Visual Testing Governance | Draft | 2026-04-14 | 2026-04-14 | [spec](features/004-visual-testing-governance/spec.md) |
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
| 2026-04-13 | Plan | [Feature 002] Plan created: Layer 3 CLI Surface -- 7 steps, 3 diagrams |
| 2026-04-13 | Spec | [Feature 002] Spec created: Layer 3 CLI Surface -- 4 stories, 10 AC, 9 FR |
| 2026-04-13 | Feature | [Feature 001] Implemented: Auto LLM Review -- 4 new files, 3 modified, 36 new tests |
| 2026-04-13 | Plan | [Feature 001] Plan created: Auto LLM Review -- 6 implementation steps, 3 diagrams |
| 2026-04-14 | Spec | [Feature 004] Spec created: Visual Testing Governance — 4 stories, 12 AC, 8 FR |
| 2026-04-14 | Spec | [Feature 003] Spec created: Visual Testing Fidelity — 6 stories, 14 AC, 10 FR |
| 2026-04-13 | Spec | [Feature 001] Spec created: Auto LLM Review -- 4 stories, 14 AC, 11 FR |
| 2026-04-13 | Setup | LiveSpec initialized via spec.init --from-code |
<!-- readme:activity:end -->

---

*Maintained automatically by LiveSpec commands. Do not remove section markers.*
