---
title: Conventions Migration Docs Implementation
feature: 065-conventions-migration-docs
status: Implemented
created: 2026-06-13
updated: 2026-06-25
---

<!-- @spec FR-001: Migration v22 manifest and wrappers — .specs/features/065-conventions-migration-docs/spec.md#fr-001 -->
<!-- @spec FR-003: Conventions enforcement reference — .specs/features/065-conventions-migration-docs/spec.md#fr-003 -->
<!-- @spec FR-006: Agent instruction conventions commands — .specs/features/065-conventions-migration-docs/spec.md#fr-006 -->

# Implementation — Conventions Migration Docs

## Summary

Implemented migration v22 and the conventions enforcement documentation surface:

- Migration v22 manifest wires agent-sync refresh, gates init, rulebook compile, scaffold, and first non-blocking verify.
- Four migration wrapper scripts are executable, idempotent/no-op safe for missing prerequisites, and use `set -euo pipefail`.
- `system/conventions-enforcement.md` documents the three engines, gates/rulebook schemas, human operations, anti-bypass locks, and CLI reference.
- README, `system/spec-system.md`, `.specs/spec-system.md`, `CLAUDE.md`, and `AGENTS.md` now surface conventions enforcement commands and quality gates.

## Requirement Mapping

| Requirement | File(s) | Status | Last Verified |
|---|---|---|---|
| FR-001 | **Read** [`migrations/22/migrate.md`](../../../migrations/22/migrate.md), [`scripts/migrate-conventions-gates-init.sh`](../../../scripts/migrate-conventions-gates-init.sh), [`scripts/migrate-conventions-compile.sh`](../../../scripts/migrate-conventions-compile.sh), [`scripts/migrate-conventions-scaffold.sh`](../../../scripts/migrate-conventions-scaffold.sh), and [`scripts/migrate-conventions-first-verify.sh`](../../../scripts/migrate-conventions-first-verify.sh). | ✅ Implemented | 2026-06-13 |
| FR-002 | **Read** [`scripts/migrate-conventions-gates-init.sh`](../../../scripts/migrate-conventions-gates-init.sh), [`scripts/migrate-conventions-compile.sh`](../../../scripts/migrate-conventions-compile.sh), [`scripts/migrate-conventions-scaffold.sh`](../../../scripts/migrate-conventions-scaffold.sh), and [`scripts/migrate-conventions-first-verify.sh`](../../../scripts/migrate-conventions-first-verify.sh). | ✅ Implemented | 2026-06-13 |
| FR-003 | **Read** [`system/conventions-enforcement.md`](../../../system/conventions-enforcement.md). | ✅ Implemented | 2026-06-13 |
| FR-004 | **Read** [`README.md`](../../../README.md). | ✅ Implemented | 2026-06-13 |
| FR-005 | **Read** [`system/spec-system.md`](../../../system/spec-system.md) and [`.specs/spec-system.md`](../../spec-system.md). | ✅ Implemented | 2026-06-13 |
| FR-006 | **Read** [`CLAUDE.md`](../../../CLAUDE.md) and [`AGENTS.md`](../../../AGENTS.md). | ✅ Implemented | 2026-06-13 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001, AC-002 | **Read** [`tests/test_conventions_migration_docs.py`](../../../tests/test_conventions_migration_docs.py). | ✅ Covered |
| AC-003 through AC-006 | **Read** [`tests/test_conventions_migration_docs.py`](../../../tests/test_conventions_migration_docs.py). | ✅ Covered |
| AC-007 through AC-011 | **Read** [`tests/test_conventions_migration_docs.py`](../../../tests/test_conventions_migration_docs.py). | ✅ Covered |
| AC-012 through AC-014 | Documentation updated directly in README, spec-system, CLAUDE, and AGENTS. | ✅ Implemented |
