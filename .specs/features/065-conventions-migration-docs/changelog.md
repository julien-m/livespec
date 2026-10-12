# Changelog — Conventions Migration Docs

## 2026-06-13 — [Feature]: Initial spec and plan

- **Type:** Feature
- **Spec modified:** Yes (created feature spec, plan, progress)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-014
- **Author:** Codex

## 2026-06-13 — [Feature]: Migration v22 and conventions enforcement docs implemented

- **Type:** Feature
- **Spec modified:** Yes (status, progress, implementation mapping)
- **Code modified:** Yes (migration scripts, migration manifest, system docs, README, agent docs)
- **AC impacted:** AC-001 through AC-014
- **Author:** Codex

## 2026-06-13 — [Bugfix]: Make migration v22 advisory and version last

- **Type:** Bugfix
- **Spec modified:** Yes (AC-001, AC-003 through AC-006)
- **Code modified:** migrations/22/migrate.md, scripts/migrate-conventions-*.sh, tests/test_conventions_migration_docs.py
- **AC impacted:** AC-001, AC-003, AC-004, AC-005, AC-006
- **Author:** Codex

## 2026-10-12 — [Refactor]: Migration v22 exercised end to end

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_conventions_migration_docs.py
- **AC impacted:** None (AC-001..AC-006 now behavioral)
- **Author:** Claude Code (test-suite cleanup, lot 1)
- migrate.sh runs migration 22 against three synthetic projects with a recording `livespec` that fails: each step runs only when its inputs exist, failures stay advisory and the version becomes 22. Static RUN/text checks replaced; the SET_VERSION ordering and enforcement-doc section checks kept.
