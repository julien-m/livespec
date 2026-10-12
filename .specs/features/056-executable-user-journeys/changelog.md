# Changelog — 056 Executable User Journeys

## 2026-10-12 — [Bugfix]: Fix: AC-003, AC-004, AC-015 implemented; FR-005 select and FR-007 portable XCUITest target

- **Type:** Bug Fix
- **Spec modified:** Yes (Clarifications session 2026-10-12: v2 layout and shape, `wait` fields, bounded waits, manual reason, run stages, exit codes, action/runner matrix, XCUITest destination, Maestro and Playwright outputs, superseded ACs, interactive features, compile-ahead gate; FR-003/FR-004/AC-001 wording, Story 1/2 Gherkin, Canonical YAML Shape, Edge Cases)
- **Plan modified:** Yes (rewritten on the shipped v2 pipeline; steps 9–16)
- **Code modified:** `validator/journeys/schema.py`, `validator/journeys/validator.py`, `validator/journeys/capabilities.py`, `validator/journeys/compiler.py`, `validator/journeys/paths.py`, `validator/journeys/runner.py`, `validator/journeys/migration.py`, `validator/cli_commands/journey_cmd.py`, `validator/exceptions.py`, `system/testing/user-journeys.md`
- **Tests:** new `tests/test_journeys_wait_manual.py`, `tests/test_journeys_select_targets.py`; adapted fixtures in `tests/test_journeys.py`, `tests/test_journey_v2_compiler.py`, `tests/_journey_v2_runner_01.py`, `tests/_journey_v2_runner_02.py`, `tests/test_journey_v2_fixtures_contract.py`. The 057 test that asserted XCUITest refuses `wait` now asserts the refusal of `press`, because `wait` compiles since AC-003.
- **Gaps closed:** AC-003 (previously mapped to a test without any `wait` step), AC-004, AC-015, FR-005 (`select` on Playwright, explicit refusal elsewhere), FR-007 (no hardcoded `STRAPTUITests`; `journey_xcuitest_target_unresolved`, compile exit 3)
- **Reviews:** independent spec and plan reviews, complete and ready (`.reviews/spec.json`, `.reviews/plan.json`, model claude-opus-5-5, budget 120000); `--progression implement` READY
- **Remaining:** the orphan compiled artifact edge case is not implemented (no AC)
- **Author:** spec-fix (Claude Opus 5.5)

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
