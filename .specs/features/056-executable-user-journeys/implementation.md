---
feature: 056-executable-user-journeys
title: Executable User Journeys
status: Implemented
updated: 2026-06-02
---

# Implementation — 056 Executable User Journeys

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `system/testing/user-journeys.md` | Canonical format reference | ✅ Implemented | 2026-06-02 |
| FR-002 | `validator/journeys/models.py`, `validator/journeys/validator.py` | `@spec FR-002: Journey validation package` | ✅ Implemented | 2026-06-02 |
| FR-003 | `validator/cli_commands/journey_cmd.py`, `validator/cli_commands/__init__.py` | `@spec FR-003: Journey CLI` | ✅ Implemented | 2026-06-02 |
| FR-004 | `validator/journeys/paths.py` | `@spec FR-004: Canonical journey source path` | ✅ Implemented | 2026-06-02 |
| FR-005 | `validator/journeys/validator.py` | `@spec FR-005: v1 journey actions` | ✅ Implemented | 2026-06-02 |
| FR-006 | `validator/journeys/compiler.py` | `@spec FR-006: Playwright journey compiler` | ✅ Implemented | 2026-06-02 |
| FR-007 | `validator/journeys/compiler.py` | `@spec FR-007: XCUITest journey compiler` | ✅ Implemented | 2026-06-02 |
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
| AC-003 | `tests/test_journeys.py::test_compile_generates_playwright_with_source_hash` | ✅ Implemented |
| AC-004 | `tests/test_journeys.py::test_wait_without_until_or_reason_is_warning` | ✅ Implemented |
| AC-005 | `tests/test_journeys.py::test_compile_generates_playwright_with_source_hash` | ✅ Implemented |
| AC-006 | `tests/test_journeys.py::test_compile_generates_xcuitest_for_ios_and_watchos` | ✅ Implemented |
| AC-007 | `tests/test_journeys.py::test_compile_generates_xcuitest_for_ios_and_watchos` | ✅ Implemented |
| AC-008 | `tests/test_journeys.py::test_compile_generates_playwright_with_source_hash` | ✅ Implemented |
| AC-009 | `tests/test_journeys.py::test_doctor_reports_stale_and_removed_ac` | ✅ Implemented |
| AC-010 | `tests/test_journeys.py::test_doctor_reports_stale_and_removed_ac` | ✅ Implemented |
| AC-011 | `tests/test_journeys.py::test_manual_disabled_and_executable_categories_are_reported` | ✅ Implemented |
| AC-012 | `.agent-sync/skills/spec-feature/SKILL.md` | ✅ Implemented |
| AC-013 | `tests/test_journeys.py::test_journey_validate_rejects_unsupported_target` | ✅ Implemented |
| AC-014 | `tests/test_journeys.py::test_manual_disabled_and_executable_categories_are_reported` | ✅ Implemented |
| AC-015 | `tests/test_journeys.py::test_manual_journey_requires_reason` | ✅ Implemented |

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
| `.agent-sync/skills/spec-specify/SKILL.md` | Journey proposal guidance. |
| `.agent-sync/skills/spec-feature/SKILL.md` | Compile-before-functional-tests guidance. |
| `.agent-sync/skills/spec-test/SKILL.md` | Separate journey audit/reporting guidance. |
