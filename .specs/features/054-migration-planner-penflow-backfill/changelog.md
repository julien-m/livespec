# Changelog - 054-migration-planner-penflow-backfill

## 2026-06-01 — [Spec Update]: Feature specified and planned

- **Type:** Spec Update
- **Spec modified:** Yes (initial spec and plan)
- **Code modified:** None
- **AC impacted:** AC-001..AC-013
- **Author:** codex

## 2026-06-01 — [Feature]: Migration planner and Penflow backfill implemented

- **Type:** Feature
- **Spec modified:** Yes (status and implementation mapping)
- **Code modified:** `validator/migration_planner.py`, `validator/cli_commands/migrate_cmd.py`, `validator/cli_commands/__init__.py`, `migrations/17/migrate.md`, `scripts/migrate-penflow-backfill.py`, `.agent-sync/skills/spec-migrate/SKILL.md`, `VERSION`
- **AC impacted:** AC-001..AC-013
- **Author:** codex

## 2026-06-17 — [Bugfix]: Block stale projects before normal commands

- **Type:** Bugfix
- **Spec modified:** Yes (AC-014, FR-013)
- **Code modified:** [validator/version_guard.py](../../../validator/version_guard.py), [validator/cli.py](../../../validator/cli.py), [scripts/migrate.sh](../../../scripts/migrate.sh), [.specs/spec-system.md](../../spec-system.md), [tests/test_version_guard.py](../../../tests/test_version_guard.py)
- **AC impacted:** AC-014
- **Author:** codex
