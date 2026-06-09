---
feature: 057-cross-feature-user-journeys-v2
status: Implemented
created: 2026-06-04
updated: 2026-06-09
---

# Progress - Cross-Feature User Journeys v2

| Step | Description | Status | Evidence |
|---|---|---|---|
| 1 | Add v2 typed model layer | Done | `pytest tests/test_journey_v2_schema.py -v --tb=short` → 5 passed |
| 2 | Replace path helpers with v2 layout support | Done | `pytest tests/test_journey_v2_validation.py -v --tb=short` |
| 3 | Build the v2 validator and index | Done | v2 refs, index, backlinks covered by `tests/test_journey_v2_validation.py` |
| 4 | Implement journey history and decision governance | Done | `pytest tests/test_journey_v2_history.py -v --tb=short` |
| 5 | Add bootstrap and auto-assignment services | Done | `pytest tests/test_journey_v2_assignment_bootstrap.py -v --tb=short` |
| 6 | Add JourneyImpactAnalyzer | Done | `pytest tests/test_journey_v2_impact.py -v --tb=short` |
| 7 | Split compiler into registry, capabilities, and runner compilers | Done | `pytest tests/test_journey_v2_compiler.py -v --tb=short` |
| 8 | Define manifest semantics | Done | Manifest read/write covered by `tests/test_journey_v2_compiler.py` |
| 9 | Implement compiled-only run semantics | Done | `pytest tests/test_journey_v2_runner.py -v --tb=short` |
| 10 | Extend `livespec journey` CLI | Done | `pytest tests/test_journey_v2_cli.py -v --tb=short` |
| 11 | Integrate with `livespec test`, `$spec-test`, `$spec-feature`, and `$spec-implement` | Done | `pytest tests/test_journey_v2_test_integration.py -v --tb=short`; skills updated |
| 12 | Create `$spec-journey` skill surface | Done | `pytest tests/test_journey_v2_docs_skills.py tests/test_command_audit_cli.py -q` |
| 13 | Add native visual checks | Done | `pytest tests/test_journey_v2_visual_llm.py tests/test_journey_v2_compiler.py -q` |
| 14 | Add LLM visual checks | Done | `pytest tests/test_journey_v2_visual_llm.py tests/test_journey_v2_compiler.py -q` |
| 15 | Implement v1 migration | Done | `pytest tests/test_journey_v2_migration.py -v --tb=short` |
| 16 | Extend doctor reporting | Done | `pytest tests/test_journey_v2_doctor.py tests/test_doctor.py -q` |
| 17 | Update documentation | Done | `pytest tests/test_journey_v2_docs_skills.py tests/test_command_audit_cli.py -q` |
| 18 | Preserve backward compatibility boundaries | Done | `pytest tests/test_journeys.py tests/test_journey_v2_migration.py -q` |

## Checkpoints

- 2026-06-04: Goal contract created and prerequisite evidence accepted through task 14.
- 2026-06-04: Step 1 completed with Pydantic v2 source, coverage, target, action, visual, and privacy models.
- 2026-06-04: Steps 2-4 completed with v2 path helpers, project validation/index, generated backlinks, and source-hash history governance.
- 2026-06-04: Steps 5-6 completed with deterministic assignment/bootstrap and journey impact analysis.
- 2026-06-04: Steps 7-8 completed with v2 compiler facade, runner capabilities, native artifact markers, and compiled manifest.
- 2026-06-04: Step 9 completed with compiled-only runner selection and stale/missing manifest findings.
- 2026-06-04: Steps 10-18 completed with CLI, `$spec-journey`, v1 migration, doctor findings, native/LLM visual checks, and docs.
- 2026-06-04: Verification complete: `pytest tests/ --ignore=tests/integration -q` → 1583 passed, 4 skipped; `pyright validator/` → 0 errors; changed-file `ruff check` and `ruff format --check` passed.
- 2026-06-05: `$spec-fix` closed check gaps: implementation mapping now covers 41 FR and 46 AC, journey skills use global v2 paths and compiled-only run gates, impact detection uses SmartTestSelector plus stable target signals, and Python convention gaps were fixed.
- 2026-06-07: Migration 19 added so existing v18 projects re-run agent asset sync and receive `$spec-journey`, User Journeys v2 routing, and updated command guidance; root README now documents `/spec-journey`.
- 2026-06-08: `$spec-fix` corrected the native execution gap: `livespec journey run`, `livespec test`, and feature/implement gates now execute compiled native artifacts without recompiling; XCUITest compilation refreshes XcodeGen projects; compiler `journeys-v2-2` makes old manifests stale so migrated projects must explicitly regenerate journeys.
- 2026-06-09: `$spec-fix` made Migration 20 run `migrate-journeys-compile.sh`, which invokes `livespec journey compile --force` from the migrated project root; regression coverage proves old `journeys-v2-1` manifests are rewritten to the current compiler version.
- 2026-06-09: `$spec-fix` hardened native journey compilation after Strapt audit blockers: XCUITest now emits named test methods, URL-only deep-link opening with timeout, Foundation import, broad identifier lookup, fill, screenshot attachments, and negative assertions; unsupported actions, malformed step dictionaries, missing payload values, and non-URL XCUITest opens are rejected before writing native artifacts; manifests now end with a trailing newline.
- 2026-06-09: `$spec-fix` closed the W13 compiler gap: XCUITest preconditions now populate `app.launchEnvironment` before `app.launch()`, and `open` renders `openJourneyURL(_:in:)` using `XCUIApplication.open(URL)` after launch without `Process()` or post-launch launch-environment mutation.
- 2026-06-09: `$spec-fix` closed W14 audit majors: XCUITest tests now assert `auth` and `feature_flags` before `app.launch()`, compiler source reread failures return `journey_source_unreadable` before artifact writes, launch environment keys are constants, and W16 requalified verification docs so `mypy .` is recorded as pre-existing project type debt while touched files pass targeted `mypy` and `pyright`.
- 2026-06-09: `$spec-fix` closed the W21/W22 assertion compiler gap: generated XCUITest `assert` and `assert_not` steps now call wait-based helpers instead of reading `.exists` immediately, with regression coverage proving helper generation and absence of immediate descendant assertions.
- 2026-06-09: `$spec-fix` closed the W31/W33/W35/W37 simulator-destination correction chain validated through V22, preserving the V21 W37 proof: [`validator/journeys/runner.py`](../../../validator/journeys/runner.py) resolves XCUITest destinations from available `simctl` devices, emits `id=<UDID>` instead of hardcoded `name=iPhone 16`, boots/awaits the resolved simulator before `xcodebuild test`, and W39 traceability no longer records W32/W34/W36 as the active finalization scope.
