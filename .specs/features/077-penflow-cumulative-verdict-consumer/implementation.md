---
title: Penflow cumulative verdict consumer implementation
feature: 077-penflow-cumulative-verdict-consumer
---

# Implementation

## Current evidence and remaining work

Read [the durable native consumer evidence](checks/2026-09-05-native-consumer/README.md). Actual cumulative A+B source approval, runtime `e699444a-6d9d-480b-976e-04eea6c6c85a`, C51 implementation PASS, public consumer status, finalize apply/verify A+B, Test Done and final Doctor are verified. Adversarial changes and idempotent closure without the independent manifest refuse certification; exact restoration revalidates. Lock-order revalidation reused the same runtime capture.

Feature 077 is Implemented and its actual nonvisual registry finalization is complete. Actual native review and consumer approval of the imported Brainstorm + LiveSpec union pass, alongside bootstrap, replay, projection and origin-absent relocation. Both loaders agree on 8 requirements and 28 bindings with no uncovered obligation; destination runtime certification is not claimed. Both final spec-implement and spec-feature patches are applied and hash-checked; the 28 command-contract tests pass. Their recorded archives are preserved, including historical Feature DRIFT. Archived pilot snapshots record Analyze, Preflight and Implement as Pending, so these receipts do not establish a complete native consumer feature-pipeline execution. The completed witnesses remain archived and were not replayed for later finalizer fixes.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | Read [status](../../../validator/penflow_contract.py) and [CLI](../../../validator/cli_commands/penflow_contract_cmd.py) | FR-001 | Implemented | 2026-09-05 |
| FR-002 | Read [producer integration](../../../validator/penflow_verification.py) | FR-002 | Implemented; real C51 implementation and consumer PASS | 2026-09-05 |
| FR-003 | Read [response validation](../../../validator/penflow_verification.py) and [CLI](../../../validator/cli_commands/penflow_contract_cmd.py) | FR-003 | Implemented | 2026-09-05 |
| FR-004 | Read [status](../../../validator/penflow_contract.py) | FR-004 | Implemented | 2026-09-05 |
| FR-005 | Read [protocol tests](../../../tests/test_penflow_contract_verification.py) and [documentation](../../../system/testing/penflow-contract.md) | FR-005 | Implemented; final callers applied and hash-checked; SC005 verified | 2026-09-05 |
| FR-006 | Read [closure](../../../validator/penflow_closure.py), [finalize](../../../validator/finalize.py), [registry builders](../../../validator/finalize_registry.py), [README recovery](../../../validator/finalize_readme.py) and [pipeline](../../../validator/pipeline.py) | FR-006 | Implemented; real LiveSpec source and lifecycle proof passed | 2026-09-05 |
| FR-007 | Read [AST source](../../../validator/penflow_requirement_source.py), [review snapshot](../../../validator/penflow_review_snapshot.py), [canonical input guard](../../../validator/penflow_contract_validation.py), [approval](../../../validator/penflow_review_approval.py) and [models](../../../validator/penflow_approval_models.py) | FR-007 | Implemented; real LiveSpec source and lifecycle proof passed | 2026-09-05 |
| FR-008 | Read [authority import](../../../validator/penflow_authority_import.py), [policy source](../../../validator/penflow_policy_source.py) and [inherited projection](../../../validator/penflow_authority_projection.py) | FR-008 | Implemented; actual import, native union review, consumer approval and both loaders passed | 2026-09-05 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | Read [protocol tests](../../../tests/test_penflow_contract_verification.py): inspection and absent scope | Passed |
| AC-002 | Read [protocol tests](../../../tests/test_penflow_contract_verification.py): exact caller args, response identities, explicit CLI PASS | Protocol and real producer passed |
| AC-003 | Read [protocol tests](../../../tests/test_penflow_contract_verification.py): missing fields, malformed response, timeout, unavailable CLI, foreign identities, concurrent mutation | Passed |
| AC-004 | Read [protocol tests](../../../tests/test_penflow_contract_verification.py): alias downgrade and independent manifest required | Passed |
| AC-005 | Read [existing tests](../../../tests/test_penflow_contract.py): bootstrap and registry | Passed |
| AC-006 | Read [command tests](../../../tests/test_penflow_contract_command_contract.py) | Passed: both caller patches applied, 28 command-contract tests; actual producer integration verified separately |
| AC-007 | Read [lifecycle tests](../../../tests/test_penflow_closure.py) and [finalization tests](../../../tests/test_finalize_penflow.py) and [roadmap/lock tests](../../../tests/test_finalize.py) | Recorded A+B finalization passed; later LF/README regressions passed 67, then 68 and 69 with example preservation |
| AC-008 | Read [approval tests](../../../tests/test_penflow_review_approval.py), [pipeline tests](../../../tests/test_penflow_approval_pipeline.py) and [schema tests](../../../tests/test_penflow_approval_models.py) and [multi-feature lifecycle tests](../../../tests/test_penflow_approval_multifeature.py) and [automatic review transport tests](../../../tests/test_penflow_review_result.py) | Protocol/file/CLI tests passed; actual native A+B review approval verified separately |
| AC-009 | Read [import tests](../../../tests/test_penflow_authority_import.py) and [policy tests](../../../tests/test_penflow_policy_source.py) | Passed: actual native union review/approval, both loaders, three blocking mutations and exact restoration |

