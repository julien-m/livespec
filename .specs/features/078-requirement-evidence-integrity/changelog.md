# Changelog - 078-requirement-evidence-integrity

## 2026-10-12 — [Refactor]: Reduce the semantic operation matrix to one case per rejection branch

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_semantic_operation_matrix.py, tests/test_spec_test_visual_modes.py, tests/test_witness_penflow.py
- **AC impacted:** AC-014 (FR-015 option authority, still covered)
- **Author:** claude-code (test-suite cleanup, lot 5)
- **Details:** Before: 171 cases, 155 of them from a 5 operations x 31 legacy options cross product that hit the same guard. After: 42 cases. Each legacy option is still checked once (rotating across operations) and must be named in the diagnostic, and there is one pair per conflict branch with its diagnostic. `--reindex` was dropped together with its removal from the CLI (cleanup lot 2). The visual-mode DoD parametrization went from 24 to 6 cases. The browser-measured witness tests now skip when Node, Playwright or Chromium is unavailable, using the same resolution as `capture.mjs`.

### 2026-09-06 — Specified the complete five-axis requirement/evidence integrity programme in three delivery lots: full-context semantic review, consequential clarification, independently verified execution receipts, functional generation witnesses and versioned compatibility. Defined16FR and16AC, five Gherkin/Mermaid stories and three concrete witness contracts. Structural validation100/100; independent review0blocking, two planning warnings: snapshot stability and selected versus actually executed full corpus. No runtime implementation proof claimed.

<!-- finalize:spec-specify:2026-09-06:165bc17e -->

### 2026-09-06 — ### Plan created — Requirement Evidence Integrity

- Type: Plan
- Eight implementation steps in three delivery lots, covering all 16 FR/AC.
- One sequence and one state diagram; no database or public API introduced.
- Defined shared review/progression interfaces, runner-owned evidence and independent witness evaluation.
- Explicit concurrent mutation, legacy 076/077 compatibility and selected-versus-executed corpus gates.
- Author: Codex

<!-- finalize:spec-plan:2026-09-06:752c710f -->

### 2026-09-06 — ### Plan refined — Success criteria evidence mapping

- Type: Plan Update
- Added SC-001 through SC-004 mapping to existing implementation steps and observable proof.
- No requirement, numbering, implementation step or product scope changed.
- Current plan structural validation: 100/100. Independent delta review retained separately from the original archived review.
- Code modified: None.
- Author: Codex

<!-- finalize:spec-plan:2026-09-06:b64026f3 -->

### 2026-09-06 — Implementation and verification checkpoint

- Read the [implementation map](implementation.md) for all16 FR/AC and five implemented axes; read the [verification report](verification-report.md) for actual execution, independent source reviews and historical failures.
- Added shared grounded review/clarification/progression, typed evidence and runner capture, independent witnesses and CI selection. Lifecycle finalization supports bounded legacy/current metadata without body markers or manual migration.
- Current native SPEC/PLAN reviews are complete/ready; scoped lifecycle/evidence checks243PASS and typed-goal checks129PASS. Final mapped execution, independent spec-test and supervisor closure remain pending; no Implemented promotion recorded by this checkpoint.

### 2026-09-06 — Implementation regression and conventions complete

- Read the [final verification report](verification-report.md):3018 unit tests passed,4 skipped;12 deterministic witness tests passed,3 model cases deselected; global Ruff/validator typing and mandatory conventions passed. Existing warnings/type/format debt remain separately classified.
- All eight implementation steps complete; C and goal extraction independent source reviews passed. Final AC mapping review, runner capture and independent spec-test remain pending.
- Implementation phase archives at In Progress; only root may promote the feature after certification. No full-pipeline generation success or10/10 score claimed.

### 2026-09-06 — Policy 2 implementation and final documentation freeze

