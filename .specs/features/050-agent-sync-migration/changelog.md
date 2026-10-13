# Changelog - Agent Sync Migration

## 2026-05-18 — [Spec Update]: Created

- **Type:** Spec Update
- **Spec modified:** Yes (initial feature spec and plan)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-012
- **Author:** codex

## 2026-05-18 — [Feature]: Agent-sync migration implemented

- **Type:** Feature
- **Spec modified:** Yes (status, implementation mapping, progress)
- **Code modified:** `.agent-sync/`, `scripts/`, `validator/`, `hooks/`, `tests/`, `system/`, `README.md`, `AGENTS.md`, `migrations/16/`, `VERSION`
- **AC impacted:** AC-001 through AC-012
- **Author:** codex

## 2026-05-18 — [Bugfix]: Restrict global bootstrap to init and migrate

- **Type:** Bugfix
- **Spec modified:** Yes (AC-006 clarification)
- **Code modified:** `scripts/install.sh`, `README.md`, `tests/test_agent_sync_scripts.py`, `tests/test_command_aliases.py`
- **AC impacted:** AC-006
- **Author:** codex

## 2026-05-18 — [Bugfix]: Ignore provider outputs and clean relative legacy links

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** `scripts/init.sh`, `scripts/migrate-agent-sync.sh`, `migrations/16/migrate.md`, `.gitignore`, tests
- **AC impacted:** AC-007
- **Author:** codex

## 2026-05-20 — [Bugfix]: Build project rules from file symlinks

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** `scripts/sync-agent-assets.sh`, `scripts/init.sh`, `.agent-sync/skills/spec-init/SKILL.md`, `migrations/16/migrate.md`, `.gitignore`, tests
- **AC impacted:** AC-004, AC-007
- **Author:** codex

## 2026-05-20 — [Bugfix]: Move project LiveSpec links to `.agent-sync.local`

- **Type:** Bugfix
- **Spec modified:** Yes (AC-007, AC-009 local-root semantics)
- **Code modified:** `scripts/sync-agent-assets.sh`, `scripts/migrate-agent-sync.sh`, `scripts/init.sh`, `.agent-sync/skills/spec-init/SKILL.md`, `migrations/16/migrate.md`, `.gitignore`, tests
- **AC impacted:** AC-007, AC-009
- **Author:** codex

## 2026-10-12 — [Refactor]: Layout and agent-sync script tests deduplicated

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_agent_sync_layout.py, tests/test_agent_sync_scripts.py, implementation.md
- **AC impacted:** AC-005, AC-006 remapped to test_agent_sync_scripts.py
- **Author:** Claude Code (test-suite cleanup, lot 1)
- The layout module owns the inventory through `discover_commands`; registry, expectations-identity and spec-migrate prose duplicates removed; script tests no longer depend on the working directory.

## 2026-10-13 — Bugfix: native quality review

- Replace the retired audit-skill call before finalization with independent native `high` review; load the same canonical protocol after each successful implementation step. Read the [protocol](../../../system/hooks/after-implement-step.md).
- Preserve convention/custom-check coverage, real reports, bounded correction loops and blocking findings without temporary staging. Read the [user-hook replacement procedure](../../../system/hooks.md#native-quality-review).
- This instruction correction does not certify application runtime or rewrite historical audit records.
