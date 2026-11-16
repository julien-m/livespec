# Implementation: Existing Test Journeys

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `validator/journeys/schema.py`, `models.py`, `validator.py` | FR-001 execution modes | Implemented | 2026-11-16 |
| FR-002 | `validator/cli_commands/journey_cmd.py`, `journeys/impact.py`, `scanner.py`, `requirements.py` | Existing reference catalogue/impact | Implemented | 2026-11-16 |
| FR-003 | `journeys/compiler.py`, `runner.py`, `existing_tests.py`, `vitest-reference.mjs`, `pyproject.toml` | FR-003 preserve existing tests; FR-002 exact suite execution | Implemented | 2026-11-16 |
| FR-004 | `journeys/runner.py`, `cli_commands/journey_cmd.py` | FR-004 reuse and explicit outcomes | Implemented | 2026-11-16 |
| FR-005 | Guide and README | Read [the adoption guide](../../../system/testing/existing-test-journeys.md) | Implemented | 2026-11-16 |

## Acceptance Criteria Mapping

| AC | Evidence | Status |
|---|---|---|
| AC-001 | `tests/test_journey_existing_tests.py`: mixed/unsafe references, missing and symlink files | Verified |
| AC-002 | Catalogue/CLI/config-impact/deleted-file tests, definition-format tests and installed-wheel CLI | Verified |
| AC-003 | Real original pytest fixture/config and Playwright/Vitest execution; unchanged bytes/no generated tests | Verified |
| AC-004 | Exact sibling exclusion in real Node runners; all-skipped/invalid-report/retry checks; original suite assertions retained | Verified |
| AC-005 | Real successful and failed duplicate references execute once, with reused mapping | Verified |
| AC-006 | Empty catalogue/filter, dry-run no spawn, planned IDs and argv; prior generated dry-run assertion corrected | Verified |
| AC-007 | Declared evidence retained in runtime record; no browser/device claim | Verified |
| AC-008 | 175 existing journey regressions; actual bound Atlas runtime untouched | Verified |

## Checks and review

Read [the installed-wheel proof](checks/installed-wheel.json), [the verification record](checks/verification.json), [progress](progress.md) and [the independent review](review.md).

A real Playwright runner here exercises fixture/configuration and selection without launching a browser. Vitest 4.0.18 was tested through its public exact-specification API; other installed versions must provide that API. These checks do not observe Atlas rendering, native persistence, images or provider services. A consumer rollout still needs its owner to port/adopt the reviewed change while retaining its runtime lineage.
