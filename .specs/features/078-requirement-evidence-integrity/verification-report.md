# Verification Report — Requirement Evidence Integrity

**Frozen implementation checkpoint — 2026-09-06, before final acceptance review/capture.** Read the [implementation map](implementation.md), [progress](progress.md) and [contract](spec.md). This report records results already observed. Subsequent acceptance verdicts belong to the canonical receipts and generated archives; this source-bound report will not be rewritten to add them. Temporary original artifacts may expire and never substitute for current canonical proof.

## Five-axis outcome

| Axis | Implemented and verified | Practical limit |
|---|---|---|
| Complete semantic review | Qualified full-context inventory, bounded comparisons, grounded dispositions/synthesis, exact review identity; independent A findings closed | Citation grounding establishes provenance; actual semantic judgment remains independent. |
| Consequential clarification | Bilingual inventory, approved decisions, complete critical-question retention, source-aware persistence; separate structural/semantic Analyze | Presentation limits cannot discard blockers; technical choices follow conventions. |
| Observable execution | Runner-owned capture, actual assertion observations, independently reviewed mappings, source/report/policy checks; B findings closed | Counts, names, prose and RED observations do not replace mapped passing acceptance assertions. |
| Generation evaluation | Frozen external oracles, Python/API/UI witnesses, explicit scenario/outcome and sample/full selection | Direct generation and prepared UI success do not establish full spec-feature success or runtime parity. |
| Durable progression | Existing shared CLI/native gates, typed acceptance policy 2, scoped preparation and full final conjunction, lifecycle-only finalizer | Final feature proof still requires its actual canonical acceptance receipts and corresponding terminal archive. |

## Final regression and quality evidence

- **Pre-synthesis-delta checkpoint: 3084 passed, 4 skipped in 120.09s:** read the [broad unit output](/tmp/livespec-078-implementation-checks/policy2-final-unit.stdout) and [capture metadata](/tmp/livespec-078-implementation-checks/policy2-final-checks.json).
- **Same pre-delta checkpoint: 13 passed, 3 real-model cases deselected in 5.20s:** read the [witness output](/tmp/livespec-078-implementation-checks/policy2-final-witnesses.stdout). This includes actual prepared UI authority validation. Deselection is not model execution.
- Global Ruff passed; validator Pyright reported zero errors; validator mypy passed for 299 source files. Full mypy remained 294 errors versus 298 at baseline: **zero introduced, four resolved**, compared by file/message/error code. Read the [comparison](/tmp/livespec-078-implementation-checks/policy2-final-mypy-baseline-comparison.json).
- The six remaining full-format findings are byte-identical to initial HEAD: conventions diffguard, multilingual language, taxonomy and verify-scope tests, journey-v2 runner test, and conventions gate source. Read their [baseline classification](/tmp/livespec-078-implementation-checks/policy2-final-format-baseline.json). The final evidence-policy formatting delta was separately approved and independently checked AST-identical; no behavior change was inferred from formatting.
- **Prior checkpoint — Conventions PASS, zero blockers, 239 warnings:** read the [actual receipt](../../conventions/runs/20260906T063131Z/receipt.json). Warnings remain visible. The [strict baseline-aware inventory](/tmp/livespec-078-constitution-inventory.json) records 91 new Python files, zero oversized new files, zero actionable new/rewritten-function violations and 14 classified legacy bridges under the 300/50 limits; no waiver or broadened exclusion was added.
- Earlier scoped results remain historical and overlap the final suite: 243 lifecycle/evidence tests, 129 typed-policy/goal tests, and pipeline/finalizer extraction checks. All 20 changed canonical command inventories compiled without unclassified tasks; matching expectation dates were reviewed. Do not sum overlapping counts as independent tests.

```bash
.venv/bin/pytest tests --ignore=tests/integration -q
.venv/bin/pytest tests/integration/test_generation_witnesses.py tests/integration/test_prepared_ui_authority.py -m 'not level_3c' -q
```

The captured environment prepended the virtualenv bin directory to PATH, including the real Penflow entrypoint. Earlier missing-PATH and in-flight failures remain historical; they are not erased by the final passing results.

## Independent review and honest gate ordering