## Files Created/Modified

- Created producer transport and protocol tests; extended status helper and existing handler only.
- Updated readiness/legacy regression expectations, main README and Penflow documentation.
- Production integration adds no runtime launcher, duplicated gate policy or dependency. Isolated consumer pilot artifacts provide the native evidence recorded below; no commit is claimed.
- Added finalization/pipeline enforcement before terminal or idempotent success, preserving explicit reopening without premature runtime certification.

## Automated validation checkpoints

The latest finalizer selection passes 69 tests after detached README recovery and explicit preservation of fenced/multiline-comment examples. Earlier checkpoints passed 67 after final-LF repair and 68 after the first detached-row fix. Both have recorded RED → GREEN evidence and Ruff/Pyright PASS. Read [LF regression](checks/2026-09-05-native-consumer/finalizer-newline-regression.json) and [README recovery](checks/2026-09-05-native-consumer/finalizer-readme-recovery.json). The Penflow README source was initially inspected read-only; the producer subsequently performed the recorded real apply → verify at 15:45:51–52 UTC with zero verify violations and preserved final LF.

Counts below describe earlier overlapping selections, not a cumulative total or a fresh whole-suite run. The lock-order checkpoint passed 70 tests. A subsequent 17-suite run passed 472 tests with one outdated `.LOCK` assertion; after correcting that assertion, the two finalizer suites passed 66 tests. This assertion correction did not change certification policy.

- Active-plan policy union and pre-review selector validation are now automatic. The real CLI validates a canonical shared C20 fixture; missing/duplicate identifiers, invalid schema and absent CLI cannot publish review inputs. The policy/guard/command suite passes 46 tests after fixture migration. The standard spec-plan source adds only UI-specific instructions; the unrelated non-UI goal076 state remains unchanged.

- After policy/ancestry integration: 585 tests across 18 targeted suites passed; the subsequently added exact nested YAML duplicate case passes in the 9-case policy suite. Ruff and Pyright on changed policy/projection/approval/CLI files pass. The command documentation suite remains 27 passed after the inactive spec-init bootstrap correction.
- Source policy and import models match public C51 schema 898cda3595b77c3a16c4d8ab2a7f326d454846026c5a1bde1e45a4bb5f1b719b. Historical absence is readable but noncertifying; new snapshots require the actual workflow policy. The generated policy derives from strict YAML modes, not candidate C20 decisions.

- Before change: 56 existing Penflow helper/command tests passed.
- Consolidated consumer, classification, closure, pipeline and finalization tests: 521 passed, 0 failed.
- Ruff touched source/tests: passed. Pyright touched source/new tests: 0 errors/warnings.
- LiveSpec structural validation of spec/plan/progress/changelog: 4 files, 0 errors.
- Historical protocol-only boundary: doubles bind fixture byte hashes but do not prove producer policy. The later native pilot below supplies the actual producer integration evidence.

## Finalization complete

Both shared caller patches are applied. Read [Implement application](checks/2026-09-05-native-consumer/implement-workflow-applied.json), [Feature application](checks/2026-09-05-native-consumer/feature-workflow-applied.json), and [the applied SC005 inventory](checks/2026-09-05-native-consumer/process-simplicity.md): source/expectations hashes match current files; 28 command-contract tests pass. The prior Feature archive remains DRIFT, unchanged; no historical success was fabricated.

