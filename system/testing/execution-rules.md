# Test Execution Rules

> When to run tests and final validation checklist.
> Referenced by `/spec-implement` phases 3, 4, and 6.

---

## When to Test

Stack-agnostic rules — applies to all ecosystems:

- **After each implementation step:** run tests targeting the layer just implemented
- **Transverse checks:** lint + type checker on touched files after each step
- **Before declaring a step Done:** the Step Gate in `implement.md` requires tests to pass
- **Before declaring the feature complete:** the smallest relevant regression selection (unit/integration/E2E only where justified); reuse passing proof when inputs have not changed

All commands come from the **Resolved Test Commands** table. Never hardcode commands.

## Execution evidence

<!-- @spec FR-010: Runner-owned acceptance proof — .specs/features/078-requirement-evidence-integrity/spec.md#fr-010 -->

- <!-- @spec FR-006: Anchor-derived mapping — .specs/features/087-anchor-derived-acceptance/spec.md#fr-006 -->
  **Preferred: derive the mapping from test anchors.** Put a `@spec AC-xxx` comment block naming the feature (`.specs/features/<feature>/spec.md#ac-xxx`) directly above the test function (it binds the function's last assertion) or above one assertion inside it (Python `#`, Rust `//`; decorators and attributes may sit between the block and the function). Then run:

  ```bash
  livespec test --feature <feature> --acceptance-mapping <mapping-path> --derive-mapping
  ```

  It writes a mapping with `"derivation": "anchors"` and exits 0, or writes nothing and exits 1 with `orphan_acceptance` (an execution AC without anchor), `unknown_anchor` (an AC the spec does not declare), `anchor_target_unresolved`, `anchor_test_without_assert` or `anchor_test_parametrized`. A derived mapping needs no mapping review: certification derives it again and requires identical bindings, then a passing test and the observed passing assertion. Whether the anchored assertion really proves its AC is judged once, in the end-of-feature [delivery review](../delivery-review.md), which reads the complete diff including the tests.
- Otherwise generate the existing acceptance mapping by hand with `feature`, actual `reviewer_model`, `review_receipt_path` and bindings: qualified AC, executed `test_id`, expected outcome, assertion path/line span/source SHA and justification. Read the strict [mapping schema](../../validator/execution_mapping.py). Test names and a global percentage never establish the mapping's semantic truth.
- A hand-written mapping keeps its mapping review by the existing Code Quality Reviewer, without adding a second mandatory reviewer:

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

- <!-- @spec FR-001: Trusted Cargo runner — .specs/features/085-cargo-execution-runner/spec.md#fr-001 -->
  Rust projects pass the resolved `cargo test ...` command with `--report-adapter junit`. Cargo still runs the exact command; LiveSpec installs itself as Cargo's target runner and `RUSTC_WORKSPACE_WRAPPER`, runs each selected test alone and reads its LLVM coverage profile to trace the assertions (`assert!`, `assert_eq!`, `assert_ne!`, `assert_matches!`) it executed. It needs stable Rust plus `llvm-profdata`/`llvm-cov` (`rustup component add llvm-tools`, or Xcode on macOS); without them the command runs uncertified with an `Unsupported runner` gap. Bind Rust tests as `<package>/<kind>/<target>::<module::test>` (a bare `module::test` is accepted when unique) and cite one complete assertion invocation inside that test function. Select test targets (`--test <name>`, `--tests`, `--lib`): doctests, `--no-run`, `--doc`, `--message-format`, `--config`, `-Z` and caller-set `RUSTC_WORKSPACE_WRAPPER`/`CARGO_TARGET_*_RUNNER` cannot be certified. Commit `Cargo.lock`, since a run that creates it changes the captured inputs.
- Preserve the actual runner receipt path. The runner captures invocation, fresh report, stdout/stderr and before/after source/test/configuration identity; proof consumption revalidates these inputs and independently recomputes certified AC scope. Caller-supplied success fields cannot replace capture. JUnit case results do not invent fine-grained assertion counts.
- Zero tests, entirely skipped results, failures, foreign or replaced reports, source mutation, malformed capture and insufficient mappings cannot certify execution even with exit code zero. Unsupported/manual drivers remain executable and return the exact missing certification scope.
- Submit the runner-owned `execution_receipt_path` for generic execution tasks and RED/GREEN observations. For policy2 final feature acceptance (`ac-scope:feature`), it is required whenever any AC declares execution, including mixed inventories. A nonempty all-review inventory instead requires complete current acceptance-review proof and the current spec review when `reviewed-spec` is bound; empty/invalid inventories block. This does not waive separate success criteria, actual checks or remote delivery evidence. Specialized visual, conventions, finalization and cumulative Penflow requirements remain additional obligations.
- For the final coordinator task declaring `ac-binding:reviewed-spec`, also submit `spec_review_receipt_path` from the current complete independent spec review and any required `acceptance_review_receipt_path`. Read the [acceptance conjunction](../review-protocol.md#documentary-acceptance): the contract predates the spec, but every current criterion must still be certified at proof, archive and archive-read.

## Plan evidence classes

<!-- @spec FR-002: Evidence class parsing, goal deferral and ship requirement — .specs/features/090-minimal-plan-scope/spec.md#fr-002 -->

- A plan step declares at most one `**Evidence class:**` line: `local` (default, usually omitted) or `release`. Steps are `Step N` headings inside the Implementation Plan (or Implementation Steps) section, or its top-level numbered items when it has no `Step` heading. Write the line on its own line under the step (a list item or a blockquote also works) or at the end of a numbered item. A step is identified by the number in its title (`Step 2.5` is step `2.5`, `Step 02` is step `2`), never by its position.
- `livespec validate <plan.md>` rejects an unknown class, two classes on one step, a class outside a step, any other `Evidence class:` mention it cannot bind (a table cell, a heading, `__…__`, `*…*`, `Evidence-class`, `<strong>…</strong>`, no-break space or unemphasized forms; text in inline code, code blocks and HTML comments is ignored, and an unclosed `<!--` hides text only when it starts the line) and two steps with the same number when one of them declares a class. Split a step whose proof is partly local and partly release.
- Only proof that needs release signing, a device fleet or production may be `release`; everything this machine can produce stays `local`. The delivery review checks the classification.
- The implement goal (`/spec-implement`, `/spec-feature`) lists each unproven release step under `runtime_context.pending_release_evidence`, outside the required tasks: it never blocks `finalize`. Local evidence stays required during implementation.
- A release proof is recorded in `implementation.md` under a heading exactly `## Release Evidence`, one row per step: `| Step | Evidence | Proof |` with the step number, the step's name as the plan writes it (with or without its `Step N` prefix) and the proof or receipt path. The item is then no longer pending. A row is ignored inside a code block, an HTML comment or with four spaces of indentation; a later row of the same step replaces an earlier one. A proof cell must name something checkable (a path or file name with an extension, a URL, or an identifier with a digit such as a build or receipt number) and announce nothing: a cell that opens with `TBC`, `not …`, `will …`, `?`, `[ ]`, `<…>`, `❌`, `⏳` or `-`, or whose words outside paths and URLs include `pending`, `deferred`, `to be`, `yet`, `in progress` or `later`, is not one (`done`, `✅` or `...` name nothing either). A row whose name is not the plan step's name is a mismatch: the ship progression refuses it, so a proof never moves to another step when the plan changes. Every acceptance criterion stays provable locally: release evidence complements it and never certifies an AC.
- `/spec-ship` requires it, including on `--resume`: `livespec validate <feature-dir> --progression ship` runs the `complete` checks, exits 1 with `release_evidence_invalid:<errors>` when the plan's evidence classes do not validate or a proof row names another step (fail closed) with `release_evidence_pending:<steps>` while a release step has no recorded proof, and with `release_evidence_unreadable:<error>` when the plan or implementation map cannot be read. The goal lists unreadable files under `runtime_context.release_evidence_unreadable` instead of failing the render; recording a proof changes the goal context, so the goal is recompiled.

## Generation evaluation

<!-- @spec FR-014: Observed generation coverage — .specs/features/078-requirement-evidence-integrity/spec.md#fr-014 -->

- Keep Python purge, TypeScript create API and UI/Penflow witnesses isolated from production data. Freeze evaluator-owned oracles outside candidate paths before generation; verify their hashes afterward. Retain candidate workspaces until evaluation ends, bound attempts/timeouts and reject symlink escapes or changed oracles.
- Check positive candidates and behavior-changing mutants. UI browser behavior alone cannot replace the existing Penflow authority; missing capability is insufficient proof.
- Record observed first-attempt/repaired success, expected blocking, failure, invalid and not-run outcomes separately, with attempts, duration, actual runtime/model and measured cost or explicit unknown. Only a witness expecting rejection can classify rejection as correct blocking.
- GitHub CI executes deterministic checks without installing or invoking model providers or requiring model credentials. Real-model samples and full-corpus evaluation remain explicit local opt-in operations through the existing tools. Report local selection separately from attempted/completed/blocked/not-run coverage; unavailable runtimes cannot imply parity or completed evaluation.

## Final Validation

Before declaring implementation complete, execute in order:

1. Type checker (if applicable)
2. Linter
3. Necessary unit/integration regression selection; run the full suite only when changed scope or a concrete unresolved risk requires it
4. E2E suite (if applicable)
5. Visual tests (if applicable and tool available)

All commands come from `plan.md` **Resolved Test Commands**. No hardcoded commands.

---

*LiveSpec Test Protocol — Execution Rules v1.1*

## Validation budgets

<!-- @spec FR-001: Managed command bounds — .specs/features/095-test-time-budgets/spec.md#fr-001 -->
<!-- @spec FR-006: Necessary validation — .specs/features/095-test-time-budgets/spec.md#fr-006 -->
<!-- @spec FR-007: Stop and diagnose — .specs/features/095-test-time-budgets/spec.md#fr-007 -->
- Apply [necessary validation](../minimal-spec-scope.md#necessary-validation): each added test proves a named behavior, changed branch, concrete risk or regression; reuse sufficient existing tests, avoid duplicate cases and unjustified exhaustive matrices, and stop when relevant checks pass. Broaden or repeat only for a new change, failure or concrete unresolved concern.
- Ordinary individual limits: unit 2s, integration 10s, acceptance 30s (unclassified means unit). The whole command, including preparation, data generation and cleanup, shares 300s across capabilities. Pytest/Cargo managed instrumentation covers the full test lifecycle. Other managed commands report `command-only`; configure the framework's native per-test timeout or an explicitly bounded selection before execution. Direct shell, separate SDK/journey/device runners and remote jobs are not intercepted by these guards.
- Resolve strict prior exceptions from `.specs/testing/test-budgets.yaml`: schema version 1, exact original command argv, optional exact collected test id, unique id, category, nonempty reason, command_seconds and test_seconds for a test exception. Every duration is positive, finite and at most 600s. A test above 300s needs a sufficient command-wide companion declaration. A command exception never enlarges unrelated tests. Existing timeout arguments can only tighten the effective maximum.
- Canonical driver identity: `livespec test`, then present options in order `--feature <resolved-slug>`, `--mutation`, `--no-coverage`. Captures/capabilities use their exact pre-instrumentation argv. Invalid active policy refuses before spawn; nested work cannot extend the enclosing command cap.
- On timeout, stop the owned execution, report command/test scope, limit, elapsed duration, granularity and diagnostics; exit 124 at execution boundaries cannot certify acceptance or assertion RED. Never reuse a stale report.
- No identical automatic retry or timeout inflation. At most one retry requires a documented changed cause/new evidence and shares the initial attempt's cumulative 300s (or prior declared maximum ≤600s). Exhaustion remains unresolved. This retry policy governs agents; runner enforcement bounds each invocation without claiming persistent interception of arbitrary shell commands.
- These changes reach a pinned consumer only after its explicit runtime update/migration; never rewrite a consumer project's pins or tests as part of a tooling change.

Example of a prior command exception (individual tests keep ordinary limits):

```yaml
schema_version: 1
exceptions:
  - {id: capacity, command: [cargo, test, --test, scale], category: benchmark, reason: Required capacity measurement, command_seconds: 600}
```
