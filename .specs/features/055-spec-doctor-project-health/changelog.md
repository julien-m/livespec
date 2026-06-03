# Changelog — 055 Spec Doctor Project Health

## 2026-06-03 — [Bugfix]: Add downstream migration for spec-doctor

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** `migrations/18/migrate.md`, `VERSION`, `tests/integration/test_migration_v18_agent_sync.py`
- **Docs modified:** `implementation.md`
- **AC impacted:** AC-014
- **Author:** Codex

## 2026-06-03 — [Check]: Spec-code alignment verified

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** `validator/goal_contracts.py`, `tests/test_goal_contracts.py`
- **Checks modified:** `checks/2026-06-03.md`
- **Coverage:** 26/26 verified (100%), 0 partial, 0 missing
- **Report:** `checks/2026-06-03.md`
- **AC impacted:** AC-001 through AC-014 verified
- **Author:** Codex

## 2026-06-02 — [Feature]: Implement project doctor command

- **Type:** Feature
- **Spec modified:** Yes (status/branch metadata)
- **Code modified:** `validator/doctor/*`, `validator/cli_commands/doctor_cmd.py`, `validator/cli_commands/__init__.py`, `tests/test_doctor.py`
- **Docs modified:** `README.md`, `.agent-sync/skills/spec-doctor/SKILL.md`, `.agent-sync/skills/spec-doctor/expectations.md`
- **AC impacted:** AC-001 through AC-014
- **Author:** Codex
