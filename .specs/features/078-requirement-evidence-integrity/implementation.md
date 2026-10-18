---
title: Requirement Evidence Integrity implementation
feature: 078-requirement-evidence-integrity
---

# Implementation — Requirement Evidence Integrity

Read the [contract](spec.md), [approved plan](plan.md), [progress](progress.md) and [verification report](verification-report.md). All five axes and eight implementation steps are implemented and regression-tested. This map is frozen before final acceptance capture; canonical receipts and generated archives publish the actual later verdicts. Source links are traceability, not proof receipts.

## Requirement Mapping

| Requirement | Acceptance scope | Implementation | Regression coverage |
|---|---|---|---|
| FR-009 (2026-10-17) | AC-007, AC-015 | Read [canonical Test tasks](../../../.agent-sync/skills/spec-test/SKILL.md#phase-4--execute-test-suite), [Test expectations](../../../.agent-sync/skills/spec-test/expectations.md#3-observable-signals) [command applicability](../../../validator/evidence_applicability.py) and [typed command binding](../../../validator/evidence_policy.py) (`@spec FR-009`). | Read [the real observation regression](../../../tests/test_spec_test_observations.py); this maps the bounded fix, not full feature acceptance. |
| FR-011 (2026-10-17) | AC-009, AC-010 | Read [actual transport binding](../../../validator/evidence_applicability.py). | Read [the real Native Node22 transport regression](../../../tests/test_suite_transport.py); two genuine runtimes distinguish capture-time PATH from proof-time PATH. Read [the Cargo proxy declaration regression](../../../tests/test_suite_cargo_transport.py), which executes no compiler. |
| FR-009, FR-016 | AC-007, AC-015 | Verified 2026-10-16: read [typed policy](../../../validator/evidence_policy.py) and [acceptance conjunction](../../../validator/acceptance_evidence.py). | Read [documentary-only boundary tests](../../../tests/test_documentary_only_acceptance.py). |
| FR-001 | AC-001, AC-002 | Read [qualified inventory](../../../validator/semantic/review_context.py). | Read [context tests](../../../tests/test_review_context.py). |
| FR-002 | AC-002 | Read [complete batches](../../../validator/semantic/review_batches.py), [synthesis](../../../validator/semantic/review_synthesis.py) and [lossless synthesis transport](../../../validator/semantic/review_synthesis_transport.py). | Read [paired-plan/blocker tests](../../../tests/test_review_batching.py) and [transport/budget tests](../../../tests/test_review_synthesis_transport.py). |
| FR-003 | AC-003 | Read [grounded validation](../../../validator/semantic/review_contract.py) and [semantic Analyze](../../../validator/semantic_analysis.py). | Read [semantic gate tests](../../../tests/test_gate_review_evidence.py). |
| FR-004 | AC-002, AC-004 | Read [review receipts](../../../validator/semantic/review_receipts.py), [v2 identity](../../../validator/normative_identity.py) and [metadata bounds](../../../validator/lifecycle_metadata.py). | Read [context tests](../../../tests/test_review_context.py), [legacy001/077 tests](../../../tests/test_lifecycle_metadata.py) and [freshness tests](../../../tests/test_progression_integrity.py). |
| FR-005 | AC-004 | Read [structural analysis](../../../validator/pre_impl_analysis.py) and [pure report rendering](../../../validator/pre_impl_render.py); semantic contradiction comes from grounded review. | Read [Analyze tests](../../../tests/test_pre_impl_analysis.py). |
| FR-006 | AC-005 | Read [bilingual detection](../../../validator/clarify_gate.py) and [review/context inventory](../../../validator/clarify_inventory.py). | Read [clarification tests](../../../tests/test_clarify_gate.py) and [approved-context tests](../../../tests/test_gate_review_evidence.py). |
| FR-007 | AC-006 | Read [complete ambiguity inventory](../../../validator/clarify_inventory.py). | Read [six-question/noncritical-choice tests](../../../tests/test_gate_review_evidence.py). |
| FR-008 | AC-006 | Read [decision persistence](../../../validator/clarify_decisions.py) and [existing CLI](../../../validator/cli_commands/clarify_io.py). | Read [ID-preservation tests](../../../tests/test_gate_review_evidence.py) and [stale-answer tests](../../../tests/test_progression_integrity.py). |
| FR-009 | AC-007, AC-015 | Read [typed policy](../../../validator/evidence_policy.py), [AC inventory](../../../validator/acceptance_requirements.py), [acceptance conjunction](../../../validator/acceptance_evidence.py), [receipt verification](../../../validator/run_requirement_receipts.py) and [archive receipt types](../../../validator/run_receipt_types.py). | Read [typed proof/archive tests](../../../tests/test_evidence_policy.py), [review-kind consumers](../../../tests/test_review_kind_consumers.py), [review-kind archives](../../../tests/test_review_kind_archives.py) and [fix execution scope](../../../tests/test_fix_execution_scope.py). |
| FR-010 | AC-008 | Read [capture](../../../validator/execution_capture.py), [pytest observations](../../../validator/execution_pytest.py), [mapping review](../../../validator/execution_mapping.py) and [verifier](../../../validator/execution_evidence.py). | Read [real assertion/provenance tests](../../../tests/test_execution_evidence.py). |
| FR-011 | AC-009, AC-010 | Read [reports](../../../validator/execution_reports.py), [source scope](../../../validator/execution_scope.py) and [driver integration](../../../validator/drivers/runner.py). | Read [stale/foreign/empty/skipped/custom-driver controls](../../../tests/test_execution_evidence.py). |
| FR-012 | AC-011 | Read [external evaluator](../../../tests/integration/helpers/witness_evaluator.py) and [Penflow capture](../../../tests/integration/helpers/witness_penflow.py). | Read [seeds/mutants](../../../tests/integration/test_generation_witnesses.py) and [capture tests](../../../tests/test_witness_penflow.py). |
| FR-013 | AC-011, AC-012 | Read [native generation](../../../tests/integration/helpers/witness_generation.py), [snapshots](../../../tests/integration/helpers/witness_snapshot.py), [process control](../../../tests/integration/helpers/witness_process.py) and [SDK lifecycle](../../../tests/integration/helpers/sdk_runner.py). | Read [trial tests](../../../tests/test_generation_trials.py), [workspace/control tests](../../../tests/test_generation_workspace.py) and [SDK lifecycle tests](../../../tests/test_sdk_runner_lifecycle.py). |
| FR-014 | AC-013 | Read [selection](../../../tests/integration/helpers/generation_selection.py), [opt-in evaluation runner](../../../tests/integration/helpers/generation_ci.py) and [workflow](../../../.github/workflows/ci.yml). | Read [selection tests](../../../tests/test_generation_selection.py) and [private corpus wiring tests](../../../tests/test_generation_ci_selection.py) and [deterministic GitHub policy tests](../../../tests/test_generation_ci_events.py). Runtime completion remains separate from selection. |
| FR-015 | AC-014 | Read [shared progression](../../../validator/progression_gate.py), [pipeline](../../../validator/pipeline.py), [review validation](../../../validator/pipeline_review_validation.py), [approval recovery](../../../validator/pipeline_approval_write.py) and [native protocol](../../../system/review-protocol.md). | Read [direct/nested tests](../../../tests/test_progression_integrity.py), [publication tests](../../../tests/test_pipeline_gate_publication.py), [rollback tests](../../../tests/test_pipeline_approval_rollback.py), [CLI dispatch](../../../tests/test_gate_cli_dispatch.py) and [generation gates](../../../tests/test_spec_test_progression_contract.py). |
| FR-016 | AC-015, AC-016 | Read [versioned policy](../../../validator/evidence_policy.py), [documentary acceptance review](../../../validator/semantic/acceptance_review.py), [lifecycle finalizer](../../../validator/finalize_spec.py) and [058 amendment](../058-deterministic-finalization/spec.md#fr-002). | Read [legacy policy tests](../../../tests/test_evidence_policy.py), [legacy archive CLI tests](../../../tests/test_verify_output_legacy_policy.py), [review-kind archive compatibility](../../../tests/test_review_kind_archives.py), [finalizer tests](../../../tests/test_finalize_lifecycle.py), [first CLI closure](../../../tests/test_finalize_review_boundary.py) and [077 identity tests](../../../tests/test_penflow_requirement_source.py). |

## Documentary-only acceptance correction

Read [the regression tests](../../../tests/test_documentary_only_acceptance.py): policy2 final acceptance resolves receipt kinds from the nonempty canonical AC inventory. All-review proofs retain complete current review validation at prove, archive and archive-read; mixed/execution requirements, fix selection and RED/GREEN observations keep their previous guards.

## Acceptance Criteria

Derived from the requirement mapping above (no new claim): each AC is covered by the regression tests listed on its requirement rows; scoped verdicts and receipts remain in the [verification report](verification-report.md). Source anchors use `@spec` comments, for example `# @spec FR-008: Accepted source decisions` in [clarify_decisions.py](../../../validator/clarify_decisions.py).

| AC | Requirement rows |
|---|---|
| AC-001 | FR-001 |
| AC-002 | FR-001, FR-002, FR-004 |
| AC-003 | FR-003 |
| AC-004 | FR-004, FR-005 |
| AC-005 | FR-006 |
| AC-006 | FR-007, FR-008 |
| AC-007 | FR-009 |
| AC-008 | FR-010 |
| AC-009 | FR-011 |
| AC-010 | FR-011 |
| AC-011 | FR-012, FR-013 |
| AC-012 | FR-013 |
| AC-013 | FR-014 |
| AC-014 | FR-015 |
| AC-015 | FR-009, FR-016 |
| AC-016 | FR-016 |

## Behavior and process

Existing commands prepare complete context, preserve actual independent raw review output and ingest it through one validator. Actual runtime model identity and policy govern reuse. Clarify retains every critical question while presenting a bounded list; accepted decisions preserve IDs. Analyze reports structural reference coverage separately from semantic readiness. Direct and nested commands use the same progression authority.

Execution evidence records actual runner invocation and passing assertion observations. Mapping review justifies the AC/test/assertion relationship against exact source spans. Verification checks current scope and immutable capture instead of a supplied success flag. A failing assertion observation can prove a RED task only; it cannot certify acceptance.

Generated review/run artifacts are disposable caches. Users continue using existing commands; no mandatory extra document, hosted service or recurring review step was introduced. Read the [shared protocol](../../../system/review-protocol.md) and [execution rules](../../../system/testing/execution-rules.md) for internal adapters.

## Lifecycle compatibility

Finalization changes recognized lifecycle metadata only. It never inserts a spec body marker; historical comments remain untouched and generated registries/receipts retain full payload/status history. Explicit Header and legacy introductory H1 metadata use one bounded parser. Duplicate/competing bands, malformed YAML and fenced/body examples cannot become metadata authority. CRLF bytes remain exact. Normative Identity v2 invalidates prior policy identities; current native reviews must refresh after this upgrade.

## Verification status

Read the [durable report](verification-report.md) for scoped results, original trials, historical failures and remaining closure. Deterministic reviewer fixtures test validation mechanics, not model judgment quality. Direct code-generation success does not establish full spec-feature success, runtime parity or a 10/10 result.

## Narrow076 compatibility changes

Read the [parent preservation check](/tmp/livespec-078-parent-preservation-check.json): 19 observed baseline paths identical, 10 attributed deltas, zero missing. Unavailable initial 076 bytes remain unavailable; these comparisons never assert blanket preservation of an unknown baseline.

- Read [bootstrap test support](../../../tests/goal_bootstrap_support.py): explicit documentary evidence metadata added to synthetic fixtures.
- Read [goal CLI actions](../../../validator/goal_cli_actions.py): actual model binding before goal emission, with early failure before an unusable model-bound contract.
- Read [run builder](../../../validator/goal_run_builder.py): immutable policy version and canonical task declarations govern revalidation; RED outcomes and current feature/model/budget propagate to receipt checks. Completed typed tasks are independently revalidated; evidence errors force receipt/verify-output failure. Helper extraction preserves that intended behavior. Initial JSON typing, ownership, paired roots and confinement remain.
- Read [archive paths](../../../validator/goal_archive_paths.py): new policy-2 filename suffix is the narrowly reviewed compatibility bridge. The resolved name requires intact canonical policy 2 and matching mirrors. Wholesale replacement plus renaming as legacy is outside cryptographic authentication; local provenance is not a signature.

## Policy 2 final acceptance scope

Read [AC declarations](../../../validator/acceptance_requirements.py), [conjunction verification](../../../validator/acceptance_evidence.py) and [native acceptance review](../../../validator/semantic/acceptance_review.py). Fifteen ACs require execution; AC-016 requires independent review of the actual declared migration dataset. Only final resolved execution tasks with `ac-scope:feature`, excluding RED observations, require the complete conjunction. Preparatory tasks/archives keep individual typed scope. Canonical policy 1 remains readable with its original interpretation and cannot certify a current policy-2 run.

The canonical assertion-mapping review and documentary acceptance review are distinct artifacts; the latter uses existing validation prepare/ingest with review kind acceptance. Final tasks submit execution and acceptance-review receipt paths. Archive retains immutable evidence_contract and independently rechecks declared obligations even if receipt references are omitted. Read the [frozen verification report](verification-report.md) for exact CLI, current tests and final authority locations.

## Witness outcome scope

The API unauthorized scenario is selected before generation and can produce correct_blocked only after independent HTTP403 and unchanged-storage assertions. The full API scenario keeps six assertions and ordinary first/repaired outcomes. Pipeline blocking, unavailable runtime and timeout are not correct_blocked. Historical direct/prepared successes and full-pipeline failures remain distinct; no fifth full trial is claimed.

Parent archives implementation at feature status In Progress. Root advances Implement Done→Test and decides final status from actual canonical evidence. This map is frozen before that capture and is not rewritten to forecast a verdict.

## Bounded synthesis transport correction

Read the [frozen five-file delta](/tmp/livespec-078-synthesis-transport-delta/freeze.json), [transport](../../../validator/semantic/review_synthesis_transport.py), [producer](../../../validator/semantic/review_receipts.py), [consumer](../../../validator/semantic/review_contract.py) and [regressions](../../../tests/test_review_synthesis_transport.py). For FR-002/FR-004, version 2 shares repeated exact inventory lists and reconstructs every original raw response byte-for-byte. Judgments, citations, issue ledgers and coverage scope are preserved; both producer and native ingestion reject an over-budget synthesis. The observed prompt shrank from 246526 to 176772 characters without truncation. Thirty-eight targeted tests and scoped Ruff/Pyright/mypy passed; 300/50 limits hold. This bounded delta follows the earlier global checkpoint; independent Test will re-run the final suite.

## Observed-assertion bytecode correction

For FR-010/AC-008, read the [real warm-cache regression](../../../tests/test_execution_bytecode.py) and [capture runner](../../../validator/execution_capture.py). A preexisting pytest bytecode cache lacked the assertion-pass hook, so passing tests alone produced no certifiable observations. The invocation now sets its own fresh `PYTHONPYCACHEPREFIX` after caller environment values; existing cache bytes are preserved. The regression warms a real uninstrumented cache, exercises both caller-prefix variants, then observes an assertion and certifies its test AC while checking the old cache remains byte-identical. Read the independent [bounded review](/tmp/livespec-078-bytecode-review.json): PASS_BOUNDED, no findings; the reviewer inspected source/tests without running a new capture. Owner-reported 87 targeted tests and scoped quality checks passed; final feature acceptance still comes from its actual canonical capture.

## Lossless synthesis transport version 3

For FR-002/FR-004, read the [transport](../../../validator/semantic/review_synthesis_transport.py), [string/prefix regressions](../../../tests/test_review_synthesis_strings.py), retained [budget tests](../../../tests/test_review_synthesis_transport.py) and independent [bounded review](/tmp/livespec-078-synthesis-v3-review.json). Version 3 reversibly shares complete string tokens, IDs and common prefixes while preserving the raw byte streams, global ordered inventory, requirements, invariants, batch IDs and issue ledgers. An independent stdlib-only decoder reconstructed all nine AC-016 and eight mapping responses exactly. The observed prompts fit their unchanged declared budgets:189781/250000 and138410/200000 characters. Producer and consumer retain the same strict budget check.

Read the [measurements](/tmp/livespec-078-transport3-measurement/report.json) and [test log](/tmp/livespec-078-transport3-tests.log) for the pre-audit checkpoint of 2026-09-06: 59 targeted tests passed in 11.41s and static checks passed. At that checkpoint, the monobatch SPEC/PLAN reviews and the 29 mapped tests, 244 bindings and mapping context b88c97b04b50 were unchanged. Subsequent audits changed two mapped test fixtures; this historical context is not a current freshness claim. Older multibatch transport-2 receipts remain readable but require actual CLI re-ingestion for current reuse. Current acceptance depends on the source-bound canonical receipts and archives, not this checkpoint.


## Corrections from audits 1–3

Review purpose now follows the immutable task declaration through proof, archive and verify-output. Read [receipt verification](../../../validator/run_requirement_receipts.py) and [archive receipt types](../../../validator/run_receipt_types.py): a spec review cannot satisfy a required plan review, and a changed receipt mirror cannot replace the canonical purpose. Historical contracts without a declared purpose retain their original interpretation. Absent, legacy and policy-1 archive versions select policy 1; only an explicit policy 2 selects policy 2. Read the [kind/archive regressions](../../../tests/test_review_kind_archives.py) and [legacy CLI regression](../../../tests/test_verify_output_legacy_policy.py).

Read [spec-fix](../../../.agent-sync/skills/spec-fix/SKILL.md) and [scope regressions](../../../tests/test_fix_execution_scope.py). Fixes run current implementation readiness before code/test writes and after relevant changes or retries, forwarding the same model and budget. Filtered fixes require actual execution evidence for their selected scope; only an unfiltered feature fix requires the full 15-execution-plus-one-review conjunction. Collection mode delegates to feature children, preserving filters and identity, and reads their actual contracts/states. Compilation tests exercise those obligations; they do not establish that a complete native model workflow ran.

Read [spec-test](../../../.agent-sync/skills/spec-test/SKILL.md), [generation entrypoint tests](../../../tests/test_spec_test_progression_contract.py), [real batch gate regression](../../../tests/test_spec_test_batch_gate.py) and [hook inventory tests](../../../tests/test_spec_test_hook_inventory.py). Phase 3, Phase 4.5.1 and confirmed regeneration check the same real progression CLI before each affected feature's test writes. Batch execution records feature, command, identity, exit code and raw output, then stops before writing the failing feature. The bounded regression lets ready A write and rejects stale B without writing B; it is not full acceptance certification. Audit-only, no-generate, preview and dry-run paths do not acquire a generation obligation; dry-run overrides confirmation. The documentary task attests the actual gate call without introducing another global semantic review. Global, project and local hook resolution remains explicit.

Read [pipeline validation](../../../validator/pipeline_review_validation.py), [publication recovery](../../../validator/pipeline_approval_write.py), [publication tests](../../../tests/test_pipeline_gate_publication.py), [rollback tests](../../../tests/test_pipeline_approval_rollback.py) and [CLI dispatch tests](../../../tests/test_gate_cli_dispatch.py). Readiness/closure checks precede eligible approval publication; terminal replay retains the authority that closure certified. Handled phase-write failures restore the matching prior phase and approval, detect conflicting bytes and report failed recovery. Immutable archives remain; process death and noncooperating writers are outside a multi-file atomicity guarantee. Explicit execution/review preparation and clarification paths return without unrelated test/review fallthrough.

Read [SDK lifecycle](../../../tests/integration/helpers/sdk_runner.py) and its [regressions](../../../tests/test_sdk_runner_lifecycle.py): only supported successful terminal results count as SDK completion; unknown stops remain incomplete. The transport closes on completion, timeout and cancellation. Returned workspaces remain available for independent evaluation and belong to the caller until closed; unreturned cancelled workspaces are cleaned up. SDK completion remains separate from the behavioral oracle. Read the [CI selector regression](../../../tests/test_generation_ci_selection.py): full evaluation considers Claude and Codex, sampling remains bounded, and manual runtime selection is preserved.

Read [pure report rendering](../../../validator/pre_impl_render.py) for the analyzer extraction: public re-exports and rendered output are preserved. These audit corrections add no user command or workflow phase. Earlier suite totals and capture identities in this map, the progress document and verification report remain dated checkpoints; this update claims no new final audit, native workflow or acceptance PASS.

## Corrections from audits 4–12

The following mapping records implemented corrections and their bounded regressions; it does not promote historical receipts to current acceptance.

| FR / AC | Current implementation and behavior | Regression sources |
|---|---|---|
| FR-005 / AC-004 | Read [Analyze](../../../validator/pre_impl_analysis.py): missing canonical artifacts retain CRITICAL diagnostics before semantic preparation; structural findings use qualified identities. | Read [missing-artifact cases](../../../tests/test_pre_impl_missing_artifacts.py) and [finding identities](../../../tests/test_analysis_finding_identity.py). |
| FR-006–008 / AC-005–006 | Read [Clarify](../../../validator/clarify_gate.py): each English/French claim has its own applicable metric and identity; exact duplicates merge, alternatives remain distinct. Capacity requires a noun; vulnerability counts and error-rate percentages accept bounded relevant forms and reject glued labels or neighboring metrics. Read the aligned [069 contract](../069-clarify-gate/spec.md). | Read [claim identity](../../../tests/test_clarify_claim_identity.py), [French forms](../../../tests/test_clarify_french_forms.py), [alternatives](../../../tests/test_clarify_alternatives.py) and [outcome metrics](../../../tests/test_clarify_outcome_metrics.py). |
| FR-009, FR-015 / AC-007, AC-014–015 | Read [Test](../../../.agent-sync/skills/spec-test/SKILL.md) and [Fix](../../../.agent-sync/skills/spec-fix/SKILL.md): preview/regeneration writers and runtime obligations follow their actual branches; visual-only retains visual authority without claiming a functional-suite run. Generated syntax checks do not import/run applications. Penflow captures remain in the run before approved promotion. | Read [preview obligations](../../../tests/test_command_preview_obligations.py), [syntax boundary](../../../tests/test_generation_syntax_boundary.py), [visual modes](../../../tests/test_spec_test_visual_modes.py) and [visual-only prerequisite](../../../tests/test_visual_only_prerequisite.py). |
| FR-013 / AC-012 | Read [SDK lifecycle](../../../tests/integration/helpers/sdk_runner.py): cleanup preserves an active iteration error, while standalone cleanup failure or new cancellation propagates. | Read [cleanup failures](../../../tests/test_sdk_cleanup_failures.py). |
| FR-015 / AC-014 | Read [option authority](../../../validator/cli_commands/operation_options.py) and [pipeline skill](../../../.agent-sync/skills/spec-feature/SKILL.md): one semantic/native operation executes with its consumed identity; mixed or orphan options reject before access; progression forwards actual model and budget. | Read [semantic options](../../../tests/test_semantic_operation_matrix.py), [native options](../../../tests/test_native_test_option_matrix.py), [structural-only options](../../../tests/test_structural_only_options.py) and [pipeline identity](../../../tests/test_feature_pipeline_review_identity.py). |
| FR-016 / AC-016 | Read the aligned [001](../001-auto-llm-review/spec.md), [048](../048-command-validation-hardening/spec.md), [052](../052-deterministic-command-goal-contracts/spec.md), [058](../058-deterministic-finalization/spec.md), [069](../069-clarify-gate/spec.md) and [070](../070-analyze-gate/spec.md) contracts. Actual initial snapshots remain preserved; unavailable initial076 bytes remain explicitly unknown. | Read the [documentary acceptance regression](../../../tests/test_acceptance_review.py) and [audit13 result](/tmp/livespec-078-parent-final/audit-r13.stdout). Current migration acceptance still requires its independently ingested source-bound review. |

Public result/capability documentation now reflects actual ownership, readiness and propagated errors. Existing source API/facade exports and legacy contract interpretations are preserved. The roadmap078 row uses its managed MVP region. False-positive audit suggestions, protected initial076 debt and deferred cosmetic suggestions are not described as fixed. Read the [final audit freeze](/tmp/livespec-078-audit-fixes/final-freeze-r12.json) and [checkpoint](checks/2026-09-06-test.md) for exact evidence boundaries; overlapping targeted totals are not summed into a global result.

## Targeted correction — 2026-09-07

| Scope | Implemented correction and evidence | Remaining limit |
|---|---|---|
| G1 / AC-001–015 | Read the [canonical mapping review](.reviews/acceptance-review.json): eight independent batches and their synthesis ground every one of the unchanged 258 bindings. The 57 missing citations were repaired without changing the certifier. Read the [fresh execution summary](/Users/julienm/.codex/recovery/livespec-078-dd25/full-runtime-current-summary.json) and [independent revalidation](/Users/julienm/.codex/recovery/livespec-078-dd25/check-closure/g1-readonly-verification.json): all 15 runtime ACs certified, zero gaps. | Final current receipt is published after the report writes; documentary AC-016 is separate. |
| G3 / FR-013 trial support | Read [hook CLI output](../../../validator/hooks_cli.py) and the [real CLI regression](../../../tests/test_hooks_cli.py): stdout now preserves the compiled hook context bytes, without an extra newline. The regression checks the actual output hash for zero, one and two trailing newlines; 30 hook tests passed. | Read the [v7 outcome](/Users/julienm/.codex/recovery/livespec-078-dd25/pipeline-v7-summary.json): timeout at 1800.568 seconds, evidence_incomplete; no complete agentic success. |
| G2 / AC-016 | Read the [historical comparison](/Users/julienm/.codex/recovery/livespec-078-dd25/076-baseline-assessment.json): eight documents match authentic historical tool outputs. | Complete initial inventory and the journal history remain unproven; no blanket preservation claim. |

Feature status remains In Progress. This bounded correction does not change the feature spec, previous contracts, the source checkout, or commit history. Read the [partial closure report](checks/2026-09-07-closure.md) for the independent verdict.

## Coordinator acceptance lifecycle correction — 2026-09-07

For FR-009 / AC-007 and AC-015, read the [binding and conjunction](../../../validator/acceptance_evidence.py), [explicit metadata validation](../../../validator/evidence_policy.py), [typed proof dispatch](../../../validator/goal_generic_evidence.py) and [review identity resolution](../../../validator/goal_review_identity.py). Read the [coordinator regressions](../../../tests/test_coordinator_acceptance.py) and [scoped acceptance mapping](.reviews/coordinator-acceptance-mapping.json). The production coordinator explicitly binds the current reviewed specification; historical tasks preserve their frozen inventories.

For the supporting isolated witness correction, read the [snapshot inputs](../../../tests/integration/helpers/witness_snapshot.py), [trial finalization](../../../tests/integration/helpers/witness_pipeline.py), [actual conventions regression](../../../tests/test_generation_workspace.py) and [invalid-report regressions](../../../tests/test_witness_snapshot_integrity.py). Native pipeline completion remains separately evaluated against the unchanged oracle and archive verifier.

Read the [mapping ingestion guard](../../../validator/mapping_review_validation.py) and [pre-execution regressions](../../../tests/test_mapping_review_preflight.py): ambiguous Python spans fail preparation; missing exact binding citations fail ingestion before a runner is launched. The final runtime verifier retains the same independent checks.


### Independent closure follow-up

- Read [the pipeline witness helper](../../../tests/integration/helpers/witness_pipeline.py): bind candidate instructions to the snapshot CLI/interpreter; verify terminal progression with explicit feature and archived reviewer identity; reject usage exit 2, output diagnostics, timeouts and incomplete process control.
- Read [closure regression tests](../../../tests/test_witness_pipeline_closure.py): actual CLI terminal, pending and malformed-option scenarios plus incomplete-control rejection.
- Runtime replay under a different Python/pytest installation remains rejected. Native v9 requires fresh capture through its unchanged authoritative frozen CLI before independent closure can pass.

## 2026-09-08 — GitHub policy amendment

The explicit user decision supersedes the earlier CI selector descriptions: GitHub runs only deterministic unit and level_3a integration checks, without model providers or credentials. Local opt-in selection, generation and evidence helpers remain intact. Read [the policy tests](../../../tests/test_generation_ci_events.py) and [private corpus tests](../../../tests/test_generation_ci_selection.py) for current FR-014/AC-013 behavior. Historical trial and verification reports retain their original scope; current runtime and CI proof are pending.

## 2026-10-12 — Warm-cache regression environment (spec-fix, test only)

The [warm-cache regression](../../../tests/test_execution_bytecode.py) removes `PYTHONDONTWRITEBYTECODE` from its own environment: the scenario needs real bytecode from both the warm-up and the runner subprocess. The production capture is unchanged.

## 2026-10-13 — Project-confined execution scope (spec-fix)

FR-011: read the [source scope](../../../validator/execution_scope.py) and its [link and ignore regressions](../../../tests/test_execution_scope_links.py). The manifest never reads outside the project root. It skips untracked paths that git ignores and the agent tooling directories, and binds external or dangling links by their link text. The scope policy is `078.2`.

## 2026-10-13 — Review status as lifecycle metadata (spec-fix)

FR-004 / AC-004: [normative identity](../../../validator/normative_identity.py) treats every spec-system status, now including `Review`, as lifecycle metadata. The [clarification inventory](../../../validator/clarify_inventory.py) names a reviewer model mismatch next to `stale_or_incomplete_spec_review`. [The finalize regression](../../../tests/test_finalize_status_review_identity.py) runs `finalize apply --status` through the CLI and then the implement progression: status transitions stay READY, and an AC change makes the review stale.

## Bugfix Receipts

| Date | Requirement | Regression tests | RED receipt | GREEN receipt |
|---|---|---|---|---|
| 2026-10-16 | implementation | `tests/test_documentary_only_acceptance.py::test_documentary_only_goal_proves_archives_and_rechecks[False]`, `tests/test_documentary_only_acceptance.py::test_documentary_only_goal_proves_archives_and_rechecks[True]` | `.specs/.execution/56e45aefdf574871927347a14ea70e0f/receipt.json` | `.specs/.execution/9ad8beec4d00468dbdc5b60e866bfb82/receipt.json` |
| 2026-10-16 | implementation | `tests/test_execution_mapping.py::test_governed_mapping_and_raw_review_cannot_change_inside_generated_cache[mapping-True]`, `tests/test_execution_mapping.py::test_governed_mapping_and_raw_review_cannot_change_inside_generated_cache[review-True]` | `.specs/.execution/a5afa5c4870749d0bfcf0b35f80bc286/receipt.json` | `.specs/.execution/01917bd3a4b445ceac4993164733cdbe/receipt.json` |
| 2026-10-17 | implementation | `tests/test_spec_test_observations.py::test_canonical_test_goal_proves_real_observation_without_certifying_review_acs`, `tests/test_spec_test_observations.py::test_explicit_absence_and_resolved_commands_have_distinct_applicability` | `.specs/.execution/1f051d7a14a14812974a52a41c8f9f93/receipt.json` | `.specs/.execution/ec3f3e562184495fbfd7862261d79d83/receipt.json` |
| 2026-10-17 | implementation | `tests/test_spec_test_observations.py::test_canonical_test_goal_proves_real_observation_without_certifying_review_acs`, `tests/test_spec_test_observations.py::test_explicit_absence_and_resolved_commands_have_distinct_applicability` | `.specs/.execution/453c6a2bc1354d1eaf4f244639e7943d/receipt.json` | `.specs/.execution/91c842aea1e34caa815c911e359e812e/receipt.json` |
| 2026-10-17 | implementation | `tests/test_spec_test_observations.py::test_explicit_absence_and_resolved_commands_have_distinct_applicability`, `tests/test_spec_test_observations.py::test_suite_observations_reject_wrong_selection_and_require_complete_aggregate` | `.specs/.execution/59f06396b43048b68f0c9baf2c5a0171/receipt.json` | `.specs/.execution/7c63ea90132a45a09b0cbd79e7093122/receipt.json` |
| 2026-10-17 | implementation | `tests/test_spec_test_observations.py::test_explicit_absence_and_resolved_commands_have_distinct_applicability`, `tests/test_spec_test_observations.py::test_suite_observations_reject_wrong_selection_and_require_complete_aggregate` | `.specs/.execution/59f06396b43048b68f0c9baf2c5a0171/receipt.json` | `.specs/.execution/b4206a7d50f944b1820c971a22cba070/receipt.json` |

## 2026-10-17 — Test observation applicability bugfix

Read [canonical Test tasks](../../../.agent-sync/skills/spec-test/SKILL.md), [command applicability](../../../validator/evidence_applicability.py) and [the regression](../../../tests/test_spec_test_observations.py). Generic passed observations remain separate from six reviewed ACs and historical strict tasks; explicit absent command cells no longer activate suites. This bounded fix does not certify the full owner feature.

## Current Command-Scope Correction

- Read [the binding and immutable plan identity](../../../validator/evidence_applicability.py), [typed suite metadata guards](../../../validator/evidence_policy.py) and [five real regressions](../../../tests/test_spec_test_observations.py). Commands bind actual cwd, explicit direct transport, canonical local CLI, package/config identities and every supported filter. Literal npm aliases resolve only a genuine local shim; unresolved, chained or forwarded commands block.
- RED `d90a624ad7fc4857a5ac8d08e4b7433b` and GREEN `41521b0767034ce18fb84cce829f6d5f` pass the same final five-test selection; both initial exploit assertions and the independent suite/acceptance guard are preserved. This pair is regression evidence, not an ELIGIBLE lane claim: normal filtered FR-009/FR-011 closure follows the printed FALLBACK.
- Final acceptance remains independent; observed zero-AC tests never certify six review ACs. Current policy2 archive checks preserve every declaration, leaving unrelated tasks pending in the regression artifact rather than inventing completion. Historical goal markers and old receipt policies keep their original interpretation.


## Cloud command-discovery correction — 2026-10-17

| Date | Requirements | Owned source / existing requirement anchors | Behavior |
|---|---|---|---|
| 2026-10-17 | [FR-009](spec.md#fr-009), [AC-007](spec.md#ac-007), [AC-009](spec.md#ac-009) | Read [evidence_applicability.py](../../../validator/evidence_applicability.py), `@spec FR-009`, and [the command-discovery regressions](../../../tests/test_suite_command_discovery.py), `@spec AC-007` / `@spec AC-009` | One shared Action classifier freezes every declared test purpose and preserves typed unit/suite/aggregate proof boundaries. |
| 2026-10-17 | [FR-011](spec.md#fr-011), [AC-010](spec.md#ac-010) | Read [evidence_applicability.py](../../../validator/evidence_applicability.py), `@spec FR-011`, and [the genuine custom-execution regression](../../../tests/test_suite_command_discovery.py), `@spec AC-010` | Unknown command identity preserves canonical cwd and exact original argv; unsupported assertion certification remains an explicit gap. |

Explicit unit/integration/E2E Action labels take priority. Clear install/build/bootstrap/package-generation and quality actions are excluded before broad focused/test/regression/compatibility purposes. Command arguments never infer a suite; ambiguous execution actions stay required and unresolved. DoD binds the union, including every applicable integration/E2E command.

Opaque identity is planning metadata, not a new Playwright, Bun, uv or npx assertion adapter. Custom commands retain real execution availability, but mandatory runner-owned passing-observation verification still precedes identity comparison. An opaque required command reports `suite_assertion_adapter_unsupported`; a genuine unit receipt cannot stand in for it or certify the aggregate. Strict known-runner parse/alias errors are not downgraded into opaque fallback. No wrapper is unwrapped and no unsupported command becomes N/A or PASS.

This normal correction targets AC-007, AC-009 and AC-010 only. AC-015 and the other historical acceptance criteria are not recertified. Earlier closed controls and source-bound archives remain unchanged.

- Current scoped proof: read [the runner-owned execution receipt](../../.execution/1ea13b21907b47e3848486ee536c55ed/receipt.json), with 28 passing cases, zero skips and 95 independently reviewed assertion bindings for AC-007/009/010. The actual custom driver executes without qualifying; genuine unit proof cannot cover its opaque identity or the complete aggregate. This does not recertify the other thirteen criteria or every unchanged historical clause.

### Approved command-table compatibility follow-up — 2026-10-17

Read [the command-discovery assertions](../../../tests/test_suite_command_discovery.py) and [the existing FR-009 contract](spec.md#fr-009). Resolve named Action/Purpose and Command columns in either order. After explicit non-test and absent rows, other declared purposes remain required unit commands; only explicit action labels declare integration/E2E. Full suite, Targeted, Witness corpus and arbitrary purposes preserve exact command/cwd identity. Unsupported opaque drivers retain their explicit proof gap; no adapter or wrapper support is inferred. The prior 28-test proof remains historical for its executed bytes.

The same discovery helper selects an existing plan section before the approved testing-strategy fallback. Bind the selected source path/hash and the feature plan hash; a changed strategy or newly explicit plan invalidates prior commands. An explicit plan N/A never falls through to strategy; missing declarations remain required discovery gaps. Read [the actual fallback/precedence assertions](../../../tests/test_suite_command_discovery.py) before reusing a receipt.

Absence uses a closed, case-insensitive positive vocabulary: exact `N/A`, `N/A — no UI`, `Not applicable`, `Not run`, `None`, `—`, `-`, plus the single approved corpus sentence `Not applicable to bootstrap fixtures`. Outer whitespace is ignored. No other suffix is inferred as prose: colon, parentheses, because, other to/for qualifiers, paths, runners and wrappers remain required opaque declarations. Applicability and binding share this grammar; opaque identity never grants assertion certification. Read [the consolidated qualifier matrix and real-unit refusal](../../../tests/test_suite_absence_declarations.py) before changing accepted forms.

Ambiguous trailing-parenthesis forms still meet the existing working-directory annotation grammar. They remain required and unresolved when that directory is invalid; no exact-argv identity or passing proof is claimed for such a binding. Read [the matrix branches and real E2E/aggregate refusal](../../../tests/test_suite_absence_declarations.py) to distinguish opaque identity from conservative unresolved discovery.

### Requirement Mapping — 2026-10-18

| Requirements | Current source/test | Existing acceptance anchors |
|---|---|---|
| FR-009, FR-011; AC-007/009/010 | Read [the dedicated absence declarations](../../../tests/test_suite_absence_declarations.py), using the shared owned project/goal helpers in [command discovery](../../../tests/test_suite_command_discovery.py), and inspect [the production predicate](../../../validator/evidence_applicability.py). | Read [AC-007](spec.md#ac-007), [AC-009](spec.md#ac-009) and [AC-010](spec.md#ac-010). |

The three absence tests moved without assertion changes to keep both test modules within the 500-line convention. Their new module identities require fresh mapping and execution; the first 43-case receipt remains historical for its exact pre-split bytes.
