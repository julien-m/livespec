# Test Execution Rules

> When to run tests and final validation checklist.
> Referenced by `/spec-implement` phases 3, 4, and 6.

---

## When to Test

Stack-agnostic rules — applies to all ecosystems:

- **After each implementation step:** run tests targeting the layer just implemented
- **Transverse checks:** lint + type checker on touched files after each step
- **Before declaring a step Done:** the Step Gate in `implement.md` requires tests to pass
- **Before declaring the feature complete:** full suite (unit + integration + E2E if applicable)

All commands come from the **Resolved Test Commands** table. Never hardcode commands.

## Execution evidence

<!-- @spec FR-010: Runner-owned acceptance proof — .specs/features/078-requirement-evidence-integrity/spec.md#fr-010 -->

- Generate the existing acceptance mapping with `feature`, actual `reviewer_model`, `review_receipt_path` and bindings: qualified AC, executed `test_id`, expected outcome, assertion path/line span/source SHA and justification. Read the strict [mapping schema](../../validator/execution_mapping.py). Names, anchors and a global percentage never establish the mapping's semantic truth.
- Use the existing Code Quality Reviewer for mapping review, without adding a second mandatory reviewer:

  ```bash
  livespec test --feature <feature> --acceptance-mapping <mapping-path> --prepare-mapping-review
  livespec test --feature <feature> --acceptance-mapping <mapping-path> --ingest-mapping-review <actual-raw-bundle>
  ```

- The first command returns prepared context and `response_schema`. Reviewer must inspect the exact test assertions against the acceptance outcome and return actual grounded JSON for every batch; ingest the actual raw results and synthesis. Unreviewed, missing or stale bindings remain unproven. Read the [raw review protocol](../review-protocol.md) for batch completeness and synthesis.
- Preparation rejects Python bindings that cite multiple assertions. Ingestion requires the complete exact span of every binding in its own AC conclusion's source-matching citation, including after synthesis; representative examples cannot mark the mapping ready. Fix these errors before runner capture.
- Execute the resolved command through the existing test surface with supported structured reporting, for example a resolved pytest command and its JUnit adapter:

  ```bash
  livespec test --feature <feature> --acceptance-mapping <mapping-path> --execution-command '<resolved-test-command>' --report-adapter junit
  ```

- Preserve the actual runner receipt path. The runner captures invocation, fresh report, stdout/stderr and before/after source/test/configuration identity; proof consumption revalidates these inputs and independently recomputes certified AC scope. Caller-supplied success fields cannot replace capture. JUnit case results do not invent fine-grained assertion counts.
- Zero tests, entirely skipped results, failures, foreign or replaced reports, source mutation, malformed capture and insufficient mappings cannot certify execution even with exit code zero. Unsupported/manual drivers remain executable and return the exact missing certification scope.
- Submit the runner-owned `execution_receipt_path` for execution tasks. Specialized visual, conventions, finalization and cumulative Penflow requirements remain additional obligations.
- For the final coordinator task declaring `ac-binding:reviewed-spec`, also submit `spec_review_receipt_path` from the current complete independent spec review and any required `acceptance_review_receipt_path`. Read the [acceptance conjunction](../review-protocol.md#documentary-acceptance): the contract predates the spec, but every current criterion must still be certified at proof, archive and archive-read.

## Generation evaluation

<!-- @spec FR-014: Observed generation coverage — .specs/features/078-requirement-evidence-integrity/spec.md#fr-014 -->

- Keep Python purge, TypeScript create API and UI/Penflow witnesses isolated from production data. Freeze evaluator-owned oracles outside candidate paths before generation; verify their hashes afterward. Retain candidate workspaces until evaluation ends, bound attempts/timeouts and reject symlink escapes or changed oracles.
- Check positive candidates and behavior-changing mutants. UI browser behavior alone cannot replace the existing Penflow authority; missing capability is insufficient proof.
- Record observed first-attempt/repaired success, expected blocking, failure, invalid and not-run outcomes separately, with attempts, duration, actual runtime/model and measured cost or explicit unknown. Only a witness expecting rejection can classify rejection as correct blocking.
- Routine CI executes deterministic checks. Core generator changes select a bounded real-model sample; release/model/runtime changes select the full corpus. Report selection separately from attempted/completed/blocked/not-run coverage. Unavailable runtimes cannot imply parity or satisfy required release coverage.

## Final Validation

Before declaring implementation complete, execute in order:

1. Type checker (if applicable)
2. Linter
3. Full test suite (unit + integration)
4. E2E suite (if applicable)
5. Visual tests (if applicable and tool available)

All commands come from `plan.md` **Resolved Test Commands**. No hardcoded commands.

---

*LiveSpec Test Protocol — Execution Rules v1.1*