- Read the bounded [A review](/tmp/livespec-078-a-review.json), [B review](/tmp/livespec-078-b-review.json) and [C review](/tmp/livespec-078-c-review.json). Original findings and later resolutions remain recorded; C ends in PASS_BOUNDED, including process-control and helper-extraction rechecks.
- Read the final [typed-AC policy 2 review](/tmp/livespec-078-typed-ac-policy2-final-review.json): PASS, no remaining findings, 28 reviewed hashes and separately inspected AST-identical format delta. The reviewer independently ran 22 parser/archive tests and 15 capture/join/review tests, reran original bypass probes and rejected them. Author-reported broader suites are identified separately in that artifact.
- Read the [integration freeze](/tmp/livespec-078-policy2-integration-freeze.json) for code identity and exact CLI transport. Its worklist was a historical freeze checkpoint; the final regression captures above supersede its then-outstanding combined-check item.
- Read the [gate-order record](/tmp/livespec-078-policy2-gate-order.json): nine actual artifact hashes preserve the initial blocking scope review, stale ingestion rejection and successive normative freezes. A parser-only, unconnected file existed before fresh semantic gates while active policy remained 1; implementation then paused. Current scoped SPEC/PLAN, Clarify, Analyze and progression all passed before supervised behavior implementation resumed. No clean ordering is invented for the earlier exception.
- Scoped final native SPEC is complete/ready at context `5fd77c33bfa4f037291c99c969909e6d61498859c139bac94674dbe0fdeec533`; PLAN is complete/ready at `89347a95465cdfdf9184182de2d4292d43dfbfdaf7dc4074eb0c99c1252aaabd`. Clarify reported no blocker, Analyze no finding and progression READY. Historical v1 and intermediate policy-2 review outputs remain historical; consumption must independently recheck current source/model/policy identity.

## Acceptance proof and final authority

Policy 2 uses **15 execution ACs plus AC-016 in independent documentary review**. Only resolved execution tasks with existing `ac-scope:feature`, excluding RED observations, require the complete final conjunction. Preparatory documentary/review tasks and targeted tests retain their own declared scopes; no future runtime proof is required merely to prepare a source or review.

At this freeze, the runtime mapping proposal contains 244 bindings across 29 tests; it has not yet been published with a final accepted review. The earlier mapping context `5c370` was reviewed FAIL and remains preserved. A large proposal or this report is not certification. Documentary review must inspect the actual migration dataset with per-file provenance; unknown initial 076 baselines stay unknown.

Read the canonical [assertion-mapping review](.reviews/acceptance-review.json) and the distinct [documentary AC review](.reviews/acceptance.json) when produced. The former validates assertion-to-behavior mappings; the latter certifies the review-kind AC scope. Final task evidence supplies `execution_receipt_path` and `acceptance_review_receipt_path` as required by its immutable declaration. Their actual current verdicts and the generated terminal archive are the final authority, not a predicted status in this frozen report.

```bash
livespec validate .specs/features/078-requirement-evidence-integrity --prepare-review acceptance --model <actual-model> --review-max-chars 200000
livespec validate .specs/features/078-requirement-evidence-integrity --ingest-review <actual-raw-bundle.json> --review-kind acceptance --model <actual-model> --review-max-chars 200000
```

The actual native raw output, linked source inputs, purpose and model/budget are bound to the documentary receipt. Final proof, archive and verify-output recheck the full immutable AC conjunction; deleting a receipts-list item cannot delete an obligation. Ordinary plan review cannot substitute for acceptance review. Unknown policy, conflicting AC kind, stale manifest, transient source reads and wrong runner stamps reject certification.

New policy-2 archive filenames end in `-policy2.json`; validation checks the resolved actual path, intact canonical policy 2, goal hash, command and mirrors. Legacy archives retain their original interpretation. This local path/provenance authority is **not cryptographic authentication against wholesale replacement and renaming as a legacy file**. Existing path confinement, bootstrap pairing, publication and Penflow gates remain active.

## Generation observations and limits

| Trial | Observed result | Scope |
|---|---|---|
| Read [Codex Python](/tmp/livespec-078-witness-python-codex.json) | First-attempt success, 62.94s, four assertions | Direct native generation; model/cost unknown in the artifact. |
| Read [Claude Python](/tmp/livespec-078-witness-python-claude.json) | First-attempt success, 114.36s, four assertions; measured 2.4820225USD | Direct native generation; artifact model null, parent runtime journal separately reports claude-fable-5-1. |
| Read [Codex API v2](/tmp/livespec-078-witness-api-codex-v2.json) | First-attempt success, 68.74s, six HTTP/persistence assertions | Parent-owned independent oracle; exact historical oracle hash, model/cost unknown. |
| Read [UI trial](/private/tmp/livespec-native-form-Wq7xbl/ui-witness-trial-report.json) | Repaired implementation success after one allowed repair; three mutants rejected | Prepared/direct native generation with browser and implementation C51 proof, not a full workflow trial. |
| Read [full pipeline v4](/tmp/livespec-078-full-pipeline-codex-v4.json) and [summary](/tmp/livespec-078-full-pipeline-v4-summary.json) | Natural failure after 857.53s, no timeout, no successful closure | No purge.py, no behavioral oracle execution or assertions. First Specify finalization invalidated its review; deterministic regression now covers the fix, but no fifth full trial or pipeline PASS is claimed. |

