# Changelog - Cross-Feature User Journeys v2

### 2026-06-09 — Fix: 7 gaps closed (7 functional, 0 visual)

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** Updated [`validator/journeys/runner.py`](../../../validator/journeys/runner.py), [`tests/test_journey_v2_runner.py`](../../../tests/test_journey_v2_runner.py), [`implementation.md`](implementation.md), [`progress.md`](progress.md), [`checks/2026-06-09.md`](checks/2026-06-09.md), and [`../../changelog.md`](../../changelog.md).
- **Gaps closed:** W51/W53 simulator ranking now builds one candidate list across runtimes and sorts by family, shutdown state, runtime rank, and device name; it preserves watchOS selection, validates non-string `state`, skips `simctl boot` for already booted devices, and keeps UDID only as an unclaimed deterministic tie-breaker.
- **Remaining:** None for the W51/W53 runner-ranking fix; verification is scoped to the targeted runner, type, and LiveSpec checks recorded in [`checks/2026-06-09.md`](checks/2026-06-09.md).
- **Verification:** V36 PASS: `git diff --check`; `ruff check validator/journeys/runner.py tests/test_journey_v2_runner.py`; `ruff format --check validator/journeys/runner.py tests/test_journey_v2_runner.py`; `pytest tests/test_journey_v2_runner.py -q` -> 27 passed; `mypy tests/test_journey_v2_runner.py validator/journeys/runner.py` -> no issues; `pyright validator/journeys/runner.py` -> 0 errors; `livespec validate --coherence` -> 0 errors, 0 warnings, 4 infos; `livespec doctor` -> OK, 0 errors, 0 warnings, 4 infos.
- **Author:** spec-fix

### 2026-06-09 — Fix: 3 gaps closed (3 functional, 0 visual)

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** Updated [`validator/journeys/runner.py`](../../../validator/journeys/runner.py), [`tests/test_journey_v2_runner.py`](../../../tests/test_journey_v2_runner.py), [`implementation.md`](implementation.md), [`progress.md`](progress.md), [`checks/2026-06-09.md`](checks/2026-06-09.md), and [`../../changelog.md`](../../changelog.md).
- **Gaps closed:** W49 pre-XCTest hang where a simulator was reported `Booted` but `xcodebuild test` never reached `Test Suite`/`Test Case`. Compiled journey runs now prefer a shutdown available iPhone/watch simulator over an already-booted destination, then boot and await it explicitly.
- **Remaining:** The targeted Strapt import journey now reaches XCTest and returns a real `TEST FAILED`; its functional assertion failure is downstream Strapt work, not this runner hang.
- **Verification:** `pytest tests/test_journey_v2_runner.py -q` -> 23 passed; `ruff check validator/journeys/runner.py tests/test_journey_v2_runner.py` -> pass; `ruff format --check validator/journeys/runner.py tests/test_journey_v2_runner.py` -> pass; `pyright validator/journeys/runner.py` -> 0 errors; Strapt targeted `livespec journey run --journey import-workout-to-library --json` reached `Testing started completed` and returned `** TEST FAILED **` in ~54s instead of hanging.
- **Author:** spec-fix

## 2026-06-09 — [Fix]: Close W31/W33/W35/W37 simulator-destination correction chain

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** Updated [`validator/journeys/runner.py`](../../../validator/journeys/runner.py), [`tests/test_journey_v2_runner.py`](../../../tests/test_journey_v2_runner.py), [`implementation.md`](implementation.md), [`progress.md`](progress.md), [`checks/2026-06-09.md`](checks/2026-06-09.md), and [`../../changelog.md`](../../changelog.md).
- **Gaps closed:** Runtime journey execution no longer defaults to unavailable `platform=iOS Simulator,name=iPhone 16`; XCUITest journeys resolve available iOS/watchOS simulators via `xcrun simctl list devices available --json`, use `id=<UDID>` destinations, and boot/await the resolved simulator before `xcodebuild test`.
- **Scope proof:** W39 brief records `V21 PASS on W37`; V22 accepted this W38/W39 correction using that V21 W37 scope proof. This entry intentionally covers only the W31/W33/W35/W37 chain and removes the W32/W34/W36 audit-finalization claims flagged by W38.
- **Remaining:** Strapt recompile, `$spec-test`, journey run, `$git-commit`, and push were not run.
- **Verification:** `pytest tests/test_journey_v2_runner.py tests/test_journey_v2_cli.py -q` -> 25 passed; targeted Ruff format/check, Pyright, `git diff --check`, and `livespec validate --coherence` pass. Details are recorded in [`checks/2026-06-09.md`](checks/2026-06-09.md).
- **Author:** spec-fix

