# Progress: Existing Test Journeys

| Step | Status | Observation |
|---|---|---|
| Spec and plan | Complete | Written before this feature's implementation; additive v2 reference contract accepted by coordinator. |
| Schema and validation | Complete | Dedicated worker owns typed reference and confinement; original test fixtures/config remain authoritative. |
| Catalogue and impact | Complete | Dedicated worker owns list/inspect metadata and test/config dependency matching. |
| Runner and compiler | Complete | Dedicated worker owns direct execution, reference compile skip, dedup and explicit preview/empty outcomes. |
| Reference guide | Complete | Read [the guide](../../../system/testing/existing-test-journeys.md); integrated CLI details remain to verify. |
| Behavioral checks | Observed by coordinator | 16 new contract/integration tests passed with real pytest, Node Playwright fixtures without a browser and Vitest; 81 existing journey tests passed. Vitest exit-zero/all-skipped was observed and corrected with native result validation. |
| Independent final review | Accepted | Fresh native reviewer accepted all four corrections and independently ran 18 new tests. |

## Scope boundaries

No Atlas runtime/global skill changes. Reuse the original tests and fixtures; coverage/evidence declarations remain distinct from observed product proof. Registry, implementation mappings and global changelog are coordinator-owned.

## Native result and preview follow-up

- Success requires an observed positive executed-test count in native JSON/JUnit results; all-skipped/zero selection and invalid reports are explicit errors. Reporter flags and temporary reports apply only during execution.
- The additive result field is `selection_status`; `planned` holds IDs and `planned_commands` holds selected argv without spawning or creating reports.
- Browser rendering, images, product services and provider integrations: NOT OBSERVED. Test counts above are coordinator-provided observations; this documentation worker did not rerun them. Independent review accepted the change; consumer runtime adoption remains separate.

## Exact file selection correction

- The independent reviewer observed Vitest CLI substring filtering execute a neighbouring file. The correction uses the bundled Node adapter with consumer-local `vitest/node`, real configuration, exact realpath filtering of discovered specifications before execution and context cleanup in `finally`. Observed Vitest version: 4.0.18; other versions remain unverified.
- Playwright now anchors the escaped absolute resolved file path. Its expected and flaky report counts establish execution when native exit is zero; nonzero fail-on-flaky remains failure.
- Dry-run argv remains visible through `planned_commands`; no tests execute and no reports are written. Vitest reporter choice lives inside the adapter.
- The coordinator is updating final check totals; correction review with the same independent reviewer remains in progress. Earlier counts above describe their earlier checkpoint, not final acceptance.

## Final verification — 2026-11-16

- 18 new tests pass with real pytest, Playwright fixture-only and Vitest 4.0.18 runners; the reviewer independently reproduced that result.
- 175 existing journey tests pass. The generated dry-run assertion now requires planned, never executed, matching the explicit preview contract.
- Ruff check and format pass for 23 affected journey/CLI/test files. Pyright reports zero errors/warnings for nine affected modules.
- `python -m build` was unavailable (`No module named build`); supported `uv build --offline --wheel` succeeded. Wheel hash and installed CLI/reference smoke are preserved in [the installed proof](checks/installed-wheel.json).
- An early test harness used pytest `-k original`, also matching the filename; it was corrected to the actual test selector `case_original`. This did not change product logic or suppress a failure.
- Build output/scratch consumers are cleaned after verification; the wheel remains available for the owner. No source test was copied into a journey, no Atlas runtime changed and no provider writes occurred.

## CI typing follow-up

The first public CI run found two mypy errors not reported by Pyright: a reference manifest variable was later assigned an optional generated manifest, and the raw test-builder coverage value was typed as object. The reference variable is now distinct; the test builder normalizes through the existing Pydantic boundary. No assertion/behavior was weakened. Targeted mypy and 60 affected tests pass; the same reviewer accepted the correction.
