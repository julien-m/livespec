---
created: 2026-10-16
feature: 096-node-vitest-execution
title: 'Implementation Map: Node Vitest Execution Observations'
type: implementation
updated: 2026-10-17
---

# Implementation — Node Vitest Execution Observations

The original six-AC delivery remains historical. The confined-cwd revision is under current verification; its spec and plan reviews were refreshed and the official revision closed. Current capture, consumer, acceptance and delivery evidence will be recorded below before claiming revised completion. Inspect [the checkpoint](progress.md); all earlier artifacts are preserved.

## Requirement Mapping

Inspect the linked source files and their requirement anchors.

| Date | Requirement | Source | Anchor | Current status |
|---|---|---|---|---|
| 2026-10-17 | [FR-003](spec.md#fr-003), [FR-004](spec.md#fr-004) | [execution_capture.py](../../../validator/execution_capture.py), [execution_runner.py](../../../validator/execution_runner.py), [execution_vitest.py](../../../validator/execution_vitest.py), [execution_vitest_provenance.py](../../../validator/execution_vitest_provenance.py), [execution_evidence.py](../../../validator/execution_evidence.py), [execution_working_directory.py](../../../validator/execution_working_directory.py), [execution_timeout_capture.py](../../../validator/execution_timeout_capture.py), [test_cmd.py](../../../validator/cli_commands/test_cmd.py), [operation_options.py](../../../validator/cli_commands/operation_options.py), [execution_io.py](../../../validator/cli_commands/execution_io.py), [test_execution_working_directory.py](../../../tests/test_execution_working_directory.py), [test_execution_vitest_consumer.py](../../../tests/test_execution_vitest_consumer.py) | `@spec FR-003`, `@spec FR-004`, `@spec AC-003` | Confined single-invocation cwd; current verification in progress |
| Historical | [FR-001](spec.md#fr-001) | [CLI observation](../../../validator/cli_commands/execution_io.py), [Vitest preparation](../../../validator/execution_vitest.py) | `@spec FR-001` | Implemented; real passed/red and option tests pass |
| Historical | [FR-002](spec.md#fr-002) | [matcher observer](../../../validator/vitest/matcher-observer.ts), [selected results](../../../validator/execution_vitest_results.py) | `@spec FR-002` | Implemented; four review findings corrected, 14 boundary cases pass |
| Historical | [FR-003](spec.md#fr-003) | [runtime provenance](../../../validator/execution_vitest_provenance.py), [governed configuration](../../../validator/vitest/config.ts) | `@spec FR-003` | Implemented; runtime/config/setup and artifact refusal tests pass |
| Historical | [FR-004](spec.md#fr-004) | [bounded preparation](../../../validator/execution_vitest.py) | `@spec FR-004` | Implemented; native body/hook caps plus shared command cap; enforcement reports command-only |
| Historical | [FR-005](spec.md#fr-005) | [observation branch](../../../validator/cli_commands/execution_io.py), [generic goal marker](../../../.agent-sync/skills/spec-implement/SKILL.md) | `@spec FR-005` | Implemented; acceptance unchanged; generic passed proof and current goal archive verified |
| Historical | [FR-006](spec.md#fr-006) | [two-run verification](../../../tests/test_execution_vitest_consumer.py) | `@spec FR-006` | Fresh final 46/55 observations pass; original input identity check passes |

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
| 2026-10-17 | implementation | `tests/test_execution_vitest_budgets.py::test_cli_final_verification_keeps_original_deadline_and_invalidates_timeout[completion-write-error]`, `tests/test_execution_vitest_budgets.py::test_cli_final_verification_keeps_original_deadline_and_invalidates_timeout[expired-verification]`, `tests/test_execution_vitest_budgets.py::test_consumer_timeouts_cannot_disable_owned_limits[hook-0-120]`, `tests/test_execution_vitest_budgets.py::test_consumer_timeouts_cannot_disable_owned_limits[hook-NaN-120]`, `tests/test_execution_vitest_budgets.py::test_consumer_timeouts_cannot_disable_owned_limits[test-'invalid'-None]`, `tests/test_execution_vitest_budgets.py::test_consumer_timeouts_cannot_disable_owned_limits[test--1-120]`, `tests/test_execution_vitest_budgets.py::test_consumer_timeouts_cannot_disable_owned_limits[test-0-120]` | `.specs/.execution/c173b4c641d74ae48ee8e282e6fc1cbb/receipt.json` | `.specs/.execution/0026d3d8618343dbbf796fdd27ac569a/receipt.json` |
| 2026-10-17 | AC-002 | `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[chainable]`, `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[getter]`, `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[method]`, `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[parent]`, `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[plugin-setup]`, `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[plugin-test]`, `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[replace-built-in]` | `.specs/.execution/4e64d2dbb4fd44ecbf03f38e321fe43d/receipt.json` | `.specs/.execution/ec4b03a2c9824b2a930ef252401d0383/receipt.json` |
| 2026-10-17 | AC-002 | `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[chainable]`, `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[getter]`, `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[method]`, `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[parent]`, `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[plugin-setup]`, `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[plugin-test]`, `tests/test_execution_vitest_extensions.py::test_late_custom_matcher_cannot_hide_behind_supported_dispatch[replace-built-in]` | `.specs/.execution/4e64d2dbb4fd44ecbf03f38e321fe43d/receipt.json` | `.specs/.execution/237a4d011b7d4506aa7fdf940486488d/receipt.json` |

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

## Timeout and Final Verification Correction

Consumer zero, negative and nonfinite numeric test/hook timeouts use the positive owned ceiling; stricter positive values remain effective and wrong types fail closed. CLI capture and final provenance verification share the original absolute deadline. New CLI captures remain provisional until hash-bound completion is appended within that deadline; missing, malformed or failed completion cannot qualify through later public reads. Standalone API verification retains its existing independent invocation semantics. Historical feature and consumer certificates are unchanged; this scoped bugfix is not full-feature recertification.

| Date | Owned source |
|---|---|
| 2026-10-17 | Inspect [execution_capture.py](../../../validator/execution_capture.py) |
| 2026-10-17 | Inspect [execution_evidence.py](../../../validator/execution_evidence.py) |
| 2026-10-17 | Inspect [execution_verification.py](../../../validator/execution_verification.py) |

## Confined Invocation Working Directory Revision

- FR-003/004 keep the governing project, feature and storage root fixed while one direct Vitest invocation uses an explicit existing directory confined beneath that root. CLI and API omit cwd by default; historical captures still mean root. Archive reads recheck the same directory identity and runtime provenance.
- Read [the current independent check](checks/2026-10-17.md) and [the real cwd regressions](../../../tests/test_execution_working_directory.py). The source-owned 40-test/108-binding checkpoint passed all six ACs; later source closure belongs to the current CLI goal archive, never to an older certificate. Producer copies observed 46/55 unchanged consumer tests and do not close consumer042.

| Date | Requirement | Owned source |
|---|---|---|
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [execution_working_directory.py](../../../validator/execution_working_directory.py) |
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [execution_capture.py](../../../validator/execution_capture.py) |
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [execution_evidence.py](../../../validator/execution_evidence.py) |
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [execution_runner.py](../../../validator/execution_runner.py) |
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [execution_timeout_capture.py](../../../validator/execution_timeout_capture.py) |
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [execution_vitest.py](../../../validator/execution_vitest.py) |
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [execution_vitest_provenance.py](../../../validator/execution_vitest_provenance.py) |
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [execution_io.py](../../../validator/cli_commands/execution_io.py) |
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [operation_options.py](../../../validator/cli_commands/operation_options.py) |
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [test_cmd.py](../../../validator/cli_commands/test_cmd.py) |
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [test_execution_working_directory.py](../../../tests/test_execution_working_directory.py) |
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [test_execution_vitest_consumer.py](../../../tests/test_execution_vitest_consumer.py) |
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [ci.yml](../../../.github/workflows/ci.yml) |
| 2026-10-17 | FR-003, FR-004 / AC-003, AC-004, AC-006 | Read [README.md](../../../README.md) |


## CI timeout-test correction — 2026-10-17

| Date | Requirement | Owned test and anchor | Scope |
|---|---|---|---|
| 2026-10-17 | [FR-004](spec.md#fr-004), [AC-004](spec.md#ac-004) | Read [the runtime deadline test](../../../tests/test_execution_vitest.py), `@spec AC-004` | Assert the public timeout result before branching on receipt publication; retain the 1.5-second limit and both observation refusals for published receipts. |

CI on `3cc9ac50da18e968a0b3b1d595523e9f36007f72` exposed the legitimate no-fresh-receipt timeout result. The test previously required publication through a convenience helper. Runtime behavior and normative requirements are unchanged. The local pre-edit attempt passed through the other legitimate branch; the official bugfix gate printed FALLBACK rather than qualifying a fabricated RED. The normal correction targets AC-004. Earlier 40-test/six-AC and 31-test/four-AC certificates remain bound to their original source trees.

- Current AC-004 scope: 10 passing real cases and 30 independently reviewed bindings; inspect [the execution receipt](../../.execution/cd926fb097c44fe282ed333ca49b8f56/receipt.json). It includes separate preparation-expiry and owned-descendant/heartbeat cleanup witnesses. Other acceptance criteria are not recertified by this correction.


## API completion fixture compatibility — 2026-10-18

- Fixture maintenance only: no production or normative change, no new acceptance certification. Four selected test functions execute five cases, all PASS with real Node 22/Vitest and zero skips.
- Read [the fixture](../../../tests/execution_vitest_fixture.py), [legacy-root regression](../../../tests/test_execution_working_directory.py) and [origin regression](../../../tests/test_execution_vitest_integrity.py). Semantic inventory/origin corruption updates only the capture hash in the actual completion marker while retaining its real deadline budget; historical schema explicitly has verification_pending=false.
- Prior production-095 capture7159 and other certificates remain historical under their original test trees. Standalone regression output is external, not an AC receipt.