- Read the [frozen verification report](verification-report.md): 3084 unit tests passed, four skipped; 13 deterministic witness checks passed, three model cases deselected; quality and conventions passed with baseline debt explicitly retained.
- Final acceptance combines 15 execution ACs and documentary AC-016 only at existing final feature scope. Preparation retains individual scope; archive retains immutable obligations, policy identity and current receipt checks. Independent final policy-2 source review passed.
- Native gate chronology, historical failed mapping/full pipeline trials, current UI implementation authority and unavailable baseline limits remain explicit. Future acceptance verdicts are published in canonical receipts/archives; this source-bound checkpoint predicts no PASS and is frozen before capture.

### 2026-09-06 — Implementation lifecycle: requirement evidence integrity

Record lifecycle synchronization for the approved five-axis implementation. Current status comes from the requested registry transition; acceptance certification remains governed by actual tests, independent reviews and current receipts. This entry alone claims no passing result.

<!-- finalize:spec-implement:2026-09-06:183269a4 -->

### 2026-09-06 — Test lifecycle: requirement evidence integrity

Record lifecycle synchronization for deterministic checks, mapped execution and isolated generation witnesses. Actual passed, failed, blocked and not-run scopes remain in the independent reports and current receipts. This entry alone claims no passing result.


- Type: Spec Update; spec modified: No.
- Code modified by the Test reviewer: none; generated tests: 0.
- Coverage: 16/16 AC definitions covered (15 execution plus AC-016 documentary); final freshness is enforced at prove/archive.
- Independent suites: 3099 unit, 90 integration 3A, 12 witness and 1 prepared UI tests passed; the initial integration failure and baseline limitations remain in the report.
- Report: checks/2026-09-06-test.md.
- Author: Codex native independent Test reviewer.

<!-- finalize:spec-test:2026-09-06:aebeee31 -->


### 2026-09-06 — Audit corrections to evidence scope and command progression

- Read the [updated implementation map](implementation.md) for exact source/test links: immutable review-purpose binding, legacy archive interpretation, scoped fix execution and per-feature readiness before test generation.
- Corrected CLI fallthrough, pipeline publication/recovery boundaries, SDK terminal/transport/workspace handling and CI runtime selection; retained global/project/local hooks and extracted pure analyzer rendering with public imports preserved.
- Existing preview/audit/no-generation branches keep their scope; filtered fixes do not claim whole-feature acceptance. Historical transport, mapping and suite checkpoints remain historical after source changes. This entry claims no new final audit, acceptance capture or complete model-workflow success.

### 2026-09-06 — Audit 4–12 integration checkpoint

- Read the [updated implementation mapping](implementation.md) for qualified Analyze diagnostics, bounded bilingual Clarify metrics/identities, mode-safe Test/Fix obligations, syntax-only generation checks, SDK cleanup and strict native CLI operation/identity validation.
- Read the [factual Test checkpoint](checks/2026-09-06-test.md): R11 observed3825 passing,4 skipped,34 deselected before the last Clarify delta; the later125 targeted passes do not establish a full post-delta suite. The previous report is preserved with its verified SHA under run/history.
- Read the [audit13 output](/tmp/livespec-078-parent-final/audit-r13.stdout): no blocker, major or minor finding; one cosmetic nit remains. This documentation adds no runtime verdict. Fresh mapping/documentary reviews and the final Test retain their own source identities and results.
- Spec modified by this synchronization: No. Code/tests modified by this synchronization: None.

### 2026-09-07 — Check: trois écarts de fermeture078 constatés

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **Coverage:** contrôle ciblé,16FR/16AC Partial; aucune certification runtime actuelle.
- **Report:** Consulter le [rapport ciblé](checks/2026-09-07.md).
- **Author:** Codex — spec-check d821ef6d

### 2026-09-07 — Check: clôture partielle afc4d58b

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **Coverage:**15ACruntime certifiées avant écritures;AC016 non prouvé;parcoursv7 incomplet.
- **Report:** Consulter le [contrôle de clôture](checks/2026-09-07-closure.md).
- **Author:** Codex

