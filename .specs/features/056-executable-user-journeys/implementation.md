---
feature: 056-executable-user-journeys
title: Executable User Journeys
status: Implemented
updated: 2026-10-12
---

# Implementation — 056 Executable User Journeys

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `system/testing/user-journeys.md` | Canonical format reference | ✅ Implemented | 2026-06-02 |
| FR-002 | `validator/journeys/models.py`, `validator/journeys/validator.py` | `@spec FR-002: Journey validation package` | ✅ Implemented | 2026-06-02 |
| FR-003 | `validator/cli_commands/journey_cmd.py`, `validator/cli_commands/__init__.py` | `@spec FR-003: Journey CLI` | ✅ Implemented | 2026-06-02 |
| FR-004 | `validator/journeys/paths.py` | `@spec FR-004: Canonical journey source path` | ✅ Implemented | 2026-06-02 |
| FR-005 | `validator/journeys/schema.py`, `validator/journeys/capabilities.py`, `validator/journeys/compiler.py` | `@spec FR-005: select on Playwright only` | ✅ Implemented (`select` compiles on Playwright; XCUITest/Maestro refuse it) | 2026-10-12 |
| FR-006 | `validator/journeys/compiler.py` | `@spec FR-006: Playwright journey compiler` | ✅ Implemented | 2026-06-02 |
| FR-007 | `validator/journeys/compiler.py`, `validator/journeys/paths.py`, `validator/cli_commands/journey_cmd.py`, `validator/exceptions.py` | `@spec FR-007, AC-006, AC-007: project-resolved XCUITest destination` | ✅ Implemented (destination from `surfaces.yaml` `testDir` or the unique `*UITests` directory; no hardcoded project name) | 2026-10-12 |
| FR-008 | `validator/journeys/compiler.py` | `@spec FR-008: Maestro journey compiler` | ✅ Implemented | 2026-06-02 |
| FR-009 | `validator/journeys/compiler.py`, `validator/journeys/scanner.py` | `@spec FR-009: Source hash marker` | ✅ Implemented | 2026-06-02 |
| FR-010 | `.agent-sync/skills/spec-specify/SKILL.md` | Journey proposal instruction | ✅ Implemented | 2026-06-02 |
| FR-011 | `.agent-sync/skills/spec-feature/SKILL.md` | Journey compile-before-test instruction | ✅ Implemented | 2026-06-02 |
| FR-012 | `validator/cli_commands/test_cmd.py`, `.agent-sync/skills/spec-test/SKILL.md` | `@spec FR-012: Separate journey reporting` | ✅ Implemented | 2026-06-02 |
| FR-013 | `validator/doctor/scanner.py`, `validator/journeys/scanner.py` | `@spec FR-013: Journey scan handoff` | ✅ Implemented | 2026-06-02 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_journeys.py::test_journey_validate_accepts_valid_yaml` | ✅ Implemented |
| AC-002 | `tests/test_journeys.py::test_journey_validate_rejects_unknown_action` | ✅ Implemented |
| AC-003 | `tests/test_journeys_wait_manual.py::TestBoundedWaitCompilation::test_playwright_until`, `::test_xcuitest_until_waits_for_hittable`, `::test_maestro_until`, `::test_playwright_fixed_delay`, `::test_maestro_fixed_wait_is_refused` | ✅ Implemented (2026-10-12; the former mapping had no `wait` step) |
| AC-004 | `tests/test_journeys_wait_manual.py::TestFixedWaitWarning::test_fixed_wait_without_until_or_reason_warns`, `::test_reason_or_until_silences_warning`, `::test_blank_reason_still_warns`, `::test_malformed_wait_is_rejected` | ✅ Implemented (2026-10-12) |
| AC-005 | `tests/test_journeys.py::test_compile_generates_playwright_with_source_hash` | ✅ Implemented |
| AC-006 | `tests/test_journeys.py::test_compile_generates_xcuitest_for_ios_and_watchos`, `tests/test_journeys_select_targets.py::TestXcuitestDestination::test_unique_ios_target_directory`, `::test_several_ios_targets_are_ambiguous`, `::test_no_target_directory_is_refused`, `::test_surfaces_test_dir_overrides` | ✅ Implemented |
| AC-007 | `tests/test_journeys.py::test_compile_generates_xcuitest_for_ios_and_watchos`, `tests/test_journeys_select_targets.py::TestXcuitestDestination::test_watchos_uses_watch_target`, `::test_watchos_without_watch_target_is_refused` | ✅ Implemented |
| AC-008 | `tests/test_journeys.py::test_compile_generates_playwright_with_source_hash` | ✅ Implemented |
| AC-009 | `tests/test_journeys.py::test_doctor_reports_stale_and_removed_ac` | ✅ Implemented |
| AC-010 | `tests/test_journeys.py::test_doctor_reports_stale_and_removed_ac` | ✅ Implemented |
| AC-011 | `tests/test_journeys.py::test_manual_disabled_and_executable_categories_are_reported` | ✅ Implemented |
| AC-012 | `.agent-sync/skills/spec-feature/SKILL.md` | ✅ Implemented |
| AC-013 | `tests/test_journeys.py::test_journey_validate_rejects_unsupported_target`, `tests/test_journeys_select_targets.py::TestSelect::test_other_runners_refuse_select`, `tests/test_journeys_wait_manual.py::TestBoundedWaitCompilation::test_maestro_fixed_wait_is_refused` | ✅ Implemented |
| AC-014 | `tests/test_journeys.py::test_manual_disabled_and_executable_categories_are_reported` | ✅ Implemented |
| AC-015 | `tests/test_journeys_wait_manual.py::TestManualReason::test_manual_without_reason_fails_validation`, `::test_run_reports_missing_reason_instead_of_skipping`, `::test_manual_with_reason_is_reported_as_manual`, `tests/test_journeys_wait_manual.py::test_v1_migration_keeps_manual_reason` | ✅ Implemented (2026-10-12) |

## Files Created/Modified

| File | Description |
|---|---|
| `system/testing/user-journeys.md` | Canonical YAML reference. |
| `validator/journeys/` | Validation, compilation, paths, scanner, typed models. |
| `validator/cli_commands/journey_cmd.py` | `livespec journey validate/compile/test`. |
| `validator/cli_commands/__init__.py` | Registers `journey`. |
| `validator/cli_commands/test_cmd.py` | Adds direct/journey/manual/disabled category reporting. |
| `validator/doctor/scanner.py` | Adds journey health findings. |
| `tests/test_journeys.py` | Regression tests for validation, compilers, doctor, category reporting. |
| `validator/journeys/schema.py` | 2026-10-12: `JourneyStep.until`/`reason` with bounded-wait validation; `JourneySourceV2.manual_reason`, `is_manual`, `lacks_manual_reason`. |
| `validator/journeys/validator.py` | 2026-10-12: `wait_reason_missing` warning, `journey_manual_reason_missing` error, wait payload fields, `manual_reason` on `JourneyFile`. |
| `validator/journeys/capabilities.py`, `validator/journeys/compiler.py` | 2026-10-12: `wait` on Playwright/XCUITest/Maestro (Maestro needs `until`), `select` on Playwright, project-resolved XCUITest destination with `journey_xcuitest_target_unresolved`. |
| `validator/journeys/paths.py`, `validator/exceptions.py` | 2026-10-12: `resolve_xcuitest_target_dir`; removed the unused hardcoded `compiled_artifact_path`; `XcuitestTargetUnresolvedError`. |
| `validator/journeys/runner.py`, `validator/journeys/migration.py` | 2026-10-12: manual journey without reason reported as an error by `journey run`; v1 migration keeps `manual_reason`. |
| `tests/test_journeys_wait_manual.py`, `tests/test_journeys_select_targets.py` | 2026-10-12: TDD tests for AC-003, AC-004, AC-015, FR-005 and FR-007. |
| `.agent-sync/skills/spec-specify/SKILL.md` | Journey proposal guidance. |
| `.agent-sync/skills/spec-feature/SKILL.md` | Compile-before-functional-tests guidance. |
| `.agent-sync/skills/spec-test/SKILL.md` | Separate journey audit/reporting guidance. |
