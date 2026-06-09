---
title: "Command Validation Hardening Implementation"
feature: 048-command-validation-hardening
status: Implemented
updated: 2026-05-18
---

# Implementation - Command Validation Hardening

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `validator/command_registry.py` | `FR-001` | ✅ Implemented | 2026-05-18 |
| FR-002 | `validator/command_audit.py`, `validator/cli_commands/command_audit_cmd.py` | `FR-002` | ✅ Implemented | 2026-05-18 |
| FR-003 | `validator/cli_commands/goal_cmd.py` | `FR-003` | ✅ Implemented | 2026-05-18 |
| FR-004 | `system/anti-drift-block.md` | `FR-004` | ✅ Implemented | 2026-05-18 |
| FR-005 | `.agent-sync/skills/*/expectations.md`, `validator/command_audit.py` | `FR-005` | ✅ Implemented | 2026-05-18 |
| FR-006 | `scripts/check-coherence.sh` | `FR-006` | ✅ Implemented | 2026-05-18 |
| FR-007 | `validator/cli_commands/utility_cmd.py` | `FR-007` | ✅ Implemented | 2026-05-18 |
| FR-008 | `validator/cli_commands/utility_cmd.py`, `scripts/play-coverage.sh` | `FR-008` | ✅ Implemented | 2026-05-18 |
| FR-009 | `validator/cli_commands/utility_cmd.py` | `FR-009` | ✅ Implemented | 2026-05-18 |
| FR-010 | `.agent-sync/skills/spec-hooks/SKILL.md`, `.agent-sync/skills/spec-init/SKILL.md`, `system/hooks.md`, `system/spec-system.md`, `.agent-sync/rules/livespec/commands.md`, `scripts/init.sh` | `FR-010` | ✅ Implemented | 2026-05-18 |
| FR-011 | `tests/test_command_audit_cli.py`, `tests/test_command_registry.py` | `FR-011` | ✅ Implemented | 2026-05-18 |
| FR-012 | `migrations/14/migrate.md`, `scripts/migrate-command-validation.sh` | `FR-012` | ✅ Implemented | 2026-05-18 |
| FR-013 | `validator/command_registry.py` | `FR-013` | ✅ Implemented | 2026-05-18 |

## Acceptance Criteria Mapping

| AC | Test File / Command | Status |
|---|---|---|
| AC-001 | `tests/test_command_registry.py` | ✅ |
| AC-002 | `python3 -m validator.cli command-audit --repo . --json` | ✅ |
| AC-003 | `python3 -m validator.cli command-audit --repo . --json` | ✅ |
| AC-004 | `bash scripts/check-coherence.sh` | ✅ |
| AC-005 | `tests/test_command_audit_cli.py` | ✅ |
| AC-006 | `bash scripts/check-coherence.sh` | ✅ |
| AC-007 | `tests/test_visual_implementation_gate.py` | ✅ |
| AC-008 | `tests/test_command_audit_cli.py` | ✅ |
| AC-009 | `tests/test_status_play_conventions_cli.py` | ✅ |
| AC-010 | `tests/test_status_play_conventions_cli.py` | ✅ |
| AC-011 | `python3 -m validator.cli command-audit --repo . --naming-policy hyphenated --json` | ✅ |
| AC-012 | `tests/integration/test_migration_v14_v15.py` | ✅ |
| AC-013 | `python3 -m pytest -q` | ✅ |

## Files Created/Modified

- Created `validator/command_registry.py`, `validator/command_audit.py`, `validator/cli_commands/command_audit_cmd.py`, `validator/cli_commands/utility_cmd.py`.
- Updated `validator/cli_commands/goal_cmd.py`, `validator/command_registry.py`, `validator/integrations.py`, `validator/hooks_cli.py`, `validator/hook_resolver.py`.
- Updated command docs, expectations, routing docs, coherence script, play-coverage wrapper, migrations, and tests.

## Verification

- `python3 -m pytest -q` -> 1506 passed, 32 skipped.
- `python3 -m validator.cli command-audit --repo . --naming-policy hyphenated --json` -> score 5, failed 0.
- `bash scripts/check-coherence.sh` -> All checks passed.
- `python3 -m validator.cli validate .specs/features/048-command-validation-hardening --format compact` -> 100/100 for all feature artifacts.
- `python3 -m ruff check ...` could not run: `No module named ruff`.
