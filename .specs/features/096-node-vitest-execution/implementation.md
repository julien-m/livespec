---
created: 2026-10-16
feature: 096-node-vitest-execution
title: 'Implementation Map: Node Vitest Execution Observations'
type: implementation
updated: 2026-10-17
---

# Implementation — Node Vitest Execution Observations

All six execution ACs are certified by the fresh runner-owned98-test capture. Current143 bindings, independent mapping/full-scope reviews, nine-asset installed API and unchanged46/55 consumer observations pass. Inspect [the final capture](.reviews/implementation-evidence/corrected-98-capture.json) and [the progress checkpoint](progress.md). Earlier failed and stale runs remain historical; no consumer lifecycle or global runtime was changed.

## Requirement Mapping

Inspect the linked source files and their requirement anchors.

| Requirement | Source | Anchor | Current status |
|---|---|---|---|
| [FR-001](spec.md#fr-001) | [CLI observation](../../../validator/cli_commands/execution_io.py), [Vitest preparation](../../../validator/execution_vitest.py) | `@spec FR-001` | Implemented; real passed/red and option tests pass |
| [FR-002](spec.md#fr-002) | [matcher observer](../../../validator/vitest/matcher-observer.ts), [selected results](../../../validator/execution_vitest_results.py) | `@spec FR-002` | Implemented; four review findings corrected, 14 boundary cases pass |
| [FR-003](spec.md#fr-003) | [runtime provenance](../../../validator/execution_vitest_provenance.py), [governed configuration](../../../validator/vitest/config.ts) | `@spec FR-003` | Implemented; runtime/config/setup and artifact refusal tests pass |
| [FR-004](spec.md#fr-004) | [bounded preparation](../../../validator/execution_vitest.py) | `@spec FR-004` | Implemented; native body/hook caps plus shared command cap; enforcement reports command-only |
| [FR-005](spec.md#fr-005) | [observation branch](../../../validator/cli_commands/execution_io.py), [generic goal marker](../../../.agent-sync/skills/spec-implement/SKILL.md) | `@spec FR-005` | Implemented; acceptance unchanged; generic passed proof and current goal archive verified |
| [FR-006](spec.md#fr-006) | [two-run verification](../../../tests/test_execution_vitest_consumer.py) | `@spec FR-006` | Fresh final 46/55 observations pass; original input identity check passes |

## Acceptance Criteria Mapping

Inspect the real Python assertions; parameterized cases retain exact IDs and require the existing independent manual mapping review. No JavaScript AC certification is introduced.

| AC | Python tests | Current status |
|---|---|---|
| [AC-001](spec.md#ac-001) | [real transport cases](../../../tests/test_execution_vitest.py), [CLI option cases](../../../tests/test_native_test_option_matrix.py) | ✅ Covered; observed Implement98-test receipt |
| [AC-002](spec.md#ac-002) | [actual dispatch/settlement cases](../../../tests/test_execution_vitest.py), [boundary regressions](../../../tests/test_execution_vitest_boundaries.py) | ✅ Covered; observed Implement98-test receipt |
| [AC-003](spec.md#ac-003) | [provenance/tamper cases](../../../tests/test_execution_vitest.py), [substitution and drift cases](../../../tests/test_execution_vitest_integrity.py), [archive guard drift](../../../tests/test_execution_vitest_goal.py) | ✅ Covered; observed Implement98-test receipt |
| [AC-004](spec.md#ac-004) | [arguments/deadline cases](../../../tests/test_execution_vitest.py), [preparation and child cleanup](../../../tests/test_execution_vitest_budgets.py) | ✅ Covered; observed Implement98-test receipt |
| [AC-005](spec.md#ac-005) | [observation separation](../../../tests/test_execution_vitest.py), [canonical marker](../../../tests/test_bugfix_goal.py), [acceptance joins](../../../tests/test_acceptance_execution_join.py), [canonical task016 guard](../../../tests/test_execution_vitest_goal.py) | ✅ Covered; observed Implement98-test receipt |
| [AC-006](spec.md#ac-006) | [both unchanged selections](../../../tests/test_execution_vitest_consumer.py) | ✅ Covered; observed Implement98-test receipt |

## Files Created or Modified

- New Python transport, provenance and inventory reconciliation modules; existing runner, capture and evidence integration.
- Nine owned TypeScript assets: config, runner, reporter, matcher, callsite, expectation guard, trace, direct async syntax and opaque consumption bridge; setuptools package data includes them.
- Existing test CLI option and contradiction validation; canonical spec-implement outcome marker and expectations; README usage.
- Genuine integration fixture/core/boundary/consumer, provenance, phase budget and canonical task016 guard tests; focused CLI and goal-marker regressions.
- Dedicated Node 22 CI job and locked local Vitest/TypeScript/Biome toolchain; genuine observation witness fixture.

## Evidence and Boundaries

- Inspect [async feasibility](.reviews/implementation-evidence/async-feasibility.json): awaited/returned versus Vitest auto-awaited assertions were observed separately with real matcher outcomes.
- Inspect [compatibility recovery](.reviews/implementation-evidence/compatibility-recovery.json): 79 nearby pytest/Cargo/evidence checks passed after disk space recovery; no full suite was run.
- Inspect [historical hashes](.reviews/implementation-evidence/goal-history-before.json) and [comparison](.reviews/implementation-evidence/goal-history-after.json): the earlier immutable goal pair remains unchanged.
- Previous dashboard receipt was reverified for its then-current assets: 46 tests, 86 matchers. Its CLI transcript was unavailable after ENOSPC; final observer changes require fresh observations.
- Original consumer inputs/pins and lifecycle remain untouched. Observations certify zero ACs. This is cooperative local provenance, not a same-user JavaScript sandbox.

- Inspect [installed wheel assets and module identity](.reviews/implementation-evidence/wheel-installation.json), [real installed adapter execution](.reviews/implementation-evidence/installed-wheel-adapter.json) and [source CLI witness](.reviews/implementation-evidence/generic-source-cli.json). Whole-wheel CLI import remains a pre-existing missing driver-template packaging limitation; no installed CLI success is claimed.

- Inspect [current nine-asset wheel identities](.reviews/implementation-evidence/opaque-wheel-assets.json), [current installed async API](.reviews/implementation-evidence/opaque-installed-api.json) and [current complete consumer observations](.reviews/implementation-evidence/consumer-opaque-observations.json). Earlier seven-asset and consumer receipts retain their historical interpretation and cannot certify these changed assets.
- Inspect [the two-phase async regression proof](.reviews/implementation-evidence/async-finally-green.json) and [current143-binding mapping](.reviews/implementation-evidence/opaque-mapping-ingestion.json). Executed direct await/return syntax only authorizes the exact owned thenable; actual consumption and settlement are separately required. Unsupported compositions, callback ownership and finalizer-return forms fail closed.

## Incomplete checkpoint after canonical identity correction

Inspect [the identity/assertion/citation diagnostic](.reviews/implementation-evidence/canonical-junit-diagnostic.json):128/128 observed, passing and grounded against an existing genuine87-case run. The mapping now uses the existing canonical JUnit identity API and has current native raw review/synthesis. This diagnostic does not certify execution: governed mapping/review bytes changed after that run, so its receipt remains stale and certified ACs are empty. A future fresh capture requires an explicitly authorized envelope. No successful goal/archive, finalization or delivery is claimed.

## Final certified closure

Inspect [the actual closure summary](.reviews/implementation-evidence/implement-closure-summary.json): all6 execution ACs certified, machine finalization PASS, both conventions gates PASS, goal complete and archived verify-output success. Earlier incomplete checkpoints above remain historical.

## Bugfix Receipts

| Date | Requirement | Regression tests | RED receipt | GREEN receipt |
|---|---|---|---|---|
| 2026-10-17 | implementation | `tests/test_execution_vitest_bindings.py::test_async_import_tracking_only_uses_pattern_bindings[array-default]`, `tests/test_execution_vitest_bindings.py::test_async_import_tracking_only_uses_pattern_bindings[catch-property-key]`, `tests/test_execution_vitest_bindings.py::test_async_import_tracking_only_uses_pattern_bindings[parameter-default]`, `tests/test_execution_vitest_bindings.py::test_async_import_tracking_only_uses_pattern_bindings[parameter-property-key]`, `tests/test_execution_vitest_bindings.py::test_async_import_tracking_only_uses_pattern_bindings[property-default]`, `tests/test_execution_vitest_bindings.py::test_async_import_tracking_only_uses_pattern_bindings[property-key]` | `.specs/.execution/79c6132a0bf04d3a8f79e915844f52e6/receipt.json` | `.specs/.execution/426e1c14745247efb68ab9421427b4fd/receipt.json` |
| 2026-10-17 | implementation | `tests/test_execution_vitest_asset_paths.py::test_consumer_asset_names_remain_instrumented_and_bound[project-root]`, `tests/test_execution_vitest_asset_paths.py::test_consumer_asset_names_remain_instrumented_and_bound[test-subdirectory]` | `.specs/.execution/5056fd0acc8047728ba51b73dd2a20d6/receipt.json` | `.specs/.execution/0a3fa7ba7b2944968880e32520331bea/receipt.json` |
| 2026-10-17 | implementation | `tests/test_execution_vitest_asset_paths.py::test_wrapped_configuration_lifecycle_plugins_fail_closed[apply-nested-array]`, `tests/test_execution_vitest_asset_paths.py::test_wrapped_configuration_lifecycle_plugins_fail_closed[apply-promise]`, `tests/test_execution_vitest_asset_paths.py::test_wrapped_configuration_lifecycle_plugins_fail_closed[config-nested-array]`, `tests/test_execution_vitest_asset_paths.py::test_wrapped_configuration_lifecycle_plugins_fail_closed[config-promise]`, `tests/test_execution_vitest_asset_paths.py::test_wrapped_configuration_lifecycle_plugins_fail_closed[configResolved-nested-array]`, `tests/test_execution_vitest_asset_paths.py::test_wrapped_configuration_lifecycle_plugins_fail_closed[configResolved-promise]` | `.specs/.execution/f3932551a4b848c19902c8a3d97e0f67/receipt.json` | `.specs/.execution/5301576c58a44fea9ea1d64b1a1997c0/receipt.json` |

## Current Source Ownership

The dated map retains every previously mapped source and includes both files of the confined binding-pattern correction.

| Date | Owned source |
|---|---|
| 2026-10-17 | Inspect [SKILL.md](../../../.agent-sync/skills/spec-implement/SKILL.md) |
| 2026-10-17 | Inspect [test_acceptance_execution_join.py](../../../tests/test_acceptance_execution_join.py) |
| 2026-10-17 | Inspect [test_bugfix_goal.py](../../../tests/test_bugfix_goal.py) |
| 2026-10-17 | Inspect [test_execution_vitest.py](../../../tests/test_execution_vitest.py) |
| 2026-10-17 | Inspect [test_execution_vitest_bindings.py](../../../tests/test_execution_vitest_bindings.py) |
| 2026-10-17 | Inspect [test_execution_vitest_boundaries.py](../../../tests/test_execution_vitest_boundaries.py) |
| 2026-10-17 | Inspect [test_execution_vitest_budgets.py](../../../tests/test_execution_vitest_budgets.py) |
| 2026-10-17 | Inspect [test_execution_vitest_consumer.py](../../../tests/test_execution_vitest_consumer.py) |
| 2026-10-17 | Inspect [test_execution_vitest_goal.py](../../../tests/test_execution_vitest_goal.py) |
| 2026-10-17 | Inspect [test_execution_vitest_integrity.py](../../../tests/test_execution_vitest_integrity.py) |
| 2026-10-17 | Inspect [test_native_test_option_matrix.py](../../../tests/test_native_test_option_matrix.py) |
| 2026-10-17 | Inspect [execution_io.py](../../../validator/cli_commands/execution_io.py) |
| 2026-10-17 | Inspect [execution_vitest.py](../../../validator/execution_vitest.py) |
| 2026-10-17 | Inspect [execution_vitest_provenance.py](../../../validator/execution_vitest_provenance.py) |
| 2026-10-17 | Inspect [execution_vitest_results.py](../../../validator/execution_vitest_results.py) |
| 2026-10-17 | Inspect [async-source.ts](../../../validator/vitest/async-source.ts) |
| 2026-10-17 | Inspect [config.ts](../../../validator/vitest/config.ts) |
| 2026-10-17 | Inspect [matcher-observer.ts](../../../validator/vitest/matcher-observer.ts) |

## Observer Path Ownership Correction

Inspect the current source ownership additions; the previous dated source map remains in force.

| Date | Owned source |
|---|---|
| 2026-10-17 | Inspect [matcher-callsite.ts](../../../validator/vitest/matcher-callsite.ts) |
| 2026-10-17 | Inspect [trace-state.ts](../../../validator/vitest/trace-state.ts) |
| 2026-10-17 | Inspect [test_execution_vitest_asset_paths.py](../../../tests/test_execution_vitest_asset_paths.py) |

## Plugin Options and CI Wiring Correction

PluginOption arrays and false/null/undefined retain ordinary plugin support. Promise/thenable and unknown wrapper options are explicitly unsupported; config/configResolved and function-valued apply callbacks are rejected. String apply:serve/build remain supported. This confined bugfix does not recertify the full feature. The initial seven-module local command collected95 cases with zero skips,94 passes and one fixture failure; final changed tests pass separately. Full final-head GitHub CI is required before merge.

| Date | Owned source |
|---|---|
| 2026-10-17 | Inspect [the Node observer workflow](../../../.github/workflows/ci.yml) |
