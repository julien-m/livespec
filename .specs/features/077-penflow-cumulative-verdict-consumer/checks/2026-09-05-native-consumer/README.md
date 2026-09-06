# Native consumer evidence — 2026-09-05

This archive records the actual isolated A+B consumer pilot and the separately scoped Brainstorm import checks. Read [the machine index](index.json) for every original absolute path, copy SHA-256, size and all 132 manifest references independently hash-checked when this archive was created. Copies retain original bytes and absolute source identities; they are historical evidence, not a newly issued certificate or a relocatable runtime bundle. Runtime assets remain at their indexed original paths.

## Recorded A+B result

| Claim | Retained evidence |
|---|---|
| Native cumulative source approval | Read [the actual approval transition](policy-approval-transition.json): accepted baseline, snapshot and original native review hash; source approval itself is noncertifying |
| Current runtime invocation | Read [the independent build manifest](build-manifest.json): `e699444a-6d9d-480b-976e-04eea6c6c85a` |
| C51 implementation PASS, all 34 required obligations | Read [the producer report](c51-production.stdout.json) and [public revalidation](c51-validation.stdout.json) |
| All 132 manifest reference hashes match | Read [the reference check](consumer-reference-verification.json) and [the full path/hash index](index.json) |
| Actual LiveSpec consumer status A+B PASS/certified true | Read [A status](consumer-status-001-checkout-overview.stdout.json) and [B status](consumer-status-002-payment-outcomes.stdout.json) |
| Finalize apply/verify A+B PASS after exact roadmap repair | Read [the lifecycle transcript](finalize-lifecycle-positive.json); individual original finalize receipts are also copied and indexed |
| Revalidation after the lock-order correction without recapture | Read [the lock revalidation transcript](finalizer-lock-revalidation.json): both applies are already_finalized and both verifies PASS |
| Test Done with manifest; idempotent replay without manifest BLOCKED; report still PASS; Doctor zero findings | Read [the pipeline/postflight transcript](pipeline-and-postflight-positive.json) |
| Altered FR, visual declaration, predicate, report source hash and missing manifest cannot certify | Read [the five negative cases and exact restoration](adversarial-restoration.json) |

The report SHA-256 is `71266f48f02e3c9a882d76ad0ac4fda84a7c393359c574ba1408b3de6d6a8656`; the independent manifest is `e757b3366713b178403334cd3b68b865da1e53c0200c2c6a0d9108cd579c955b`. Approved C20 is `46483d40b42a2425dbb8b837825de61ad3c186bd761f8a3e2afdd5be986a9c2a`, and cumulative baseline is `71eaba1d1e1fda8d6380db35151037726375d519c7b9f05c8739d372db4e8c03`.

## Preserved failures and scope limits

Read [the initial real B rejection](b-blocked-transition.json) and [the initial R1.3 finalizer failure](finalize-verify-001-checkout-overview.stdout.json). Later successful revisions do not erase these failures or retroactively certify earlier runtime captures.

Read [A pipeline](001-checkout-overview-pipeline.md) and [B pipeline](002-payment-outcomes-pipeline.md): Analyze, Preflight and Implement remain Pending. The recorded operations do not establish execution of a complete native feature pipeline. The root completed and archived the A+B and Brainstorm/import witnesses within those limits. Both shared caller patches are applied; consumer077 is Implemented and its actual nonvisual apply/verify closure is complete, as recorded below.

## Verified separate Brainstorm source import

Read [actual bootstrap](import-bootstrap.stdout.json), [idempotent replay](import-bootstrap-replay.json), [accepted authority projection](authority-project-initial.stdout.json) and [origin-absent relocation proof](relocated-origin-proof.json). These prove actual source import and portability boundaries with four inherited requirements. The original source was restored and its report hash remained unchanged. Read [the final native union proof](import-final-proof.json): actual native PASS and consumer approval pass; both loaders agree on 8 requirements, 28 bindings and no uncovered obligation. Read [three negative cases and exact restoration](import-union-negative-restoration.json): omitted inherited binding, changed archived product and absent import pointer block; seven inputs restored, both loaders PASS. No runtime implementation certification for the import destination is claimed. Read [the separate Brainstorm041 finalization summary](/Users/julienm/projects/project-brainstorm/.specs/features/041-penflow-cumulative-design-handoff/checks/2026-09-05-native-consumer/finalization-summary.json): its actual registry verify is PASS; the raw verify receipt SHA-256 is `3b2a8d073af404a7b6fae526fe88e64edd467d5e46fb3879caacbf0387e641bc`. Read [the machine index](index.json) for the summary hash and exact receipt path. This closes Brainstorm041 within its own scope.