## 2026-06-09 — [Fix]: Resolve XCUITest journey destinations from available simulators

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** Updated [`validator/journeys/runner.py`](../../../validator/journeys/runner.py), [`tests/test_journey_v2_runner.py`](../../../tests/test_journey_v2_runner.py), [`implementation.md`](implementation.md), [`progress.md`](progress.md), [`checks/2026-06-09.md`](checks/2026-06-09.md), and [`../../changelog.md`](../../changelog.md).
- **Gaps closed:** Runtime journey execution no longer defaults to unavailable `platform=iOS Simulator,name=iPhone 16`; XCUITest journeys resolve available iOS/watchOS simulators via `xcrun simctl list devices available --json`, use `id=<UDID>` destinations, and boot/await the resolved simulator before `xcodebuild test`.
- **Remaining:** A later fresh worker must `$git-commit` LiveSpec, then a fresh Strapt worker must recompile journeys with the updated LiveSpec before retrying `$spec-test`.
- **Verification:** `pytest tests/test_journey_v2_runner.py tests/test_journey_v2_cli.py -q` → 14 passed; targeted `ruff`/`pyright` on touched runner files pass; Strapt destination resolution proof emits iOS UDID `8C365700-3496-4DEF-BCA8-6D6EFC6C5723` and watchOS UDID `659FC5B9-A363-45EF-84C0-23AD342BFEC9`, with no `iPhone 16` destination.
- **Author:** spec-fix

## 2026-06-09 — Fix: 3/3 gaps closed — XCUITest assertions wait for element state

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** Updated [`validator/journeys/compiler.py`](../../../validator/journeys/compiler.py), [`tests/test_journey_v2_compiler.py`](../../../tests/test_journey_v2_compiler.py), [`implementation.md`](implementation.md), [`progress.md`](progress.md), [`checks/2026-06-09.md`](checks/2026-06-09.md), and [`../../changelog.md`](../../changelog.md).
- **Gaps closed:** XCUITest `assert` and `assert_not` steps now compile to generated helper calls that use `waitForExistence(timeout:)` before `XCTAssertTrue` / `XCTAssertFalse`; compiled Swift steps no longer read `.exists` immediately on `app.descendants(matching: .any)[...]`.
- **Remaining:** Downstream projects such as Strapt must recompile journeys with this LiveSpec compiler before retrying the commit-skill audit.
- **Verification:** `pytest tests/test_journey_v2_compiler.py -q` → 15 passed; `pytest tests/test_journey_v2_compiler.py tests/test_journey_v2_cli.py tests/integration/test_migration_v19_user_journeys.py -q` → 20 passed; `ruff check .` → pass after line-length cleanup; targeted `pyright` and `mypy` on touched compiler/test files → pass.
- **Author:** spec-fix

