# Changelog — 056 Executable User Journeys

## 2026-10-12 — [Refactor]: Vacuous journey tests removed; AC-004 and AC-015 recorded as missing

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_journeys.py, implementation.md (AC-004, AC-015 rows)
- **AC impacted:** AC-004, AC-015
- **Author:** claude-code (test-suite cleanup lot 3)

`test_wait_without_until_or_reason_is_warning` was a verbatim copy of the valid-YAML test with no `wait` step: the v2 step schema (057) has no `until`/`reason` fields and no validator emits the fixed-wait warning. AC-015 pointed at a test that does not exist and a `manual` journey without `manual_reason` validates cleanly. Both ACs are now marked Missing instead of Implemented; a manual-journey test that only re-validated was removed.

## 2026-06-03 — [Check]: Closed spec-check gaps

- **Type:** Spec Update
- **Spec modified:** Yes (plan frontmatter and diagram sections)
- **Code modified:** `tests/test_journeys.py`, `validator/goal_contracts.py`, `tests/test_goal_contracts.py`
- **Docs modified:** `implementation.md`, `checks/2026-06-03.md`
- **Coverage:** 28/28 verified (100%), 0 partial, 0 missing
- **Report:** `checks/2026-06-03.md`
- **AC impacted:** AC-013, AC-015
- **Author:** Codex

## 2026-06-02 — Feature: Implemented executable user journeys

- **Spec modified:** Yes (status/date).
- **Code modified:** `validator/journeys/*`, `validator/cli_commands/journey_cmd.py`, `validator/cli_commands/test_cmd.py`, `validator/doctor/scanner.py`.
- **Docs modified:** `system/testing/user-journeys.md`, `.agent-sync/skills/spec-specify/SKILL.md`, `.agent-sync/skills/spec-feature/SKILL.md`, `.agent-sync/skills/spec-test/SKILL.md`.
- **AC impacted:** AC-001..AC-015.
- **Author:** codex.