### 2026-09-07 — Fix: 1/3 targeted gaps closed

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** Read [hook output](../../../validator/hooks_cli.py) and [CLI regressions](../../../tests/test_hooks_cli.py).
- **Gaps closed:** G1 — all 258 bindings grounded; fresh execution and independent revalidation certify AC-001 through AC-015 with zero gaps.
- **Remaining:** G2 — initial 076 inventory/log unavailable; G3 — seventh production trial timed out after 1800.568 seconds, evidence_incomplete, no end-to-end success.
- **Evidence:** Read the [closure check](checks/2026-09-07-closure.md) and [execution summary](/Users/julienm/.codex/recovery/livespec-078-dd25/full-runtime-current-summary.json). Final current certification is recaptured after report writes.
- **Author:** Codex — spec-fix ccae1976

<!-- finalize:spec-fix:2026-09-07:32825067 -->

### 2026-09-07 — Check: acceptation coordinateur FR-009

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None by check
- **Coverage:** Correction ciblée inspectée; capture complète actuelle et parcours réussi attendus,AC016 non prouvé.
- **Report:** Lire le [rapport coordinateur](checks/2026-09-07-coordinator.md).
- **Author:** Codex93766262

### 2026-09-07 — Fix: coordinator acceptance lifecycle and isolated workflow inputs

- Explicit reviewed-spec coordinator binding checks the current complete independent spec review plus runtime/documentary acceptance through proof, archive and read. Historical frozen contracts are unchanged.
- Snapshot includes and hashes catalog fixtures/test dependencies; invalid identity is retained in the trial report.
- Independent code review has no remaining finding; 56 targeted checks and 3 invalid-report regressions passed. Current runner certification and native v9 final outcome are tracked separately.
- Feature remains In Progress; authentic initial076baseline is still incomplete.

<!-- finalize:spec-fix:2026-09-07:a8c7a397 -->

### 2026-09-07 — Fix: coordinator acceptance lifecycle and isolated workflow inputs

- Explicit reviewed-spec coordinator binding checks the current complete independent spec review plus runtime/documentary acceptance through proof, archive and read. Historical frozen contracts are unchanged.
- Snapshot includes and hashes catalog fixtures/test dependencies; invalid identity is retained in the trial report.
- Independent code review has no remaining finding; 56 targeted checks and 3 invalid-report regressions passed. Current runner certification and native v9 final outcome are tracked separately.
- Feature remains In Progress; authentic initial076baseline is still incomplete.

- Mapping preparation and ingestion now reject multi-assert spans and missing per-binding citations before execution. Independent v4 review grounds all72bindings; real capture22c6c801 passed3875tests and certifiedAC007/015 with zero gaps before the final waiting-policy clarification.
- Coordinator distinguishes pending observation waits from actual child failures/deadlines, preserving bounded execution and all final proof gates.

<!-- finalize:spec-fix:2026-09-07:73d32812 -->

### 2026-09-07 — ### Fix: Verify independent pipeline closure with the bound runtime

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** Read [pipeline witness helper](../../../tests/integration/helpers/witness_pipeline.py) and [closure regression tests](../../../tests/test_witness_pipeline_closure.py).
- **Gaps closed:** Incorrect positional feature argument and ambiguous exit2; missing reviewer identity; candidate guidance omitted authoritative runtime.
- **Validation:** 18 focused tests passed; independent code review has no blocking findings. Fresh scoped capture follows final writes.
- **Remaining:** Full078 acceptance and authentic076baseline remain separate; nativev9 recovery uses the frozen CLI.
- **Author:** spec-fix

<!-- finalize:spec-fix:2026-09-07:8403a3bf -->

### 2026-09-07 — Check qualité: suivi de clôture témoin

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None by check
- **Coverage:** Revue ciblée sans finding; featurepartielle,provenancev9 etbaseline076 ouvertes.
- **Report:** Lire le [suivi de clôture](checks/2026-09-07-closure-followup.md).
- **Author:** Codexa0cfa9f9