## 2026-06-09 — [Fix]: Requalify W15 mypy validation boundary

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** Updated [`implementation.md`](implementation.md), [`progress.md`](progress.md), [`checks/2026-06-09.md`](checks/2026-06-09.md), and [`../../changelog.md`](../../changelog.md).
- **Gaps closed:** C18 no longer presents `mypy .` as a passing project gate. The artifacts record the rerun result honestly: `mypy .` still fails with 52 pre-existing project-wide errors outside `validator/journeys/compiler.py` and `tests/test_journey_v2_compiler.py`; the touched W13/W15 files pass targeted `mypy` and `pyright`.
- **Remaining:** Project-wide `mypy .` debt remains outside this feature-fix scope; downstream Strapt journeys still need recompilation by a fresh worker after LiveSpec is committed.
- **Verification:** `pytest tests/test_journey_v2_compiler.py tests/test_journey_v2_cli.py tests/integration/test_migration_v19_user_journeys.py -q` → 19 passed; `ruff check .` → pass; `ruff format --check .` → pass; `mypy validator/journeys/compiler.py tests/test_journey_v2_compiler.py` → no issues in 2 source files; `pyright validator/journeys/compiler.py tests/test_journey_v2_compiler.py` → 0 errors; `mypy .` → 52 pre-existing errors in 27 files; `git diff --check` → pass; `livespec validate --coherence` → 0 errors, 0 warnings, 2 infos; `livespec doctor` → OK.
- **Author:** spec-fix

## 2026-06-09 — [Fix]: Close W14 compiler audit majors

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** Updated [`validator/journeys/compiler.py`](../../../validator/journeys/compiler.py), [`tests/test_journey_v2_compiler.py`](../../../tests/test_journey_v2_compiler.py), [`implementation.md`](implementation.md), [`progress.md`](progress.md), [`checks/2026-06-09.md`](checks/2026-06-09.md), and [`../../changelog.md`](../../changelog.md).
- **Gaps closed:** Project-level lint/format commands are documented as `ruff check .` and `ruff format --check .`; XCUITest regression coverage now asserts `auth` and `feature_flags` launch environment emission before `app.launch()`; the compiler returns `journey_source_unreadable` instead of silently compiling without preconditions when a source cannot be reread; XCUITest launch environment keys are centralized constants.
- **Remaining:** Downstream Strapt journeys must be recompiled by a fresh worker after this LiveSpec compiler fix.
- **Verification:** `pytest tests/test_journey_v2_compiler.py -q` → 14 passed; `pytest tests/test_journey_v2_compiler.py tests/test_journey_v2_cli.py tests/integration/test_migration_v19_user_journeys.py -q` → 19 passed; `ruff check .` → pass; `ruff format --check .` → pass; `git diff --check` → pass; `pyright validator/journeys/compiler.py tests/test_journey_v2_compiler.py` → 0 errors; `livespec validate --coherence` → 0 errors, 0 warnings, 2 infos; `livespec doctor` → OK; `mypy .` → fails with 52 pre-existing project-wide errors outside the W15 touched files.
- **Author:** spec-fix

## 2026-06-09 — [Fix]: XCUITest compiler honors journey preconditions before launch

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** Updated [`validator/journeys/compiler.py`](../../../validator/journeys/compiler.py), [`tests/test_journey_v2_compiler.py`](../../../tests/test_journey_v2_compiler.py), [`implementation.md`](implementation.md), [`progress.md`](progress.md), [`checks/2026-06-09.md`](checks/2026-06-09.md), and [`../../changelog.md`](../../changelog.md).
- **Gaps closed:** XCUITest artifacts now inject `preconditions.auth`, `preconditions.fixtures`, `preconditions.mocks`, and `preconditions.feature_flags` into `app.launchEnvironment` before `app.launch()`. XCUITest `open` now renders a generated `openJourneyURL(_:in:)` helper using `XCUIApplication.open(URL)` after launch, with no `Process`/`simctl` path and no post-launch `launchEnvironment` mutation.
- **Remaining:** Downstream projects such as Strapt must be recompiled by a fresh worker to regenerate Swift journey files from this LiveSpec compiler change.
- **Verification:** `pytest tests/test_journey_v2_compiler.py -q` → 13 passed; `pytest tests/test_journey_v2_compiler.py tests/test_journey_v2_cli.py tests/integration/test_migration_v19_user_journeys.py -q` → 18 passed; superseded by W15/W16 project lint/format and targeted type checks.
- **Author:** spec-fix

