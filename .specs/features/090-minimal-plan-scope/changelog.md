# Changelog - 090-minimal-plan-scope

## 2026-10-15 — [Bugfix]: Close the carried 090 delivery review warnings: checkable release proofs, fence and declaration forms, bounded step labels, release_evidence_unreadable in the ship gate

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** system/testing/execution-rules.md, tests/test_plan_evidence_class.py, tests/test_release_evidence.py, validator/plan_evidence.py, validator/progression_gate.py, validator/release_evidence.py
- **AC impacted:** implementation
- **Author:** livespec bugfix record
- **Base revision:** HEAD
- Closes the warnings carried by the 090 delivery review (round 2), after the comment scan of 1feed8e and the level-2 heading of 5e8b441. A proof cell must name something checkable (path, file name with an extension, URL or identifier with a digit) and announce nothing anywhere in its prose (`Proof pending`, `Deferred to release`, `In progress`, `...`, `✅`, `done` are refused). A backtick fence whose info string holds a backtick is text and a closing fence has nothing after it. `**Evidence-class:**`, `<strong>Evidence class</strong>:` and no-break-space forms are reported. Step and row numbers have at most nine digits per part and are normalized without `int()`. `--progression ship` is `complete` plus the release evidence and blocks with `release_evidence_unreadable:<error>` instead of a raw `PermissionError`. Path: `/spec-fix 090-minimal-plan-scope --bugfix` (the complete gate is blocked by `missing_current_spec_review`: the disposable 090 reviews are not in this worktree). Checks: `pytest tests/ --ignore=tests/integration -n 8` 4217 passed, 22 skipped; ruff and pyright clean; 94 repo plans give 0 evidence-class errors; hostile inputs of 256 KB stay under 0.03 s.
- **Regression tests:** tests/test_plan_evidence_class.py::test_invalid_evidence_classes_are_reported[### Step 1 \u2014 Build\n\n**Evidence-class:** release\n-not recognised], tests/test_plan_evidence_class.py::test_invalid_evidence_classes_are_reported[### Step 1 \u2014 Build\n\n**Evidence\xa0class:** release\n-not recognised], tests/test_plan_evidence_class.py::test_invalid_evidence_classes_are_reported[### Step 1 \u2014 Build\n\n<strong>Evidence class</strong>: release\n-not recognised], tests/test_plan_evidence_class.py::test_rendered_declarations_are_not_hidden[### Step 1 \u2014 A\n\n### Step 2 \u2014 Sign\n\n```a`\n], tests/test_plan_evidence_class.py::test_rendered_declarations_are_not_hidden[### Step 1 \u2014 A\n\n```\n**Evidence class:** bogus\n``` x\n```\n\n### Step 2 \u2014 Sign\n], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[&lt;pending&gt;], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[**Status:** TBD], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[...], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[Deferred to release], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[In progress], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[Notary receipt pending], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[Proof pending], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[Release build 1.4 (pending)], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[Signed build: pending], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[To be signed at release], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[\u2026], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[\u231b Pending], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[\u2705], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[done], tests/test_release_evidence.py::test_announced_proof_keeps_release_pending[ok]
- **RED receipt:** `.specs/.execution/a3af26e12e734ba98aaab95dd9316dd8/receipt.json`
- **GREEN receipt:** `.specs/.execution/127cd52cc9ad404998cd24a2ce548f43/receipt.json`
<!-- bugfix:127cd52cc9ad404998cd24a2ce548f43 -->

## 2026-10-15 — [Bugfix]: Release Evidence section only at level 2; foreign tests removed

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** validator/release_evidence.py, tests/test_release_evidence.py, tests/test_plan_evidence_class.py
- **AC impacted:** AC-002
- **Author:** claude-code
- PR #42 review (Codex, P2): a `### Release Evidence` or `# Release Evidence` lookalike no longer opens the proof table; only the documented `## Release Evidence` does. Commit 1feed8e had also picked up in-progress failing tests of the follow-up hardening session (same worktree); they are removed here and come back with that fix.

## 2026-10-15 — [Bugfix]: Linear HTML comment filtering (CodeQL)

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** validator/plan_evidence.py, tests/test_plan_evidence_class.py
- **AC impacted:** AC-002, AC-003
- **Author:** claude-code
- CodeQL (PR #42, "Bad HTML filtering regexp") flagged `<!--.*?-->`. Comments are now removed by a linear `str.find` scan that spans lines; an unclosed `<!--` opens a multi-line comment only at the start of a line (an inline-code `<!--` no longer hides the rest of a plan) and text after `-->` is kept. Closes the first carried warning of the 090 delivery review.

## 2026-10-15 — [Feature]: Minimal plan scope and release evidence

- **Type:** Feature
- **Spec modified:** Yes (scope: the native rule is `system/minimal-spec-scope.md`; `/spec-ship` requires release evidence through the `ship` progression; out of scope reworded)
- **Code modified:** validator/plan_evidence.py (new), validator/release_evidence.py (new), validator/rules/__init__.py, validator/goal_payload.py, validator/progression_gate.py, validator/cli_commands/operation_options.py, validator/semantic/review_batches.py, system/minimal-spec-scope.md (new), system/review-protocol.md, system/testing/execution-rules.md, system/spec-system.md, .specs/spec-system.md, system/templates/plan-template.md, spec-plan, spec-implement and spec-ship skills, tests/test_plan_evidence_class.py, tests/test_release_evidence.py, tests/plan_evidence_support.py
- **AC impacted:** AC-001, AC-002, AC-003
- **Author:** claude-code
- Read [spec](spec.md), [plan](plan.md) and [implementation](implementation.md). The plan review prompt (plan kind only) and the native rule report every mechanism no FR, AC or constitution rule asks for, as `business` scope that blocks unless it is a justified technical necessity; `PROMPT_VERSION` stays `2` so current reviews stay current (089). A plan step may declare `**Evidence class:** release`; `livespec validate <plan.md>` rejects unknown, repeated, unbound or duplicated declarations; the implement goal lists unproven release steps under `runtime_context.pending_release_evidence` outside the required tasks; `livespec validate <feature-dir> --progression ship` (run by `/spec-ship`, also on `--resume`) adds to `complete` a valid plan and a `| Step | Evidence | Proof |` row under `## Release Evidence` naming each release step.
- Checks: `pytest tests/ --ignore=tests/integration -n 8` 4175 passed, 24 skipped; ruff and pyright clean; `livespec conventions verify --feature 090-minimal-plan-scope` PASS.
- Delivery review (full lane, two distinct native agents each round, effort high; reports in [checks/](checks/)): round 0 review and audit BLOCKED (`/spec-ship --resume` skipped the release gate; a malformed plan let `ship` pass); round 1 review PASS, audit BLOCKED (cubic heading pattern); round 2 (final) review PASS and audit PASS. Not recorded with `livespec delivery review record`: the feature-start base (the commit that specified 089-092 together) puts 129 files of other, already reviewed features in the scope, so the reviewers judged the 090 diff and the reports are kept in `checks/`.
- Carried warnings (follow-up): the HTML comment pattern is quadratic on a crafted line of 100 KB or more and an unclosed `<!--` inside inline code hides the rest of a plan; announced proofs whose first word is not a negative token (`Proof pending`, `Deferred to release`, `In progress`, `...`) still count as proof, a proof should name a path, URL or identifier; `**Evidence-class:**`, `<strong>` or no-break-space forms are not reported; the ship gate raises a raw `PermissionError` (still BLOCKED) instead of `release_evidence_unreadable`; a heading `Release Evidence` is accepted at any depth; `validator/cli.py` `--progression` help does not mention `ship` (file size debt).

## 2026-10-13 — [Feature]: Specified (spec and plan, not implemented)

- **Type:** Feature
- **Spec modified:** Yes (created, status Draft)
- **Code modified:** No
- Read [spec](spec.md) and [plan](plan.md). Origin: Handy program findings.
