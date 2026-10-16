# Implementation — Node Vitest Execution Observations

Local implementation and grouped CI/async repairs are present. Fresh nine-asset wheel/API and complete46/55 consumer observations pass. Current143-binding/98-ID mapping and independent complete-diff review/audit pass. Fresh acceptance execution certification and finalization remain pending; status is explicitly INCOMPLETE/DRAFT. Inspect the [progress checkpoint](progress.md) and [approved plan](plan.md) before resuming.

## Requirement Mapping

Inspect the linked source files and their requirement anchors.

| Requirement | Source | Anchor | Current status |
|---|---|---|---|
| [FR-001](spec.md#fr-001) | [CLI observation](../../../validator/cli_commands/execution_io.py), [Vitest preparation](../../../validator/execution_vitest.py) | `@spec FR-001` | Implemented; real passed/red and option tests pass |
| [FR-002](spec.md#fr-002) | [matcher observer](../../../validator/vitest/matcher-observer.ts), [selected results](../../../validator/execution_vitest_results.py) | `@spec FR-002` | Implemented; four review findings corrected, 14 boundary cases pass |
| [FR-003](spec.md#fr-003) | [runtime provenance](../../../validator/execution_vitest_provenance.py), [governed configuration](../../../validator/vitest/config.ts) | `@spec FR-003` | Implemented; runtime/config/setup and artifact refusal tests pass |
| [FR-004](spec.md#fr-004) | [bounded preparation](../../../validator/execution_vitest.py) | `@spec FR-004` | Implemented; native body/hook caps plus shared command cap; enforcement reports command-only |
| [FR-005](spec.md#fr-005) | [observation branch](../../../validator/cli_commands/execution_io.py), [generic goal marker](../../../.agent-sync/skills/spec-implement/SKILL.md) | `@spec FR-005` | Implemented; acceptance unchanged; generic passed proof accepted; archive pending |
| [FR-006](spec.md#fr-006) | [two-run verification](../../../tests/test_execution_vitest_consumer.py) | `@spec FR-006` | Fresh final 46/55 observations pass; original input identity check passes |

## Acceptance Criteria Mapping

Inspect the real Python assertions; parameterized cases retain exact IDs and require the existing independent manual mapping review. No JavaScript AC certification is introduced.

| AC | Python tests | Current status |
|---|---|---|
| [AC-001](spec.md#ac-001) | [real transport cases](../../../tests/test_execution_vitest.py), [CLI option cases](../../../tests/test_native_test_option_matrix.py) | Passing targeted cases; final mapped capture pending |
| [AC-002](spec.md#ac-002) | [actual dispatch/settlement cases](../../../tests/test_execution_vitest.py), [boundary regressions](../../../tests/test_execution_vitest_boundaries.py) | Four findings reproduced RED, then 14 boundary cases GREEN |
| [AC-003](spec.md#ac-003) | [provenance/tamper cases](../../../tests/test_execution_vitest.py), [substitution and drift cases](../../../tests/test_execution_vitest_integrity.py), [archive guard drift](../../../tests/test_execution_vitest_goal.py) | Twelve additional real provenance cases pass; final mapped capture pending |
| [AC-004](spec.md#ac-004) | [arguments/deadline cases](../../../tests/test_execution_vitest.py), [preparation and child cleanup](../../../tests/test_execution_vitest_budgets.py) | Two distinct real timeout 124 cases pass; final mapped capture pending |
| [AC-005](spec.md#ac-005) | [observation separation](../../../tests/test_execution_vitest.py), [canonical marker](../../../tests/test_bugfix_goal.py), [acceptance joins](../../../tests/test_acceptance_execution_join.py), [canonical task016 guard](../../../tests/test_execution_vitest_goal.py) | Real canonical task proof and native archive guard pass; full goal archive pending |
| [AC-006](spec.md#ac-006) | [both unchanged selections](../../../tests/test_execution_vitest_consumer.py) | Fresh final two-run manifest and current Python verification pass |

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
