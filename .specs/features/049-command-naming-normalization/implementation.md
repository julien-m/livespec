---
title: "Command Naming Normalization Implementation"
feature: 049-command-naming-normalization
status: Implemented
updated: 2026-05-18
---

# Implementation - Command Naming Normalization

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `validator/command_registry.py` | `FR-001` | ✅ Implemented | 2026-05-18 |
| FR-002 | `validator/command_registry.py` | `FR-002` | ✅ Implemented | 2026-05-18 |
| FR-003 | `scripts/link-local.sh`, `scripts/install.sh` | `FR-003` | ✅ Implemented | 2026-05-18 |
| FR-004 | `.agent-sync/skills/*/SKILL.md`, `.agent-sync/skills/*/expectations.md`, `system/*.md`, `.agent-sync/rules/livespec/commands.md`, `AGENTS.md` | `FR-004` | ✅ Implemented | 2026-05-18 |
| FR-005 | `.agent-sync/skills/spec-verify-output/SKILL.md`, `validator/cli_commands/goal_cmd.py` | `FR-005` | ✅ Implemented | 2026-05-18 |
| FR-006 | `validator/hooks_cli.py`, `validator/hook_resolver.py`, `validator/integrations.py` | `FR-006` | ✅ Implemented | 2026-05-18 |
| FR-007 | `validator/command_audit.py` | `FR-007` | ✅ Implemented | 2026-05-18 |
| FR-008 | `migrations/15/migrate.md`, `scripts/migrate-command-naming.sh` | `FR-008` | ✅ Implemented | 2026-05-18 |
| FR-009 | `validator/command_registry.py`, `validator/expectations.py`, `validator/goal_contracts.py` | `FR-009` | ✅ Implemented | 2026-05-18 |
| FR-010 | `tests/test_command_registry.py`, `tests/test_command_aliases.py`, `tests/test_integrations.py`, `tests/test_hooks_cli.py` | `FR-010` | ✅ Implemented | 2026-05-18 |
| FR-011 | `.agent-sync/skills/spec-*`, `validator/command_audit.py`, `validator/state_files.py` | `FR-011` | ✅ Implemented | 2026-05-18 |

## Acceptance Criteria Mapping

| AC | Test File / Command | Status |
|---|---|---|
| AC-001 | `tests/test_command_registry.py` | ✅ |
| AC-002 | `tests/test_command_aliases.py` | ✅ |
| AC-003 | `tests/test_command_registry.py` | ✅ |
| AC-004 | `tests/test_command_aliases.py`, `tests/test_hooks_cli.py`, `tests/test_integrations.py` | ✅ |
| AC-005 | `tests/test_command_aliases.py` | ✅ |
| AC-006 | `grep -R --exclude-dir='__pycache__' "/spec\\.<command>" ...` leaves only legacy-alias tests/docstrings | ✅ |
| AC-007 | `tests/integration/test_migration_v14_v15.py` | ✅ |
| AC-008 | `tests/test_command_audit_cli.py` | ✅ |
| AC-009 | `tests/test_command_registry.py` | ✅ |
| AC-010 | `python3 -m validator.cli command-audit --repo . --naming-policy hyphenated --json` | ✅ |
| AC-011 | `tests/test_command_registry.py`, `tests/test_command_audit_cli.py` | ✅ |

## Files Created/Modified

- Added hyphenated canonical slash names and dotted legacy aliases in the command registry.
- Updated local and bootstrap linking to create `spec-*.md` links while preserving `spec.*.md` aliases.
- Updated `verify-output`, `run finalize`, hooks, and integrations to normalize aliases before lookup.
- Updated command docs and generated references to prefer `/spec-*`.
- Added Migration 15.
- Renamed command source files and expectation sidecars to `.agent-sync/skills/spec-*.md` and `.agent-sync/skills/spec-*.expectations.md`.
- Completed the agent-sync-era cleanup so active skills, agents, docs, CLI help, and state-file `owner_command` values use `spec-*`.
- Added state-file validation and migration coverage for legacy dotted `owner_command` values.

## Verification

- `python3 -m pytest -q` -> 1509 passed, 32 skipped.
- `python3 -m validator.cli command-audit --repo . --naming-policy hyphenated --json` -> score 5, failed 0.
- `bash scripts/check-coherence.sh` -> All checks passed.
- `python3 -m validator.cli validate .specs/features/049-command-naming-normalization --format compact` -> 100/100 for all feature artifacts.
- `python3 -m ruff check ...` could not run: `No module named ruff`.