## 2026-06-09 — [Fix]: Native compiler rejects incomplete journey outputs

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** `validator/journeys/capabilities.py`, `validator/journeys/compiler.py`, `validator/journeys/manifest.py`, `tests/test_journey_v2_compiler.py`, `.specs/features/057-cross-feature-user-journeys-v2/implementation.md`, `.specs/features/057-cross-feature-user-journeys-v2/progress.md`, `.specs/features/057-cross-feature-user-journeys-v2/checks/2026-06-09.md`, `.specs/changelog.md`, `.specs/README.md`
- **Gaps closed:** Generated XCUITest artifacts no longer retain unsupported actions as comments; supported XCUITest output now includes named test methods, broad identifier lookup, URL-only deep-link opening with timeout, fill, screenshot attachments, and `assert_not`; unsupported actions, malformed step dictionaries, missing target/value payloads, and non-URL XCUITest opens fail capability validation before native files are written; manifests end with a trailing newline.
- **Remaining:** Strapt must be recompiled by a fresh worker against this LiveSpec change; Strapt journey-source issues such as condition-based waits remain downstream validation work.
- **Verification:** `pytest tests/test_journey_v2_compiler.py tests/test_journey_v2_cli.py tests/integration/test_migration_v19_user_journeys.py -q` → 17 passed; `ruff check validator/journeys/capabilities.py validator/journeys/compiler.py validator/journeys/manifest.py tests/test_journey_v2_compiler.py`; `ruff format --check validator/journeys/capabilities.py validator/journeys/compiler.py validator/journeys/manifest.py tests/test_journey_v2_compiler.py`; `pyright validator/`
- **Author:** spec-fix

## 2026-06-09 — [Fix]: Migration 20 force-recompiles v2 journeys

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** `migrations/20/migrate.md`, `scripts/migrate-journeys-compile.sh`, `tests/integration/test_migration_v19_user_journeys.py`, `.specs/features/057-cross-feature-user-journeys-v2/implementation.md`, `.specs/features/057-cross-feature-user-journeys-v2/progress.md`, `.specs/features/057-cross-feature-user-journeys-v2/checks/2026-06-09.md`, `.specs/changelog.md`, `.specs/README.md`
- **Gaps closed:** Migration 20 now runs `livespec journey compile --force` via `migrate-journeys-compile.sh`, so migrated downstream projects regenerate every v2 journey manifest instead of only syncing assets and setting version 20.
- **Remaining:** None for the Migration 20 force-recompile gap.
- **Verification:** `pytest tests/test_journey_v2_compiler.py tests/test_journey_v2_cli.py tests/integration/test_migration_v19_user_journeys.py -q`; `ruff check tests/integration/test_migration_v19_user_journeys.py`; `ruff format --check tests/integration/test_migration_v19_user_journeys.py`; `bash -n scripts/migrate-journeys-compile.sh`
- **Author:** spec-fix

## 2026-06-08 — [Fix]: Native journey execution and migration refresh

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** `validator/journeys/runner.py`, `validator/journeys/compiler.py`, `validator/journeys/manifest.py`, `validator/journeys/scanner.py`, `validator/cli_commands/journey_cmd.py`, `validator/cli_commands/test_cmd.py`, `tests/test_journey_v2_runner.py`, `tests/test_journey_v2_compiler.py`, `tests/test_journey_v2_test_integration.py`, `.agent-sync/skills/spec-journey/SKILL.md`, `.agent-sync/skills/spec-test/SKILL.md`, `.agent-sync/skills/spec-feature/SKILL.md`, `.agent-sync/skills/spec-implement/SKILL.md`, `system/testing/user-journeys.md`, `README.md`, `VERSION`, `migrations/20/migrate.md`, `tests/integration/test_migration_v19_user_journeys.py`
- **Gaps closed:** Native compiled artifacts now execute through Playwright, XCUITest, Maestro, pytest, or cargo dispatch; `livespec test` no longer uses freshness-only journey gates; XCUITest compilation runs `xcodegen generate` for XcodeGen projects; compiler version `journeys-v2-2` forces old manifests to be regenerated after migration.
- **Remaining:** None for the native execution and migration gap.
- **Verification:** `pytest tests/test_journey_v2_runner.py tests/test_journey_v2_test_integration.py tests/test_journey_v2_compiler.py -q`
- **Author:** spec-fix

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
