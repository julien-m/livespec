<!-- @spec FR-001, FR-003: Default delivery — .specs/features/122-review-led-delivery/spec.md#fr-001 -->
# Review led delivery

This is the default delivery policy for feature, specify, plan, implement, fix, test, check, refine, preflight and ship skills, including direct, nested, autonomous and resumed invocations. It replaces their former automatic certification workflow. Read the applicable project conventions and honor the user's scope and decisions.

```mermaid
flowchart LR
    A[Spec and plan] --> C[Implement and check]
    C --> D[Independent final review]
    D --> E[Correct material findings]
    E --> F[Deliver and report]
```

## Checks inform the review

- Run useful tests, builds, typing, lint and runtime observations for the affected behavior. Keep checks proportional and reuse passing results when their relevant inputs are unchanged.
- Preserve the actual command, exit code, concise result and limitations. An error, warning, missing baseline, unavailable checker, legacy debt or missing certification is a finding for review, never an automatic stop or a reason to restart the feature pipeline.
- Fix a failure when it reveals a real defect in the requested change. Let the reviewer judge the impact of other failures. Do not require every script to be green or every warning to disappear before review or delivery.
- Do not manufacture PASS results, delete failing tests, adopt baselines blindly, weaken requirements or claim that an unexecuted interaction occurred. An essential missing observation remains unverified and goes to the reviewer with its impact.
- A failure in LiveSpec's bookkeeping does not prevent direct product checks or review. Note the issue in the current report and continue; do not start a framework repair mission as a prerequisite to the feature.

## One independent final review

Reuse an existing plan review as context. Do not create another automatic review before implementation; run a separate plan review only when the user requests it.

- Dispatch one fresh native reviewer without the implementer's conversation history. Give it the user request, current spec/plan, accepted decisions, applicable conventions, complete change and real check outcomes, including failures and unavailable checks. It must inspect relevant existing files as well as the diff. Use the host's generic native reviewer if a project-local named agent still injects the former certification requirements; do not select that obsolete definition for the new workflow.
- Review functional correctness, acceptance coverage, file placement, architecture, maintainability and concrete security/data risks. A missing receipt, model declaration, hash, registry marker or test percentage is not a product defect.
- Return a concise verdict and concrete findings with file references, impact and necessary correction. No strict JSON, raw-transcript ingestion, complete-file enumeration or reviewer identity certificate is required. Keep the host's actual response as the review record.
- Only a concrete material defect, an essential unverified behavior with material risk, a missing authority or an unresolved functional decision delays delivery. Carry minor findings and irrelevant/pre-existing test failures as reported follow-ups. Do not introduce another whole-feature review or audit by default.
- The implementer corrects findings and reruns affected checks. The reviewer inspects those corrections and their consequences without a full pipeline restart. A reviewer may correct trivial non-normative documentation, showing the diff; code changes return to the implementer so it does not approve its own edits.
- If the native reviewer is unavailable, report the missing review honestly. Do not replace it with self-approval. Independence reduces context bias; it is not a guarantee of exhaustive detection.

## No automatic certification

- Do not render/prove/archive nested LiveSpec goals, ingest semantic review receipts, classify repair patches, generate certifying manifests, run delivery-continuity/revision certificates, or require conventions, visual, Penflow, finalize or verify-output receipts to advance normal delivery.
- Read relevant design references and observe the real UI when needed. Design tooling stays useful; its certification protocol has no automatic veto over feature delivery.
- Apply the same rule to inherited hooks, child commands, phase/result wrappers and completion helpers: they cannot silently reintroduce the former certification gates. Explicit external tool refusals and user-imposed authorization limits remain in force.
- Legacy flags such as `--auto`, `--resume`, `--bugfix` and `--economy` do not reactivate certification. Honor their useful scope/read-only meaning. Read each command's retained `certification.md` only for an explicitly requested historical diagnostic.
- Existing CLI diagnostics keep their real exit codes and immutable historical interpretation. Do not turn an old BLOCKED into PASS, edit old evidence, reset mission counters or silently move an active mission to another policy. Independent work can continue while the current delivery review reports that history accurately.

## Completion

- Update the feature's spec/implementation mappings, registry and changelog as ordinary project documents. Use confined edits that preserve unrelated content and concurrent work. Do not make a metadata write depend on a certification helper.
- Mark the feature Implemented only when the independent review accepts the requested behavior with no unresolved material finding; disclose accepted limitations and nonblocking failures. This is review-led delivery, not a claim of legacy machine certification.
- Report the result, review verdict, useful checks and remaining limits. Commit, publish, merge or deploy only within the user's existing authorization. An explicit no-write or preview request remains read-only.
