---
feature: 056-executable-user-journeys
status: Done
updated: 2026-06-02
---

# Progress — 056 Executable User Journeys

| Step | Status | Files | Test |
|---|---|---|---|
| 1 | Done | `tests/test_journeys.py` | `pytest tests/test_journeys.py -q` PASS |
| 2 | Done | `validator/journeys/*` | Focused Ruff/Pyright PASS |
| 3 | Done | `validator/cli_commands/journey_cmd.py`, `validator/cli_commands/__init__.py` | CLI tests PASS |
| 4 | Done | `validator/doctor/scanner.py` | Doctor drift test PASS |
| 5 | Done | `validator/cli_commands/test_cmd.py` | Category report test PASS |
| 6 | Done | `system/testing/user-journeys.md`, `.agent-sync/skills/*/SKILL.md` | Markdown checked by review |

## Verification

- `pytest tests/test_journeys.py -q` → 7 passed.
- `ruff check validator/journeys validator/cli_commands/journey_cmd.py validator/cli_commands/test_cmd.py validator/cli_commands/__init__.py validator/doctor/scanner.py tests/test_journeys.py` → pass.
- `pyright validator/journeys validator/cli_commands/journey_cmd.py validator/cli_commands/test_cmd.py validator/doctor/scanner.py tests/test_journeys.py` → 0 errors.

## Fix checkpoint — 2026-10-12 (`/spec-fix --ac AC-004`, AC-015, plus AC-003, FR-005, FR-007)

| Step | Status | Files | Test |
|---|---|---|---|
| 9 | Done | `tests/test_journeys_wait_manual.py`, `tests/test_journeys_select_targets.py` | RED first: 20 failing, then green |
| 10 | Done | `validator/journeys/schema.py` | `TestFixedWaitWarning::test_malformed_wait_is_rejected` |
| 11 | Done | `validator/journeys/validator.py` | `TestFixedWaitWarning`, `TestManualReason` |
| 12 | Done | `validator/journeys/capabilities.py`, `validator/journeys/compiler.py` | `TestBoundedWaitCompilation`, `TestSelect` |
| 13 | Done | `validator/journeys/paths.py`, `validator/journeys/compiler.py`, `validator/cli_commands/journey_cmd.py`, `validator/exceptions.py` | `TestXcuitestDestination` |
| 14 | Done | `validator/journeys/runner.py` | `TestManualReason::test_run_reports_missing_reason_instead_of_skipping` |
| 15 | Done | `validator/journeys/migration.py`, `system/testing/user-journeys.md` | `test_v1_migration_keeps_manual_reason` |
| 16 | Done | 057/060 journey tests (fixture `*UITests` directory) | journey suites 172 passed |

Verification: full unit suite 3767 passed, 25 skipped (with the pinned Penflow CLI); ruff, ruff format, pyright validator 0 errors; conventions verify `--feature repo` PASS.
