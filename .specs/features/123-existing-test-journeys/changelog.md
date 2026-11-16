# Changelog: Existing Test Journeys

## 2026-11-16 — Spec Update: Reference original suites

- **Type:** Spec Update
- **Spec modified:** Yes — reference mode, safe adapters, coverage/impact, compile non-mutation, deduplication, empty/planned outcomes and declared evidence.
- **Code modified:** Pending parallel implementation; documentation worker modified no runtime code.
- **AC impacted:** AC-001 through AC-008.
- **Author:** Codex
- Read [the specification](spec.md), [implementation plan](plan.md) and [reference guide](../../../system/testing/existing-test-journeys.md) before adoption. Consumer runtime adoption and independent final review remain pending.

## 2026-11-16 — Spec Update: Observe native test execution

- **Type:** Spec Update
- **Spec modified:** Yes — AC-004/AC-006 require positive executed-test observations, explicit `selection_status`, `planned` IDs and `planned_commands` argv.
- **Code modified:** Parallel execution changes add JSON/JUnit report validation and execution-only reporter flags; this worker changed documentation only.
- **AC impacted:** AC-004, AC-005, AC-006, AC-007.
- **Author:** Codex
- Coordinator observed 16 new contract/integration checks and 81 existing journey checks passing. Real Vitest all-skipped returned zero and is now rejected from native report counts. Browser/images/product services/provider integrations remain unobserved; independent review is in progress, with no Implemented claim.

## 2026-11-16 — Spec Update: Exact native file selection

- **Type:** Spec Update
- **Spec modified:** Yes — AC-004 exact file selection, native retry interpretation and AC-006 observable no-execution preview.
- **Code modified:** Coordinator correction packages a Vitest Node adapter, filters exact collected realpaths and anchors Playwright file selection; documentation worker changed only these feature documents and the reference guide.
- **AC impacted:** AC-003, AC-004, AC-006, AC-007.
- **Author:** Codex
- The reviewer reproduced neighbouring-file execution with Vitest CLI substring filtering. The adapter uses the consumer's real configuration/public API and closes its context; observed Vitest 4.0.18 does not prove other-version compatibility. Playwright expected/flaky counts accept successful retries without overriding native failures. Final check totals and correction review remain coordinator-owned; no Implemented claim.

## 2026-11-16 — Feature accepted

- Independent final review accepted all material corrections; 18 new tests, 175 existing journey checks and installed-wheel smoke passed. Read [verification](checks/verification.json) and [review](review.md). Atlas runtime adoption remains separately coordinated.