The API v1 result used an impersonable oracle and is noncertifying. Later oracle/scenario updates also mean earlier trial hashes remain historical observations, not fresh certification of the current evaluator. No old report was edited and no model rerun was inferred.

AC-012 `correct_blocked` now has a precise observable meaning: the API `unauthorized` scenario is selected and frozen **before generation**, and the independent oracle verifies HTTP403 plus identical persisted bytes, two assertions. The default full API scenario retains six assertions and ordinary first/repaired success outcomes. A blocked pipeline, absent capability, timeout or runtime error is never `correct_blocked`; no fourth witness was introduced. The separate prepared-UI API smoke was `runtime_failed`, not a successful retry.

UI candidate SHA `3154f1a325ba9874a1e3fd7346c4e6bf3bf897dc49708dff98d380b06da94bd2` was restored after the bounded smoke. Read the current [independent implementation validation](/tmp/livespec-078-ui-final-authority-validation.json): implementation PASS against [runner manifest ec228](/private/tmp/livespec-native-form-Wq7xbl/consumer/.witness-runner/ec228acf7ad44625982bef77f2668e19/build-manifest.json). Missing-required-input, double-submit and wrong-button-width mutants failed. Design authority alone never certified implementation.

Inspect the [original visual](/private/tmp/livespec-native-form-Wq7xbl/consumer/penflow/.mockup-validation/visual-evidence/HYJmS.png) through the recorded [local annotation view](http://127.0.0.1:4175/i/42633c10a3ef). This is an inspection aid; current receipt/manifest identity carries certification. Local process observation does not attest remote/native-backend cancellation; uncontrolled trials remain incomplete and retain their workspace.

## Compatibility and preserved baseline

Read the [goal extraction review](/tmp/livespec-078-goal-extraction-review.json): all 15 delegates plus public facade inspected, 83 original symbols retained, 74 AST-equivalent after dependency-lookup normalization and nine manually checked. The 69 exact compile/render/hash/state equivalence cases and 357 bootstrap/proof/archive tests concern that extraction snapshot; they are not a claim that intentional policy-2 behavior is identical to policy 1.

Read the parent [preservation check](/tmp/livespec-078-parent-preservation-check.json): 19 initially preserved paths identical, 10 reviewed deltas, zero missing. These facts apply only to observed baseline bytes; unavailable initial 076 content is not reconstructed from HEAD or claimed globally unchanged. Generated registries, the public goal facade and tests have separately attributed deltas.

The narrow initial-076 integration changes are documentary-kind metadata in synthetic fixtures; actual model binding before CLI goal emission; typed policy/receipt revalidation in run artifact construction; and a one-line policy-2 archive filename suffix. The run builder records immutable policy, derives task declarations from canonical metadata, preserves RED outcome when checking receipts, forwards current feature/model/budget, and revalidates completed typed tasks. Its persisted evidence errors force receipt/verify-output failure. Pure helper extraction preserves those behaviors; existing JSON typing, ownership, paired-root confinement and publication are retained. Read the [implementation notes](implementation.md#narrow076-compatibility-changes).

## Closure after this freeze

All eight implementation steps have completed their code and regression work. This report is intentionally frozen before the independent final mapping review, AC-016 dataset review and actual acceptance capture. Those operations publish their real accepted/rejected verdicts in canonical receipts and generated archives; this report does not forecast them or need rewriting afterward.

The parent archives spec-implement with feature status In Progress. Root records pipeline Implement Done, proceeds to independent Test and alone decides final status from current evidence. Finalization requires no preparatory body marker. Neither implementation-step completion nor finite witness success is a universal10/10 guarantee.

## Final bounded synthesis delta — 2026-09-06

Read the [actual frozen delta](/tmp/livespec-078-synthesis-transport-delta/freeze.json) and [transport proof](/tmp/livespec-078-synthesis-transport-delta/transport-proof.json). Five files changed: synthesis transport, receipt producer, native consumer, dedicated regression and context fixture. Multi-batch transport version 2 deduplicates repeated exact lists and reconstructs the original raw results byte-for-byte; judgments, citations, issue ledgers and complete coverage remain intact. The actual prompt shrank from 246526 to 176772 characters. Producer and native consumer both enforce the synthesis budget.

Read the [targeted output](/tmp/livespec-078-synthesis-transport-delta/pytest.stdout.txt): 38 tests passed; scoped Ruff, Pyright, mypy and 300/50 checks passed. The global 3084/4 and corpus 13/3 figures above describe the preceding checkpoint, not a rerun after this delta; independent Test will capture current final results in its canonical report/archive.

Read the latest [conventions receipt](../../conventions/runs/20260906T071617Z/receipt.json): PASS, zero blockers and 238 warnings, receipt hash `1c5b8748d9247d551154760faeee6b106b54467c83a4e920ccdc7e76e06b056a`. Its gates identity remains `6b45fc4b27b41cb91f5df004995ef590f38312729105308559a8b08d673f2361`; the earlier 239-warning receipt remains a dated checkpoint.

The new prepared runtime mapping retains all 244 binding identities at context prefix `b88c97b04b50`; 19 span hashes were refreshed and four changed batch prompts were reread natively. No final acceptance PASS is inferred. Canonical assertion-mapping/documentary receipts and generated execution/terminal archives publish the actual subsequent verdicts. Feature finalization is already In Progress; this final factual amendment changes no lifecycle status and is frozen before AC-016 current-input hashing.

## Final observed-bytecode delta — 2026-09-06

The historical [execution receipt](../../.execution/7234a856e2bf453fb6300a372cdddef2/receipt.json) represents 482 passing tests but zero assertion callbacks, 244 mapping gaps and zero certified ACs. A warmed pytest bytecode cache had been compiled without the assertion-pass hook. This failure is retained; no AC success follows from the passing case count.

Read the [new regression](../../../tests/test_execution_bytecode.py) and independent [review](/tmp/livespec-078-bytecode-review.json): PASS_BOUNDED, no findings, exact capture/test source hashes. The one-line capture change forces an invocation-owned `PYTHONPYCACHEPREFIX` after caller environment values. Two variants test absent/existing inherited prefixes with real prewarmed pytest bytecode; actual assertion observation and scoped AC certification succeed while old cache bytes remain exact. This is cache isolation for supported capture, not a sandbox against arbitrary interpreter options or candidate-controlled launchers; no verifier rule was weakened.

The owner reported **87 targeted tests passed in 64.45s**, plus Ruff, Pyright, mypy and 300/50 checks. The independent reviewer inspected these frozen sources and tests but did not execute another suite or acceptance capture. The global 3084/4 and corpus13/3 checkpoints above remain earlier results; no new final capture success is predicted.

Read the latest [conventions receipt](../../conventions/runs/20260906T074804Z/receipt.json): PASS, zero blockers and 244 warnings, receipt hash `173e7aaaa2c436aadee35a88ab30c3373d929130ed79febf1613b2a44281c801`. Earlier warning counts remain dated checkpoints. This factual note is frozen before refreshing AC-016 inputs; subsequent assertion-mapping, documentary and execution receipts/generated archives publish the actual final acceptance verdicts.

## Final lossless transport-3 delta — 2026-09-06

Read the [measurements](/tmp/livespec-078-transport3-measurement/report.json), independent [review](/tmp/livespec-078-synthesis-v3-review.json) and [targeted test log](/tmp/livespec-078-transport3-tests.log). PASS_BOUNDED has no findings and binds three source/test hashes. A separate stdlib-only decoder reconstructed all nine current AC-016 raw UTF-8 responses and all eight mapping responses exactly, including ordered global sections, requirement records, invariants and batch identities; historical issue ledgers and other nontransport fields also remained identical. The reviewer independently performed reconstruction and read the59-test/static logs, without claiming another test-suite run.

Transport version 3 reversibly factors string tokens, IDs and shared prefixes. Current AC-016 synthesis measures189781 characters within250000; mapping measures138410 within200000. The historical nine-response version-2 prompt of425855 characters remains a preserved over-budget result. No source text, original raw judgment or obligation is discarded. Producer and native consumer still reject synthesis beyond the same declared budget.

The 29 mapped tests,244 binding identities, prepared context `b88c97b04b50261b5f9e401eec7c4a6214bef74f85b6107d6f21d3ad68b46872` and all eight original batch prompts are unchanged. Current single-batch SPEC/PLAN receipts remain valid. The older multibatch mapping receipt must be re-ingested through the actual version-3 CLI; this note does not predeclare that ingestion or final acceptance as PASS.

The new targeted checkpoint is **59 passed in11.41s**, with Ruff, Pyright and mypy passing. The earlier global3084/4, corpus13/3, cache-fix87 tests and failed482-tests/zero-observation capture remain their exact historical checkpoints. Read the latest [conventions receipt](../../conventions/runs/20260906T080713Z/receipt.json): PASS, zero blockers,248 warnings; receipt hash `4c460636836dbafa3a21dfc9b595eca949080ac2ee805578d213ee2c1479171e`, unchanged gates identity `6b45fc4b27b41cb91f5df004995ef590f38312729105308559a8b08d673f2361`. This last factual note is frozen before the final documentary input-manifest refresh. Canonical receipts and generated archives remain the authority for subsequent real verdicts.
