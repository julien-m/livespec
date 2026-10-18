# Changelog - 095-test-time-budgets

## 2026-10-16 — [Spec]: Specification created: managed command and supported individual test deadlines, prior scoped long-running exceptions, proportional plans and bounded recovery.

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-005
- **Author:** Codex

<!-- finalize:spec-specify:2026-10-16:e7daafa0 -->

## 2026-10-16 — [Plan]: Technical plan generated: shared managed command deadline and strict scoped exceptions; supported pytest/Cargo individual watchdogs; necessary proportional tests and bounded recovery.

- **Type:** Feature
- **Spec modified:** No (lifecycle status only)
- **Code modified:** None (plan.md created)
- **AC impacted:** AC-001 through AC-005 (planned evidence)
- **Author:** Codex

<!-- finalize:spec-plan:2026-10-16:bb751413 -->

## 2026-10-16 — [Test]: 5/5 AC certified with existing necessary tests

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None by spec-test; 0 tests generated
- **AC impacted:** AC-001 through AC-005, Covered / certified PASS
- **Evidence:** Inspect [the test report](.reviews/test-report.md): final 5 PASS in 0.61s, current conventions PASS; independent delivery review remains pending.
- **Author:** Codex

## 2026-10-16 — [Feature]: - **Type:** Feature

- **Spec modified:** Yes — managed command and individual test budgets, declared exceptions, necessary-test and bounded recovery contracts.
- **Code modified:** Strict project policy, managed deadline and process cleanup, pytest/Cargo instrumentation and honest timeout evidence; planning/testing/implementation guidance synchronized.
- **AC impacted:** AC-001, AC-002, AC-003, AC-004, AC-005.
- **Evidence:** Five acceptance tests certify all five ACs with 15 observed passing assertions; current native delivery review and conventions PASS, Ruff/format/Pyright PASS. No exhaustive matrix or generated tests were needed.
- **Review carry-over:** Advisory function-length warnings remain non-blocking; future refactoring must preserve signal and evidence invariants.
- **Consumer boundary:** Existing pinned runtimes receive these guards only after an explicit runtime update; HandoffBox was not modified.
- **Author:** Codex.

<!-- finalize:spec-feature:2026-10-16:d775ec24 -->

## 2026-10-16 — Bugfix: CI-compatible generator annotations

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** `validator/execution_deadline.py`, `validator/execution_test_budget.py`; four annotation/import lines only, preserving behavior.
- **AC impacted:** AC-001, AC-002; all five acceptance criteria recertified with 15 observed assertions.
- **Validation:** Ruff/format, local Pyright, current conventions and refreshed independent delivery review PASS; newer CI Pyright rechecked after push.
- **Author:** Codex

## 2026-10-16 — Bugfix: Strict mypy runner annotations

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** `validator/execution_capture.py`, `validator/execution_pytest.py`; explicit snapshot dictionaries, static-only helper import and wrapper generator typing, preserving runtime behavior.
- **AC impacted:** AC-001 to AC-005 recertified with 15 passing assertions.
- **Validation:** Locked CI dependencies: mypy passes 779 files, Pyright passes, Ruff/format pass, and 83 neighboring execution/CLI regressions pass. Current conventions and refreshed independent delivery review PASS.
- **Author:** Codex


## 2026-10-16 — Bugfix: Preserve existing tests across runner and validation changes

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** Four existing test modules now mock the owned runner boundary and identify execution obligations by their semantic fields; exact arguments, evidence requirements and inactive modes remain asserted. No new cases or production changes.
- **AC impacted:** AC-001 to AC-005 recertified with 15 passing assertions.
- **Validation:** 51 affected tests pass in 0.81s; locked mypy, Pyright and Ruff/format pass. Inspect [the current report](.reviews/test-report.md) for the five acceptance tests and current receipt. Conventions PASS; current independent review is refreshed before commit.
- **Author:** Codex


## 2026-10-16 — Bugfix: Address publication and timeout review findings

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** Publication waits within the managed deadline and closes owned descriptors on expiry; three capture consumers handle absent receipts as non-certifying failures; nested evidence distinguishes the effective remaining budget from the declared maximum.
- **AC impacted:** AC-001, AC-003 and AC-004.
- **Validation:** Three necessary regressions pass in 0.69s and seven affected neighbors pass in 5.94s. Locked Ruff/format/mypy/Pyright and conventions pass; current acceptance and independent delivery review are refreshed before commit.
- **Author:** Codex

## 2026-10-18 — [Bugfix]: Refuse successful capture returns after an expired managed deadline, preserving existing124 diagnostics. Actual receipt `6123a3e50a004a2ebb4969a4fb5961b0` records two targeted tests and five reviewed bindings for AC-001/003 only. Read [the current checkpoint](progress.md#timeout-return-verification--2026-10-18) and [the real publication regressions](../../../tests/test_execution_test_budgets.py). Earlier receipts and the rejected precheck remain historical.

<!-- finalize:spec-fix:2026-10-18:54e97348 -->

## 2026-10-18 — [Bugfix]: Keep every API receipt provisional until existing atomic in-deadline completion, preserving CLI deferral and124 diagnostics. Actual receipt `7159ad511f904dc5b3b2cb0bed87e2ef` records two targeted tests and eight reviewed bindings for AC-001/003 only. Read [the current checkpoint](progress.md#atomic-api-completion-verification--2026-10-18) and [the real publication regressions](../../../tests/test_execution_test_budgets.py). Earlier receipts and the rejected precheck remain historical.

<!-- finalize:spec-fix:2026-10-18:6dd8b550 -->
