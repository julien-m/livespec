# Changelog - 083-pinned-runtime-isolation

### 2026-10-11 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections: pinned runtime snapshots, CLI shim, pin/upgrade/dev, tool/project boundary and defect reports, drift detection, documentation)
- **Code modified:** None in this phase
- **AC impacted:** AC-001 through AC-018 (all defined)
- **Author:** Claude Code native spec-specify (claude-opus-5-5)
- Read [spec](spec.md): seven stories (five P1, two P2), eighteen AC, thirteen FR, Gherkin and Mermaid for every story, Quality Engineering, Clarifications.
- Native claude-opus-5-5 spec review complete and ready after two correction rounds (three batches plus synthesis, 60000-character budget); no blocking finding, no critical ambiguity; remaining warnings are planning inputs (ADR plus constitution amendment, symlink and dev-lock hardening, flag defaults).
- Clarify inventory empty; plan progression READY. Implementation and fixture evidence remain later phases.

<!-- finalize:spec-specify:2026-10-11:60b23cb4 -->

### 2026-10-11 — Plan: Technical plan generated

- **Type:** Feature
- **Spec modified:** No (lifecycle status only: Planned)
- **Code modified:** None (plan.md created; governance: ADR-004 added, constitution principles 3/5/6 amended, README ADR row)
- **AC impacted:** None (pre-implementation)
- **Author:** Claude Code native spec-plan (claude-opus-5-5)
- Read [plan](plan.md): 9 implementation steps, 1 sequence + 1 state (Gherkin-paired) + 1 ER diagram, planning decisions D-01..D-15 resolving the spec-review warnings, AC test mapping and QE gates. The plan is deliberately compact (single section) so the plan review fits the bound 60000-character budget in 4 batches.
- Plan review: native claude-opus-5-5, 4 batches + synthesis, two correction rounds; receipt `.reviews/plan.json` complete+ready, 35/35 requirements covered, info-only findings carried to Analyze. Plan status Approved.
- Next action: Analyze, then `/spec-implement 083-pinned-runtime-isolation`.
- Read [ADR-004](../../stacks/decisions/ADR-004-pinned-runtime-snapshots.md): runtime home write scope, `runtime` command group, snapshot + shim installation.
- Spec review re-run against the amended constitution and re-ingested complete+ready before planning; plan progression READY.

<!-- finalize:spec-plan:2026-10-11:5ddfddac -->

### 2026-10-11 — Feature: Pinned runtime implementation (steps 1-9; conventions certification pending)

- **Type:** Feature
- **Spec modified:** No (lifecycle status only: In Progress)
- **Code modified:** validator/runtime/{__init__,models,home,git_tree,manifest,snapshot,shim_core,shim,links,project,inspection,defects}.py, validator/cli_commands/runtime_cmd.py, validator/doctor/runtime_scan.py, validator/doctor/scanner.py, validator/pipeline.py, validator/cli.py, validator/exceptions.py, system/tool-project-boundary.md, system/spec-system.md, .specs/spec-system.md, .agent-sync/skills/{spec-feature,spec-fix,spec-implement,spec-ship}/SKILL.md + expectations.md, README.md, docs/cli-reference.md, .specs/conventions-gates.yaml (constitution hash refresh only), tests/runtime_support.py, tests/test_runtime_{snapshot,shim,project,cli,inspection,defects,docs}.py
- **AC impacted:** AC-001 through AC-018 (62 feature tests pass in temporary directories)
- **Author:** Claude Code native spec-implement (claude-opus-5-5)
- Read [implementation](implementation.md) and [progress](progress.md): `livespec runtime install|pin|upgrade|dev|status|defect`, stdlib shim with exit 3, shared drift scanner in `livespec doctor`, boundary rule referenced from six entry points, documented Handy migration verified on a temporary fixture.
- Full unit suite: no new failure versus the recorded baseline (24 additional failures reproduce only without `AIRESOURCES` from this worktree location and pass with it set).
- Status stays In Progress: `livespec conventions verify --feature 083-pinned-runtime-isolation` FAILs only on pre-existing debt in validator/cli.py, validator/doctor/scanner.py and validator/exceptions.py; execution certification is left to `/spec-test`.

<!-- finalize:spec-implement:2026-10-11:68d31117 -->

### 2026-10-11 — Feature: Pinned runtime implementation certified (resume)

