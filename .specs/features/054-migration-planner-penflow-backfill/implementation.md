---
title: "Migration Planner and Penflow Backfill Implementation"
feature: "054-migration-planner-penflow-backfill"
---

# Implementation - 054-migration-planner-penflow-backfill

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `validator/migration_planner.py` | Module-level `@spec FR-001` | Implemented | 2026-06-17 |
| FR-002 | `validator/migration_planner.py` | `_parse_manifest()` `@spec FR-002` | Implemented | 2026-06-01 |
| FR-003 | `validator/migration_planner.py` | `_pending_replacements()` `@spec FR-003` | Implemented | 2026-06-01 |
| FR-004 | `validator/migration_planner.py` | `_pending_replacements()` `@spec FR-004` | Implemented | 2026-06-01 |
| FR-005 | `validator/cli_commands/migrate_cmd.py`, `validator/cli_commands/__init__.py` | `plan_command()` `@spec FR-005` | Implemented | 2026-06-01 |
| FR-006 | `.agent-sync/skills/spec-migrate/SKILL.md` | Step 3 planner docs | Implemented | 2026-06-01 |
| FR-007 | `migrations/17/migrate.md`, `VERSION` | Migration 17 manifest | Implemented | 2026-06-01 |
| FR-008 | `scripts/migrate-penflow-backfill.py` | `build_report()` `@spec FR-008` | Implemented | 2026-06-01 |
| FR-009 | `scripts/migrate-penflow-backfill.py` | `build_report()` `@spec FR-009` | Implemented | 2026-06-01 |
| FR-010 | `scripts/migrate-penflow-backfill.py` | `build_report()` `@spec FR-010` | Implemented | 2026-06-01 |
| FR-011 | `scripts/migrate-penflow-backfill.py` | `build_report()` `@spec FR-011` | Implemented | 2026-06-01 |
| FR-012 | `scripts/migrate-penflow-backfill.py` | `build_report()` `@spec FR-012` | Implemented | 2026-06-01 |
| FR-013 | [validator/version_guard.py](../../../validator/version_guard.py), [validator/cli.py](../../../validator/cli.py), [scripts/migrate.sh](../../../scripts/migrate.sh), [.specs/spec-system.md](../../spec-system.md) | Blocking migration guard callback with internal migration-runner bypass | Implemented | 2026-06-17 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_migration_planner.py::test_migrate_plan_cli_outputs_json` | Implemented |
| AC-002 | `tests/test_migration_planner.py::test_linear_plan_is_unchanged_without_metadata` | Implemented |
| AC-003 | `tests/test_migration_planner.py::test_replaces_when_unapplied_skips_pending_old_migration` | Implemented |
| AC-004 | `tests/test_migration_planner.py::test_already_applied_replaced_migration_is_not_removed` | Implemented |
| AC-005 | `tests/test_migration_planner.py::test_invalid_restore_points_are_reported` | Implemented |
| AC-006 | `tests/test_migration_planner.py::test_invalid_frontmatter_reference_fails_clearly` | Implemented |
| AC-007 | `tests/test_penflow_contract_command_contract.py::test_spec_migrate_documents_planner_and_penflow_backfill_metadata` | Implemented |
| AC-008 | `tests/test_penflow_contract_command_contract.py::test_spec_migrate_documents_planner_and_penflow_backfill_metadata` | Implemented |
| AC-009 | `tests/test_penflow_backfill_migration.py::test_penflow_backfill_noops_when_workspace_complete` | Implemented |
| AC-010 | `tests/test_penflow_backfill_migration.py::test_penflow_backfill_noops_when_workspace_complete` | Implemented |
| AC-011 | `tests/test_penflow_backfill_migration.py::test_penflow_backfill_blocks_absent_runtime_without_fake_penflow` | Implemented |
| AC-012 | `tests/test_penflow_backfill_migration.py::test_penflow_backfill_reports_legacy_design_ui_pen_without_promoting_it` | Implemented |
| AC-013 | `tests/test_penflow_backfill_migration.py::test_penflow_backfill_creates_no_secondary_pen_files` | Implemented |
| AC-014 | `tests/test_version_guard.py` | Implemented |

## Files Created/Modified

| File | Purpose |
|---|---|
| `validator/migration_planner.py` | Parses migration frontmatter and computes metadata-aware apply/skip/restore-point plans |
| `validator/cli_commands/migrate_cmd.py` | Adds `livespec migrate plan` JSON/human CLI |
| `validator/cli_commands/__init__.py` | Registers the migrate command group |
| `migrations/17/migrate.md` | Adds Penflow backfill migration metadata and DSL |
| `scripts/migrate-penflow-backfill.py` | Writes deterministic Penflow backfill reports without unsafe generation |
| `.agent-sync/skills/spec-migrate/SKILL.md` | Documents planner-first `/spec-migrate` execution |
| `VERSION` | Bumps LiveSpec target version to 17 |
| `tests/test_migration_planner.py` | Planner unit and CLI tests |
| `tests/test_penflow_backfill_migration.py` | Migration 17 behavior tests |
| `tests/test_penflow_contract_command_contract.py` | Command documentation contract regression |
| [validator/version_guard.py](../../../validator/version_guard.py) | Blocks stale initialized projects before normal LiveSpec command execution |
| [scripts/migrate.sh](../../../scripts/migrate.sh) | Marks internal migration subprocesses so migration repairs are not self-blocked by the stale-project guard |
| [tests/test_version_guard.py](../../../tests/test_version_guard.py) | Stale/up-to-date/missing-version/help/migrate guard tests |

## Verification

- `pytest tests/test_migration_planner.py tests/test_penflow_backfill_migration.py tests/test_penflow_contract_command_contract.py -q` - 34 passed.
- `python3 -m pytest tests/test_version_guard.py -q` - 11 passed.
- `/tmp/livespec-cov-venv-32421/bin/python -m pytest tests/integration/ -m level_3a -v --tb=short` - 75 passed after adding the internal migration-runner bypass.
