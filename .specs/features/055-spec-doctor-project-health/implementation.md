---
feature: 055-spec-doctor-project-health
title: Spec Doctor Project Health
status: Implemented
updated: 2026-06-02
---

# Implementation — 055 Spec Doctor Project Health

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `validator/cli_commands/doctor_cmd.py` | `@spec FR-001: Public doctor CLI` | ✅ Implemented | 2026-06-02 |
| FR-002 | `.agent-sync/skills/spec-doctor/SKILL.md` | `Command: /spec-doctor` | ✅ Implemented | 2026-06-02 |
| FR-003 | `validator/doctor/models.py`, `validator/doctor/scanner.py`, `validator/doctor/report.py` | `@spec FR-003: Doctor package orchestration` | ✅ Implemented | 2026-06-02 |
| FR-004 | `validator/doctor/scanner.py` | `@spec FR-004: Reuse coherence engine` | ✅ Implemented | 2026-06-02 |
| FR-005 | `validator/doctor/scanner.py` | `@spec FR-005: Implementation map scan` | ✅ Implemented | 2026-06-02 |
| FR-006 | `validator/doctor/scanner.py` | `@spec FR-006: Runner inclusion scan` | ✅ Implemented | 2026-06-02 |
| FR-007 | `validator/doctor/scanner.py` | `@spec FR-007: Hook enforcement scan` | ✅ Implemented | 2026-06-02 |
| FR-008 | `validator/doctor/scanner.py` | `@spec FR-008: Visual evidence scan` | ✅ Implemented | 2026-06-02 |
| FR-009 | `validator/cli_commands/doctor_cmd.py`, `validator/doctor/report.py` | `@spec FR-009: Report format selection` | ✅ Implemented | 2026-06-02 |
| FR-010 | `validator/doctor/scanner.py` | `@spec FR-010: Journey checks optional` | ✅ Implemented | 2026-06-02 |
| FR-011 | `README.md`, `.agent-sync/skills/spec-doctor/expectations.md` | README command row and expectations contract | ✅ Implemented | 2026-06-02 |
| FR-012 | `tests/test_doctor.py` | `test_doctor_*` CLI coverage | ✅ Implemented | 2026-06-02 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_doctor.py::test_doctor_fix_plan_is_read_only` | ✅ Implemented |
| AC-002 | `tests/test_doctor.py::test_doctor_json_reports_stale_mapping_missing_test_and_hook` | ✅ Implemented |
| AC-003 | `tests/test_doctor.py::test_doctor_json_reports_stale_mapping_missing_test_and_hook` | ✅ Implemented |
| AC-004 | `tests/test_doctor.py::test_doctor_json_reports_stale_mapping_missing_test_and_hook` | ✅ Implemented |
| AC-005 | `tests/test_doctor.py::test_doctor_strict_promotes_runner_warning_to_failure` | ✅ Implemented |
| AC-006 | `tests/test_doctor.py::test_doctor_json_reports_stale_mapping_missing_test_and_hook` | ✅ Implemented |
| AC-007 | `tests/test_doctor.py::test_doctor_lifecycle_allows_linked_supersession_only` | ✅ Implemented |
| AC-008 | `tests/test_doctor.py::test_doctor_lifecycle_allows_linked_supersession_only` | ✅ Implemented |
| AC-009 | `tests/test_doctor.py::test_doctor_fix_plan_is_read_only` | ✅ Implemented |
| AC-010 | `tests/test_doctor.py::test_doctor_json_reports_stale_mapping_missing_test_and_hook` | ✅ Implemented |
| AC-011 | `tests/test_doctor.py::test_doctor_fix_plan_is_read_only` | ✅ Implemented |
| AC-012 | `tests/test_doctor.py::test_doctor_apply_cleanup_refuses_destructive_actions` | ✅ Implemented |
| AC-013 | `tests/test_doctor.py::test_doctor_strict_promotes_runner_warning_to_failure` | ✅ Implemented |
| AC-014 | `tests/test_doctor.py::test_spec_doctor_skill_distinguishes_doctor_from_validate` | ✅ Implemented |

## Files Created/Modified

| File | Description |
|---|---|
| `validator/doctor/models.py` | Doctor status, finding, cleanup action, and report models. |
| `validator/doctor/scanner.py` | Coherence, mapping, runner, hook, lifecycle, and visual orphan scanner. |
| `validator/doctor/report.py` | JSON and terminal report renderers. |
| `validator/doctor/__init__.py` | Doctor package public surface. |
| `validator/cli_commands/doctor_cmd.py` | `livespec doctor` Typer command. |
| `validator/cli_commands/__init__.py` | Registers the doctor command. |
| `tests/test_doctor.py` | Focused CLI tests for doctor behavior. |
| `.agent-sync/skills/spec-doctor/SKILL.md` | Agent-facing `$spec-doctor` / `/spec-doctor` command docs. |
| `.agent-sync/skills/spec-doctor/expectations.md` | Verify-output contract for command audit. |
| `README.md` | Command list and validator docs updated. |
