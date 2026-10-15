# Changelog - 090-minimal-plan-scope

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