The supervisor’s actual CLI apply and verify both exited 0 at 17:53:02 UTC. Apply wrote feature/global changelog, README, spec status and roadmap; verify returned PASS with zero violations. Read [apply receipt](run/consumer-077-final-apply-20260905/finalize/receipt.json) and [verify receipt](run/consumer-077-final-verify-20260905/finalize/receipt.json). Raw receipt SHA-256: apply `33498031e17743e8ed11e42e6d88db7d7913b6ba095b37c8259f42a28d41502c`, verify `00af04f98ebdc67232875b3d6d2f74325104679b9775b50684ffa839bd19c69d`. Their five bound registry files remain byte-for-byte unchanged by this documentation update. This records real nonvisual consumer077 closure, not execution of a complete native consumer pipeline; C51/native import witnesses remain archived within their recorded scope.

## Measured historical validation cost

On identical temporary protocol histories (not native-review or C51 evidence), 10 features revalidate in a median 19.9 ms versus 22.5 ms before the invocation-local archive cache; 50 features take 175.4 ms versus 283.1 ms. At 50, file reads fall from 3,203 to 753, while bytes only fall from 10.63 MB to 10.18 MB. Immutable source/plan archives are authenticated once per history traversal with exact expected hashes; every new invocation and all current source semantics remain freshly checked. Distinct cumulative snapshots still grow quadratically in volume; no universal latency budget or linear-growth claim is inferred.

## Historical native pilot checkpoints

The following earlier pending/FAIL states are retained for traceability and superseded by the current e699444a proof. Source approval and each runtime capture have distinct identities.

### Actual native review pilot

The isolated two-feature pilot has a real native A PASS review packaged by the CLI and accepted through PlanReviewDone. The first real B review returned two BLOCKING findings (result guard used before its producing POST, and missing transition departure predicate). The actual packaged result was refused with `review_output_not_approved`; the prior baseline and B pipeline hashes stayed unchanged. Read [the actual refusal transcript](checks/2026-09-05-native-consumer/b-blocked-transition.json). The corrected source/plan/contract revision has 22 obligations and 44 responsibility-scoped bindings; its fresh native review returned PASS with no blocking finding, and the actual CLI published PlanReviewDone B. Both A and B revalidate against cumulative baseline 8fe6752c9887955df4e3462c991eb7db69c8a250e40bb9dfe3c05d68ebb007d5. This proves the actual approval and rejection workflow, not runtime execution, rendering or C51 certification. The external runtime pilot currently differs from these approved requirements; it must be aligned before final contract review and evidence attachment.

The final expanded pilot contract now has 16 FR/AC, 34 obligations and 68 responsibility-scoped bindings. A native reviewer rejected an incomplete history-return destination; the workflow refused it without baseline/pipeline mutation. After the exact checkout assertion was added, the fresh native result passed and actual CLI publication produced baseline 195ed5c4f105a074f626e8084b76fe5b35d8fb6966a4e17e278cfe474dc7db27, with both features independently revalidated. Read [the final real publication evidence](checks/2026-09-05-native-consumer/final-approval-transition.json). Final runtime capture/C51/finalize proof remains pending.

### Actual runtime and CLI rejection

The real external runner executed nine scenarios in the approved workspace (invocation b4c34021-49d1-4695-bcd4-0f7561be0e02), produced 20 typed observations, actual tree/provenance and a runner manifest. All 96 referenced hashes match. Read [the retained manifest](/private/var/folders/l_/t1s_zytx2fqb0dkzz40d3v7m0000gn/T/penflow-c51-native-review-5z8idhig/.specs/testing/runtime-evidence/b4c34021-49d1-4695-bcd4-0f7561be0e02/build-manifest.json). This run has no PNG output and is not visual proof. The producer is adding static-state and C44 conversion before the final run; existing outputs remain untouched.

The actual installed CLI revalidation is now exercised by the consumer transport: the still-incomplete design report is rejected as FAIL. Read [actual consumer rejection](/private/var/folders/l_/t1s_zytx2fqb0dkzz40d3v7m0000gn/T/penflow-c51-native-review-5z8idhig/reviews/consumer-real-cli-design-rejection.json). The process PATH explicitly includes the real Penflow venv; without that availability, the consumer correctly returns compatible_penflow_cli_required. No development fallback was added to production code.

