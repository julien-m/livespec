---
title: Test Time Budgets implementation
feature: 095-test-time-budgets
---

# Implementation — Test Time Budgets

Local implementation and targeted checks are recorded below. All implementation steps and current acceptance/conventions checks pass. The independent delivery review is recorded and verified PASS; feature finalization is verified PASS. No consumer pin was changed.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001](spec.md#fr-001) | [execution_deadline.py](../../../validator/execution_deadline.py), [test_cmd.py](../../../validator/cli_commands/test_cmd.py), [runner.py](../../../validator/drivers/runner.py) | `@spec FR-001` | Implemented; local checks pass | 2026-10-16 |
| [FR-002](spec.md#fr-002) | [execution_test_budget.py](../../../validator/execution_test_budget.py), [execution_pytest.py](../../../validator/execution_pytest.py), [execution_cargo_hook.py](../../../validator/execution_cargo_hook.py) | `@spec FR-002` | Implemented; pytest and Cargo timeout proof pass | 2026-10-16 |
| [FR-003](spec.md#fr-003) | [execution_deadline.py](../../../validator/execution_deadline.py), [execution_capture_storage.py](../../../validator/execution_capture_storage.py) | `@spec FR-003` | Implemented; bounded TERM/KILL and pipe proof pass | 2026-10-16 |
| [FR-004](spec.md#fr-004) | [test_budgets.py](../../../validator/test_budgets.py) | `@spec FR-004` | Implemented; strict policy proof passes | 2026-10-16 |
| [FR-005](spec.md#fr-005) | [execution_capture.py](../../../validator/execution_capture.py), [execution_timeout_capture.py](../../../validator/execution_timeout_capture.py), [execution_io.py](../../../validator/cli_commands/execution_io.py), [bugfix_cmd.py](../../../validator/cli_commands/bugfix_cmd.py) | `@spec FR-005` | Implemented; normal receipts and timeout refusal verified | 2026-10-16 |
| [FR-006](spec.md#fr-006) | [minimal-spec-scope.md](../../../system/minimal-spec-scope.md), [review-protocol.md](../../../system/review-protocol.md), [execution-rules.md](../../../system/testing/execution-rules.md) | `@spec FR-006` | Implemented; contract PASS; delivery review recorded PASS | 2026-10-16 |
| [FR-007](spec.md#fr-007) | [anti-drift-block.md](../../../system/anti-drift-block.md), [execution-rules.md](../../../system/testing/execution-rules.md) | `@spec FR-007` | Implemented; contract PASS; delivery review recorded PASS | 2026-10-16 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| [AC-001](spec.md#ac-001) | [test_execution_deadline.py](../../../tests/test_execution_deadline.py) | Covered — certified PASS; 2026-10-16 |
| [AC-002](spec.md#ac-002) | [test_execution_test_budgets.py](../../../tests/test_execution_test_budgets.py) | Covered — certified PASS; 2026-10-16 |
| [AC-003](spec.md#ac-003) | [test_execution_deadline.py](../../../tests/test_execution_deadline.py), [test_execution_test_budgets.py](../../../tests/test_execution_test_budgets.py) | Covered — certified PASS; 2026-10-16 |
| [AC-004](spec.md#ac-004) | [test_test_budgets.py](../../../tests/test_test_budgets.py) | Covered — certified PASS; 2026-10-16 |
| [AC-005](spec.md#ac-005) | [test_test_budget_contracts.py](../../../tests/test_test_budget_contracts.py) | Covered — certified contract PASS; delivery review recorded PASS |

## Files Created/Modified

- Read [the plan](plan.md) for the three bounded implementation steps and their exact file responsibility.
- New policy/deadline/child-watchdog/storage/timeout-publication helpers extend existing driver, CLI and evidence APIs; optional model fields retain old receipt readability.
- Pytest freezes category and exception data before tests; Cargo freezes policy in its hashed hook configuration. Both provenance sets include the watchdog helper.
- Four focused test modules, existing Cargo fixture timeout reduced from 600s to 30s, and category markers registered.
- Central scope/review/recovery/testing contracts, spec-plan/test/implement/feature skills and expectation dates, universal spec-system copies and README updated.
- Repaired only existing doctor blockers: factual unfinished feature 035 checkpoint and stale feature 076 mapping pointers; neither unrelated feature is marked completed.

## Evidence and limits

- Initial driver/capture regression: 57 PASS in 7.45s.
- Consolidated policy/deadline/instrumentation/contracts/Cargo/CLI selection: 31 PASS with one cleanup EPERM failure in 13.49s; after handling this observed kernel error as an explicit cleanup diagnostic, affected Cargo/deadline checks: 4 PASS in 2.11s. No assertion or timeout was weakened.
- Final changed-scope Ruff/format and full configured Pyright pass with 0 errors. Atomic SIGALRM restoration was checked after its final source change; final acceptance capture is current.
- Doctor: 0 errors, 23 pre-existing warnings. Inspect [the current conventions receipt](../../conventions/runs/20261016T042049Z/receipt.json): PASS, no errors or blockers.
- A kernel denial while terminating an owned group remains a visible cleanup gap and an unsuccessful timeout. Detached/remote jobs and direct shell/SDK/device surfaces are outside executable interception; unsupported individual hooks report command-only enforcement.
- Independent delivery review is recorded and verified PASS; deterministic feature finalization is verified PASS. Git records repository delivery.

## Current acceptance execution

- Inspect [the test report](.reviews/test-report.md) and [the derived mapping](checks/acceptance-mapping.json): 5/5 AC certified, 5 tests PASS in 1.10s, 0 tests generated.
- Inspect [the current execution receipt](../../.execution/db152036d7224a8c86a9e6cb0bade955/receipt.json): valid=true, all five AC, gaps=[].
- Inspect [the current conventions receipt](../../conventions/runs/20261016T042049Z/receipt.json): PASS, no errors or blockers. Delivery review and feature finalization are recorded and verified PASS.

- Latest acceptance recapture follows annotation-only compatibility correction for CI Pyright 1.1.411 (`Iterator` to `Generator` on two context managers); behavior unchanged. Inspect [the current report](.reviews/test-report.md): all five AC certified with current source bytes.

- Current acceptance recapture follows the final strict-mypy typing-only correction, using the stable global CLI/pytest interpreter. Inspect [the current report](.reviews/test-report.md): five AC certified, gaps=[]. The supervisor reports locked CI-toolchain mypy PASS (779 files), Pyright 1.1.411 PASS (0 errors), Ruff/format PASS and 83 neighboring runner/CLI/evidence regressions PASS in 24.43s; no broad suite was repeated by this phase.

- Current acceptance capture was refreshed once after the four legacy-test compatibility changes entered the source manifest; no production behavior changed. Inspect [the current report](.reviews/test-report.md): valid=true, five AC, 15 assertions, gaps=[]. Existing legacy selection was reported by the supervisor as 51 PASS in 0.81s; this phase ran no other suite.

- Current capture follows the three production-review corrections and the supervisor-refreshed five-binding acceptance mapping: valid=true, 5/5 AC, 15 assertions, gaps=[]. Inspect [the current report](.reviews/test-report.md). The intervening mapping-staleness attempt remains unsuccessful historical evidence; no assertion or requirement was weakened.

## Timeout return guard — 2026-10-18

Read [the managed capture boundary](../../../validator/execution_capture.py) (`@spec FR-001`, `FR-003`) and [the real publication and missing-receipt regressions](../../../tests/test_execution_test_budgets.py). A consumed deadline signal must not leave a successful return: expired non-124 results enter the existing bounded timeout path, while existing124 diagnostics remain unchanged. This scoped correction addresses AC-001/003; earlier whole-feature acceptance remains historical for its original source bytes. The missing implementation frontmatter is repaired so the current structural gate can run. Current proof outcomes are published by the runner and official closure, not inferred from this mapping.

## Atomic API completion — 2026-10-18

Read [the capture boundary](../../../validator/execution_capture.py), [the existing atomic completion protocol](../../../validator/execution_verification.py) and [the all-receipt publication regression](../../../tests/test_execution_test_budgets.py). New ordinary API captures remain provisional until the existing in-deadline atomic completion accepts them; CLI callers still defer completion to their semantic verification. Timeout124 captures remain readable and nonqualifying. The current regression uses a genuine one-assertion pytest pass, an ordinary successful control in a separate project, and every receipt produced by expired publication. No receipt from that expired project may prove a passed observation. Earlier timeout-return-only proofs remain historical; current runner and closure artifacts supply the actual outcomes.
