# Changelog — Feature 052 — Deterministic Command Goal Contracts

## 2026-05-22 — [Fix]: FR-011 runtime gap — @import replaced by explicit Read directive

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** All 20 `.agent-sync/skills/spec-*/SKILL.md`
- **Gaps closed:** FR-011 runtime gap — `<!-- @import system/anti-drift-block.md -->` (HTML comment, never processed by Claude) replaced by `> **Read** [system/anti-drift-block.md](../../../system/anti-drift-block.md) before starting` directive that Claude actually executes
- **Remaining:** None
- **Author:** spec-fix

## 2026-05-21 — [Spec]: Spec + Plan

- **Type:** Spec Update
- **Spec modified:** Yes (`spec.md`, `plan.md`)
- **Code modified:** none
- **AC impacted:** AC-001..AC-010
- **Author:** tool

## 2026-05-21 — [Feature]: Feature Implementation

- **Type:** Feature
- **Spec modified:** Yes (`implementation.md`, `progress.md`)
- **Code modified:** `validator/goal_contracts.py`, `validator/cli_commands/goal_cmd.py`, `validator/cli.py`
- **Docs modified:** `system/anti-drift-block.md`, `system/expectations.md`
- **Tests added:** `tests/test_goal_contracts.py`, `tests/test_goal_contracts_cli.py`
- **AC impacted:** AC-001..AC-010
- **Author:** codex

## 2026-05-21 — [Fix]: Anchor gaps FR-011, FR-012, FR-014, FR-015 closed

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** `validator/goal_contracts.py`, `system/anti-drift-block.md`, `system/expectations.md`
- **Gaps closed:** FR-011, FR-012, FR-014, FR-015 (missing `@spec` anchors)
- **Remaining:** None
- **Author:** spec-fix

## 2026-05-21 — [Check]: Spec-code alignment verified

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **Coverage:** 11/15 FR verified (73%), 13/13 AC verified (100%), 4 FR partial (anchor gaps only)
- **Report:** `checks/2026-05-21.md`
- **Author:** spec-check

## 2026-05-21 — [Fix]: Convention domains added to command goals

- **Type:** Bugfix
- **Spec modified:** Yes (`spec.md`, `plan.md`, `implementation.md`, `progress.md`)
- **Code modified:** `validator/goal_contracts.py`, `tests/test_goal_contracts.py`
- **Docs modified:** `system/expectations.md`
- **AC impacted:** AC-011, AC-012, AC-013
- **Author:** codex
