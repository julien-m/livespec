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

## 2026-10-13 — [Bugfix]: Review status no longer stales semantic reviews

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** validator/normative_identity.py, validator/clarify_inventory.py, tests/test_finalize_status_review_identity.py
- **AC impacted:** AC-004
- **Author:** claude-code (spec-fix, Handy report 2026-10-13)

The Handy report said `finalize apply --status Planned` made the spec and plan reviews stale. A Handy-shaped spec (extra frontmatter keys, explicit `## Header` band) reproduces it end to end only when the status leaving or entering is `Review`. `Review` is a spec-system status, but Normative Identity v2 did not treat it as lifecycle metadata. Draft, Planned and In Progress transitions were already normalized. `Review` is now normalized like the other lifecycle statuses; an AC change after finalization still makes the review stale. When a review is stale and its reviewer model differs from the gate's model, the gate also reports `spec_review_model_mismatch:<receipt>!=<current>`. That was the cause recorded in Handy's 007 planning evidence, where the progression was prepared without the reviewer model. A different `--review-max-chars` budget also changes the identity; the receipt does not record the budget, so it cannot be named.

## 2026-10-16 — [Bugfix]: Verify documentary-only acceptance without requiring an unrelated runtime receipt; preserve runtime and mixed obligations

- **Type:** Bugfix
- **Spec modified:** Yes (non-requirement lines only)
- **Code modified:** .specs/features/078-requirement-evidence-integrity/spec.md, system/review-protocol.md, tests/test_documentary_only_acceptance.py, validator/acceptance_evidence.py, validator/evidence_policy.py
- **AC impacted:** implementation
- **Author:** livespec bugfix record
- **Base revision:** HEAD
- **Regression tests:** tests/test_documentary_only_acceptance.py::test_documentary_only_goal_proves_archives_and_rechecks[False], tests/test_documentary_only_acceptance.py::test_documentary_only_goal_proves_archives_and_rechecks[True]
- **RED receipt:** `.specs/.execution/56e45aefdf574871927347a14ea70e0f/receipt.json`
- **GREEN receipt:** `.specs/.execution/9ad8beec4d00468dbdc5b60e866bfb82/receipt.json`
<!-- bugfix:9ad8beec4d00468dbdc5b60e866bfb82 -->

## 2026-10-16 — [Bugfix]: Bind ignored acceptance mapping and raw review inputs in execution captures

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** .specs/livespec.lock, tests/test_execution_mapping.py, validator/execution_capture.py
- **AC impacted:** implementation
- **Author:** livespec bugfix record
- **Base revision:** HEAD
- **Regression tests:** tests/test_execution_mapping.py::test_governed_mapping_and_raw_review_cannot_change_inside_generated_cache[mapping-True], tests/test_execution_mapping.py::test_governed_mapping_and_raw_review_cannot_change_inside_generated_cache[review-True]
- **RED receipt:** `.specs/.execution/a5afa5c4870749d0bfcf0b35f80bc286/receipt.json`
- **GREEN receipt:** `.specs/.execution/01917bd3a4b445ceac4993164733cdbe/receipt.json`
<!-- bugfix:01917bd3a4b445ceac4993164733cdbe -->

## 2026-10-17 — [Bugfix]: Separate generic Test observations from acceptance and ignore explicit absent suite commands

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** .agent-sync/skills/spec-test/SKILL.md, .agent-sync/skills/spec-test/expectations.md, tests/test_spec_test_observations.py, validator/evidence_applicability.py
- **AC impacted:** implementation
- **Author:** livespec bugfix record
- **Base revision:** HEAD
- **Regression tests:** tests/test_spec_test_observations.py::test_canonical_test_goal_proves_real_observation_without_certifying_review_acs, tests/test_spec_test_observations.py::test_explicit_absence_and_resolved_commands_have_distinct_applicability
- **RED receipt:** `.specs/.execution/1f051d7a14a14812974a52a41c8f9f93/receipt.json`
- **GREEN receipt:** `.specs/.execution/ec3f3e562184495fbfd7862261d79d83/receipt.json`
<!-- bugfix:ec3f3e562184495fbfd7862261d79d83 -->

## 2026-10-17 — [Bugfix]: Separate generic Test observations and explicit absent commands while preserving acceptance

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** .agent-sync/skills/spec-test/SKILL.md, .agent-sync/skills/spec-test/expectations.md, tests/test_spec_test_observations.py, validator/evidence_applicability.py
- **AC impacted:** implementation
- **Author:** livespec bugfix record
- **Base revision:** eedd866ab2b2faff31ab5e216a71e9c72d01f799
- **Regression tests:** tests/test_spec_test_observations.py::test_canonical_test_goal_proves_real_observation_without_certifying_review_acs, tests/test_spec_test_observations.py::test_explicit_absence_and_resolved_commands_have_distinct_applicability
- **RED receipt:** `.specs/.execution/453c6a2bc1354d1eaf4f244639e7943d/receipt.json`
- **GREEN receipt:** `.specs/.execution/91c842aea1e34caa815c911e359e812e/receipt.json`
<!-- bugfix:91c842aea1e34caa815c911e359e812e -->

## 2026-10-17 — [Bugfix]: Bind Test suite observations to every resolved command and match applicability by action cell

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** .agent-sync/skills/spec-test/SKILL.md, .agent-sync/skills/spec-test/expectations.md, tests/test_spec_test_observations.py, validator/evidence_applicability.py, validator/evidence_policy.py
- **AC impacted:** implementation
- **Author:** livespec bugfix record
- **Base revision:** 3559326f811dfa8d315082405e13065b69b920f8
- **Regression tests:** tests/test_spec_test_observations.py::test_explicit_absence_and_resolved_commands_have_distinct_applicability, tests/test_spec_test_observations.py::test_suite_observations_reject_wrong_selection_and_require_complete_aggregate
- **RED receipt:** `.specs/.execution/59f06396b43048b68f0c9baf2c5a0171/receipt.json`
- **GREEN receipt:** `.specs/.execution/7c63ea90132a45a09b0cbd79e7093122/receipt.json`
<!-- bugfix:7c63ea90132a45a09b0cbd79e7093122 -->

## 2026-10-17 — [Bugfix]: Bind every resolved suite invocation and aggregate required observations; classify applicability by action

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** .agent-sync/skills/spec-test/SKILL.md, .agent-sync/skills/spec-test/expectations.md, tests/test_spec_test_observations.py, validator/evidence_applicability.py, validator/evidence_policy.py
- **AC impacted:** implementation
- **Author:** livespec bugfix record
- **Base revision:** 3559326f811dfa8d315082405e13065b69b920f8
- **Regression tests:** tests/test_spec_test_observations.py::test_explicit_absence_and_resolved_commands_have_distinct_applicability, tests/test_spec_test_observations.py::test_suite_observations_reject_wrong_selection_and_require_complete_aggregate
- **RED receipt:** `.specs/.execution/59f06396b43048b68f0c9baf2c5a0171/receipt.json`
- **GREEN receipt:** `.specs/.execution/b4206a7d50f944b1820c971a22cba070/receipt.json`
<!-- bugfix:b4206a7d50f944b1820c971a22cba070 -->