## Concurrent worktree preservation

Read [the earlier worktree inventory](worktree-preservation.json) for HEAD/index observations and the exact limits of preservation evidence. Both indexes are empty; this consumer branch executed no stage, commit or push. Unrelated goal/bootstrap work and the preexisting Ylune index remain outside ownership. No repository-wide initial byte inventory is invented. Read [the final preservation checkpoint](final-worktree-preservation.json): both HEADs and empty indexes agree with that earlier checkpoint, the Ylune hash remains unchanged, and all five consumer077 registry files still match the final verify receipt with changelog LF preserved.

## Latest finalizer regressions and caller checkpoint

Read [the LF regression record](finalizer-newline-regression.json): the added test first reproduced the missing final newline, then both finalizer suites passed 67 tests. Read [the detached README recovery record](finalizer-readme-recovery.json): the old marker-only replay skipped detached rows; the fixed apply → verify → stable replay test passed within the 68-test checkpoint, followed by 69 tests after explicit fenced and multiline HTML-comment preservation. Ruff and Pyright pass for both checkpoints. Counts overlap; they are not additive.

The initial Penflow README diagnosis at the recorded historical source/hash was read-only. The producer subsequently ran the real replay at 2026-09-05 15:45:51 UTC: apply returned `applied` and wrote `readme`; verify at 15:45:52 UTC returned PASS with zero violations. Read [the actual apply output](/Users/julienm/projects/penflow/.specs/features/077-complete-verification-workflow/checks/supervisor-finalize-apply.json), [verify output](/Users/julienm/projects/penflow/.specs/features/077-complete-verification-workflow/checks/supervisor-finalize-verify.json) and the [immutable verify receipt](/Users/julienm/projects/penflow/.specs/features/077-complete-verification-workflow/run/20260905T154552Z/finalize/receipt.json). Their exact original paths and raw SHA-256 values are recorded in [the recovery evidence](finalizer-readme-recovery.json) and [index](index.json). The observed README matched the verify receipt hash `3b1088ae91ae40541283ee35a4d9ba7e11893ce7f80ff760a017a25ed0e27bbc` and retained its final LF. This later operation does not retroactively change the read-only diagnosis or older pilot evidence; no archived A+B or Brainstorm/import pilot was replayed here. Consumer077 subsequently completed its own actual nonvisual apply/verify closure; the later Feature application and closure are recorded below.

Read [the applied spec-implement receipt](implement-workflow-applied.json): after hashes match the current skill and expectations. Read [the applied Feature receipt](feature-workflow-applied.json) and [the verified SC005 application checkpoint](process-simplicity.md#current-application-checkpoint): both skills/expectations match their after hashes; 28 command-contract tests and static/format checks pass. Zero additional user command or manual evidence registry is required; agent metadata, semantic mapping and proof work remain explicit. The historical Feature archive remains DRIFT with its original SHA; future source changes do not rewrite it. The machine index lists these locally recorded receipts separately from byte-for-byte copies of pilot outputs.

## Completed consumer077 registry closure

Read [the apply command](finalize-apply-command.json) and [verify command](finalize-verify-command.json): both exits are 0. Actual apply at 17:53:02 UTC wrote all five registry targets and set Implemented; actual verify returned PASS with zero violations. Read [the apply receipt](../../run/consumer-077-final-apply-20260905/finalize/receipt.json) and [verify receipt](../../run/consumer-077-final-verify-20260905/finalize/receipt.json). Raw receipt SHA-256 values are `33498031e17743e8ed11e42e6d88db7d7913b6ba095b37c8259f42a28d41502c` and `00af04f98ebdc67232875b3d6d2f74325104679b9775b50684ffa839bd19c69d`. Read [the machine index](index.json) for all four command/receipt references and the exact five bound file hashes.

This documentation update changes only unbound progress, implementation and proof-index documents; it preserves all finalizer-bound files. The nonvisual integration is closed. Archived A+B and Brainstorm/import evidence keeps its original scope and does not become proof of a complete native consumer pipeline.