## 2026-09-08 — Spec Update: User-authorized deterministic GitHub policy

- **Type:** Spec Update
- **Spec modified:** Yes:078FR-014/AC-013 and079FR-005/AC-006; requirement IDs preserved.
- **Code modified:** Pending implementation of the approved policy.
- **Author:** Codex
- GitHub model generation is removed by explicit user decision; local opt-in evaluation remains. Privately supply the pinned normative corpus with unchanged hash validation. Historical reports and completed goal states retain their original meaning; current reviews will be refreshed.

### 2026-10-12 — Fix: warm-cache regression controls its subprocess environment (test only)

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** `tests/test_execution_bytecode.py`
- **Gaps closed:** with `PYTHONDONTWRITEBYTECODE=1` neither the warm-up nor the runner wrote bytecode, so the regression failed; it now removes the variable from its own environment.
- **Remaining:** none for this test; production capture unchanged.
- **Author:** spec-fix (claude-opus-5-5)

<!-- finalize:spec-fix:2026-10-12:b581f1b1 -->

## 2026-10-12 — [Refactor]: ui-form witness skips cleanly without Node

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/integration/test_generation_witnesses.py
- **AC impacted:** None
- **Author:** Claude Code (test-suite cleanup, lot 1)
- ui-form cases skip with a clear reason when `node` is absent instead of failing as `node_unavailable`.

## 2026-10-12 — [Refactor]: Test suite cleanup (lot 2)

Parametrisations reduced to one case per real branch. The tag-legend test now checks every tag used by spec-fix inventory rows. JS/TS syntax cases skip explicitly when node or `node_modules/typescript` is missing; the invalid-TS case previously passed vacuously because the missing compiler also exits non-zero.

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** `tests/test_fix_execution_scope.py`, `tests/test_fix_visual_modes.py`, `tests/test_generation_syntax_boundary.py`
- **AC impacted:** None (coverage kept)
- **Author:** Claude Code

## 2026-10-12 — [Refactor]: Identity-version test made behavioural

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_lifecycle_metadata.py
- **AC impacted:** None
- **Author:** claude-code (test-suite cleanup lot 3)

`test_identity_policy_version_invalidates_prior_receipts` only compared the constant; it now proves a version bump changes the normative hash.

## 2026-10-12 — Refactor: Trim redundant review-identity and Analyze test combinations

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_review_lifecycle_protocol.py (20 → 8 cases: the lifecycle exemption still runs for every header band and newline pair, each business change runs once); tests/test_pre_impl_missing_artifacts.py (18 → 5 cases: every missing set, both semantic statuses, and an invalid review config that must not preempt the CRITICAL diagnostics).
- **AC impacted:** AC-004 (same branches still exercised)
- **Author:** claude-code

## 2026-10-13 — [Bugfix]: Execution capture stays inside the project

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** validator/execution_scope.py, docs/cli-reference.md, tests/test_execution_scope_links.py
- **AC impacted:** AC-009 (stale and foreign evidence rules unchanged; scope policy 078.2)
- **Author:** claude-code (spec-fix, Handy defect 2026-10-13)

`livespec test` rejected the whole capture in Handy with `'<livespec>/.agent-sync/rules/livespec/commands.md' is not in the subpath of '<project>'`. `livespec runtime dev` links the ignored `.agent-sync.local` entries to the LiveSpec checkout, and `.claude`/`.agents` entries link to them. The input manifest now skips untracked paths that git ignores and the agent tooling directories (`.agent-sync.local`, `.claude`, `.agents`, `.codex`). It binds a dangling link, or a link leaving the project, by its link text only, without reading the target. A spec reference that leaves the project is not an input. An internal link to an excluded input is still rejected. Captures made under policy 078.1 must be run again.