The consolidated invocation a4d3d8ba-6f5e-4aab-91d7-6cad2f07f4bb adds authenticated static UI witnesses and C44 from the actual runtime. Nine scenarios and 20 observations complete; all 117 referenced files match the independent runner manifest, while approved baseline and contract hashes stay unchanged. Read [the reference verification](/private/var/folders/l_/t1s_zytx2fqb0dkzz40d3v7m0000gn/T/penflow-c51-native-review-5z8idhig/.specs/testing/runtime-evidence/a4d3d8ba-6f5e-4aab-91d7-6cad2f07f4bb/consumer-reference-verification.json). Real CLI production and revalidation return FAIL with 27 issues; upstream/C20/semantic/C12/provenance/C44/typed outcomes/source recheck pass, but native Pencil/design/compare and 14 structural obligations still block. Read [the actual validation output](/private/var/folders/l_/t1s_zytx2fqb0dkzz40d3v7m0000gn/T/penflow-c51-native-review-5z8idhig/.specs/testing/runtime-evidence/a4d3d8ba-6f5e-4aab-91d7-6cad2f07f4bb/c51-validation.stdout.json). Postflight Doctor passes with zero findings. Final C51 PASS and lifecycle closure remain pending.

The final native policy/test-identifier revision is accepted: C20 46483d40b42a2425dbb8b837825de61ad3c186bd761f8a3e2afdd5be986a9c2a, baseline 71eaba1d1e1fda8d6380db35151037726375d519c7b9f05c8739d372db4e8c03, actual reviewer zero blocking findings. Read [the actual policy approval transition](checks/2026-09-05-native-consumer/policy-approval-transition.json). Generated flow documents now match that contract; earlier runtime manifests above are historical and do not certify this updated source.

## Current native consumer closure

The fresh runtime invocation e699444a-6d9d-480b-976e-04eea6c6c85a produces a C51 implementation PASS for all 34 required obligations, with 132 matching manifest references. Public and independent root validation agree; LiveSpec status certifies both A and B. Read [the final lifecycle proof](checks/2026-09-05-native-consumer/finalize-lifecycle-positive.json).

The initial actual apply exposed roadmap R1.3 mismatch. The finalizer now repairs the exact parsed checkbox under its existing lock; replay wrote only the roadmap and preserved earlier changelog entries. Both actual apply/verify sequences pass. TestDone transitions pass with the actual manifest and are rejected, even idempotently, without it. The original report hash remains 71266f48f02e3c9a882d76ad0ac4fda84a7c393359c574ba1408b3de6d6a8656 after all lifecycle changes, and Doctor returns zero findings. Read [the phase and postflight evidence](checks/2026-09-05-native-consumer/pipeline-and-postflight-positive.json). Other pending native phases were not marked as performed by this proof.

Five actual adversarial cases refuse certification: altered FR, visual declaration, predicate, report source hash and missing runner manifest. Original bytes were restored and fresh consumer validation passed. Read [the restoration record](checks/2026-09-05-native-consumer/adversarial-restoration.json). The finalizer/closure regression suite passed 68 tests after the roadmap correction, then 70 after the lock-order correction. Read [the actual lock-order revalidation](checks/2026-09-05-native-consumer/finalizer-lock-revalidation.json); both A+B apply/verify sequences pass with the same runtime report.

## Verified native imported union

Read [the actual import final proof](checks/2026-09-05-native-consumer/import-final-proof.json) and [negative/restoration evidence](checks/2026-09-05-native-consumer/import-union-negative-restoration.json). Native PASS was accepted by the real consumer approval command; both independent loaders project 8 requirements and 28 bindings with uncovered empty. Omitting an inherited binding, tampering with the archived product or removing the import pointer blocks review-snapshot; exact restoration of seven inputs returns both loaders to PASS. This verifies source inheritance, not a runtime implementation certificate for the destination.

## Finalizer newline regression

The real current-year apply lost the final LF because year splitting joined lines without their trailing separator. The global changelog builder now appends LF only when absent. Read [the RED/GREEN receipt](checks/2026-09-05-native-consumer/finalizer-newline-regression.json): 67 finalizer/closure tests pass, including old entry preservation and byte-identical replay; Ruff and Pyright pass. No pilot or goal infrastructure changed.
