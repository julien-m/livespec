# Changelog - Cross-Feature User Journeys v2

## 2026-06-07 - Fix: Migration 19 and README entrypoint

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** `VERSION`, `migrations/19/migrate.md`, `tests/integration/test_migration_v19_user_journeys.py`, `README.md`, `.specs/changelog.md`, `.specs/README.md`, `.specs/features/057-cross-feature-user-journeys-v2/implementation.md`, `.specs/features/057-cross-feature-user-journeys-v2/progress.md`
- **Reason:** Existing v18 projects needed a concrete migration point to re-run agent asset sync and install `$spec-journey` plus User Journeys v2 guidance.
- **Verification:** `pytest tests/integration/test_migration_v19_user_journeys.py tests/test_journey_v2_docs_skills.py tests/test_command_registry.py tests/test_agent_sync_layout.py -q`
- **Author:** codex

## 2026-06-05 - Fix: Check gaps closed

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** `.specs/features/057-cross-feature-user-journeys-v2/implementation.md`, `.agent-sync/skills/spec-test/SKILL.md`, `.agent-sync/skills/spec-feature/SKILL.md`, `.agent-sync/skills/spec-specify/SKILL.md`, `validator/journeys/*.py`, `validator/cli_commands/journey_cmd.py`, `validator/cli_commands/test_cmd.py`, `tests/test_journey_v2_impact.py`
- **Gaps closed:** GAP-001, GAP-002, GAP-003, GAP-004, convention gaps, AC-020 evidence gap
- **Remaining:** None for `checks/2026-06-04.md`; project-wide pre-existing doctor/tree warnings remain out of scope.
- **Report:** `checks/2026-06-05.md`
- **Author:** spec-fix

## 2026-06-04 - Check: Spec-code alignment verified with gaps

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **Coverage:** Functional tests pass, but canonical mapping is incomplete: 0/41 FR and 0/46 AC are mapped in `implementation.md`.
- **Gaps:** Missing implementation map, stale v1 journey wording in `$spec-test`/`$spec-specify`, compile-at-test wording in `$spec-feature`, and journey convention gaps.
- **Report:** `checks/2026-06-04.md`
- **Author:** codex

## 2026-06-04 - Implemented

- Added global v2 journey schema, path helpers, index, validation, history/decision governance, backlinks, and doctor findings.
- Added assignment/bootstrap services, JourneyImpactAnalyzer, compiled manifests, compiler registry/capabilities, Playwright/XCUITest/Maestro output, pytest/cargo unsupported handling, and compiled-only runner semantics.
- Added `livespec journey validate|compile|run|impact|migrate|list|inspect`, v1 migration, native visual checks, LLM visual contracts/evaluator, and `$spec-journey` docs/expectations.
- Updated `livespec test`, spec skills, system journey docs, command routing, and init command list.
- Verified with targeted journey tests, full non-integration suite, changed-file lint/format checks, and Pyright.