- **Type:** Feature
- **Spec modified:** No (lifecycle status only: Implemented)
- **Code modified:** validator/runtime/{__init__,errors,models,home,git_tree,manifest,snapshot,shim_core,shim,links,project,inspection,defects}.py, validator/cli_commands/runtime_cmd.py, validator/cli_commands/__init__.py, validator/doctor/runtime_scan.py, validator/doctor/__init__.py, validator/version_guard.py, validator/pipeline.py, system/tool-project-boundary.md, system/spec-system.md, .specs/spec-system.md, .agent-sync/skills/{spec-feature,spec-fix,spec-implement,spec-ship}/SKILL.md + expectations.md, README.md, docs/cli-reference.md, .specs/conventions-gates.yaml (constitution hash refresh only), tests/runtime_support.py, tests/test_runtime_{snapshot,shim,project,cli,inspection,defects,docs}.py
- **AC impacted:** AC-001 through AC-018 (runner-owned execution receipt certifies 18/18)
- **Author:** Claude Code native spec-implement (claude-opus-5-5)
- Supervisor decision applied: feature edits moved out of the debt-laden validator/cli.py, validator/exceptions.py and validator/doctor/scanner.py (all reverted to HEAD); runtime registration goes through register_unified_commands, the FR-009 guard bypass lives in validator/version_guard.py, runtime errors in validator/runtime/errors.py, doctor integration in a package-level run_doctor wrapper.
- `livespec conventions verify --feature 083-pinned-runtime-isolation` PASS; independent acceptance-mapping review complete and ready (18/18 covered); execution receipt valid with no gaps. Review-driven fix: manifest commit is now checked against the install ref and the lock.
- Full unit suite with AIRESOURCES set: no new failure versus the recorded baseline.
- Read [implementation](implementation.md) and [progress](progress.md).

<!-- finalize:spec-implement:2026-10-11:027bff35 -->

### 2026-10-11 — Test: AC coverage validated

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** tests/test_runtime_shim.py, tests/test_runtime_project.py, tests/test_runtime_inspection.py (3 appended tests); run/acceptance/mapping.json (+11 bindings, AC-003 rebind) and mapping-review-receipt.json (fresh review)
- **Coverage:** 18/18 AC covered (100%), 3 generated, 64/64 feature tests passing; full unit suite no failure outside baseline
- **Report:** `checks/2026-10-11-test.md`
- **Author:** Claude Code native spec-test (claude-opus-5-5)

### 2026-10-11 — Bugfix: Audit corrections for pinned runtime isolation

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** validator/runtime/{defects,errors,snapshot,manifest,models,links,project,inspection,shim_core}.py, validator/cli_commands/runtime_cmd.py, README.md, docs/cli-reference.md, tests/test_runtime_{snapshot,shim,project,inspection,defects,docs}.py
- **AC impacted:** AC-001, AC-003, AC-005, AC-006, AC-007, AC-012, AC-013, AC-014, AC-016, AC-018
- **Author:** Claude Code native spec-implement (claude-opus-5-5)
- Read [implementation](implementation.md) (Audit Corrections table): defect --feature/--phase validated before any write (traversal blocker), staging-named symlinks unlinked without following (containment blocker), safe defect Markdown, strict manifest schema, read-only verification, trusted provenance for broken links, locked all-or-nothing selection with rollback, runtime_reference_missing warning, verified-snapshot `current` in the shim, docs test isolated from real paths, fresh-machine docs start with the checkout's own CLI.
- Execution certification not re-run here; the supervisor re-runs /spec-test.

<!-- finalize:spec-implement:2026-10-11:c4506f10 -->

### 2026-10-12 — Bugfix: Second audit pass corrections

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** validator/runtime/{defects,project,shim_core,snapshot}.py, tests/test_runtime_{defects,project,shim,snapshot,inspection,docs}.py
- **AC impacted:** AC-003, AC-005, AC-007, AC-013, AC-018
- **Author:** Claude Code supervisor (claude-opus-5-5), implementing agent interrupted by an API limit
- Read [implementation](implementation.md) (Second audit pass table): redirected `.specs` paths refused before defect writes, HTML-escaped single-line report values, bytecode-free docs fixture, lock published last with explicit incomplete-rollback error, strict `current` manifest shape and loop-safe resolution in the shim, mandatory deletion container.
- Third audit pass (0 blocker): absolute-only trusted `.livespec-path`, `current` manifest source/created_at validation, non-directory deletion refused.

### 2026-10-12 — Test: AC coverage re-certified after audit corrections

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** tests/test_runtime_project.py (1 appended test: `test_dev_from_pinned_moves_path_and_links_to_checkout`); run/acceptance/mapping.json (re-bound to HEAD 83a48c5, +11/−2 bindings, 177 total) and mapping-review-receipt.json (fresh review)
- **Coverage:** 18/18 AC covered (100%), 1 generated, 103/103 feature tests passing; full unit suite no failure outside baseline
- **Report:** `checks/2026-10-12-test.md`
- **Author:** Claude Code native spec-test (claude-opus-5-5)

### 2026-10-12 — Feature: Pipeline complete (/spec-feature --auto)

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** No (pipeline closure only)
- **Author:** Claude Code spec-feature supervisor (claude-opus-5-5)
- Specify, Clarify, Plan, Analyze, Preflight, Implement and Test phases done; three read-only audit passes with corrections (0 unresolved blockers); execution re-certified 18/18 AC after the corrections.

<!-- finalize:spec-feature:2026-10-12:21b73207 -->
