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
