# Changelog - 083-pinned-runtime-isolation

## 2026-10-11 — [Spec]: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections: pinned runtime snapshots, CLI shim, pin/upgrade/dev, tool/project boundary and defect reports, drift detection, documentation)
- **Code modified:** None in this phase
- **AC impacted:** AC-001 through AC-018 (all defined)
- **Author:** Claude Code native spec-specify (claude-opus-5-5)
- Read [spec](spec.md): seven stories (five P1, two P2), eighteen AC, thirteen FR, Gherkin and Mermaid for every story, Quality Engineering, Clarifications.
- Native claude-opus-5-5 spec review complete and ready after two correction rounds (three batches plus synthesis, 60000-character budget); no blocking finding, no critical ambiguity; remaining warnings are planning inputs (ADR plus constitution amendment, symlink and dev-lock hardening, flag defaults).
- Clarify inventory empty; plan progression READY. Implementation and fixture evidence remain later phases.

<!-- finalize:spec-specify:2026-10-11:60b23cb4 -->

## 2026-10-11 — [Plan]: Technical plan generated

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

## 2026-10-11 — [Feature]: Pinned runtime implementation (steps 1-9; conventions certification pending)

- **Type:** Feature
- **Spec modified:** No (lifecycle status only: In Progress)
- **Code modified:** validator/runtime/{__init__,models,home,git_tree,manifest,snapshot,shim_core,shim,links,project,inspection,defects}.py, validator/cli_commands/runtime_cmd.py, validator/doctor/runtime_scan.py, validator/doctor/scanner.py, validator/pipeline.py, validator/cli.py, validator/exceptions.py, system/tool-project-boundary.md, system/spec-system.md, .specs/spec-system.md, .agent-sync/skills/{spec-feature,spec-fix,spec-implement,spec-ship}/SKILL.md + expectations.md, README.md, docs/cli-reference.md, .specs/conventions-gates.yaml (constitution hash refresh only), tests/runtime_support.py, tests/test_runtime_{snapshot,shim,project,cli,inspection,defects,docs}.py
- **AC impacted:** AC-001 through AC-018 (62 feature tests pass in temporary directories)
- **Author:** Claude Code native spec-implement (claude-opus-5-5)
- Read [implementation](implementation.md) and [progress](progress.md): `livespec runtime install|pin|upgrade|dev|status|defect`, stdlib shim with exit 3, shared drift scanner in `livespec doctor`, boundary rule referenced from six entry points, documented Handy migration verified on a temporary fixture.
- Full unit suite: no new failure versus the recorded baseline (24 additional failures reproduce only without `AIRESOURCES` from this worktree location and pass with it set).
- Status stays In Progress: `livespec conventions verify --feature 083-pinned-runtime-isolation` FAILs only on pre-existing debt in validator/cli.py, validator/doctor/scanner.py and validator/exceptions.py; execution certification is left to `/spec-test`.

<!-- finalize:spec-implement:2026-10-11:68d31117 -->

## 2026-10-11 — [Feature]: Pinned runtime implementation certified (resume)

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

## 2026-10-11 — [Test]: AC coverage validated

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** tests/test_runtime_shim.py, tests/test_runtime_project.py, tests/test_runtime_inspection.py (3 appended tests); run/acceptance/mapping.json (+11 bindings, AC-003 rebind) and mapping-review-receipt.json (fresh review)
- **Coverage:** 18/18 AC covered (100%), 3 generated, 64/64 feature tests passing; full unit suite no failure outside baseline
- **Report:** `checks/2026-10-11-test.md`
- **Author:** Claude Code native spec-test (claude-opus-5-5)

## 2026-10-11 — [Bugfix]: Audit corrections for pinned runtime isolation

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** validator/runtime/{defects,errors,snapshot,manifest,models,links,project,inspection,shim_core}.py, validator/cli_commands/runtime_cmd.py, README.md, docs/cli-reference.md, tests/test_runtime_{snapshot,shim,project,inspection,defects,docs}.py
- **AC impacted:** AC-001, AC-003, AC-005, AC-006, AC-007, AC-012, AC-013, AC-014, AC-016, AC-018
- **Author:** Claude Code native spec-implement (claude-opus-5-5)
- Read [implementation](implementation.md) (Audit Corrections table): defect --feature/--phase validated before any write (traversal blocker), staging-named symlinks unlinked without following (containment blocker), safe defect Markdown, strict manifest schema, read-only verification, trusted provenance for broken links, locked all-or-nothing selection with rollback, runtime_reference_missing warning, verified-snapshot `current` in the shim, docs test isolated from real paths, fresh-machine docs start with the checkout's own CLI.
- Execution certification not re-run here; the supervisor re-runs /spec-test.

<!-- finalize:spec-implement:2026-10-11:c4506f10 -->

## 2026-10-12 — [Bugfix]: Second audit pass corrections

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** validator/runtime/{defects,project,shim_core,snapshot}.py, tests/test_runtime_{defects,project,shim,snapshot,inspection,docs}.py
- **AC impacted:** AC-003, AC-005, AC-007, AC-013, AC-018
- **Author:** Claude Code supervisor (claude-opus-5-5), implementing agent interrupted by an API limit
- Read [implementation](implementation.md) (Second audit pass table): redirected `.specs` paths refused before defect writes, HTML-escaped single-line report values, bytecode-free docs fixture, lock published last with explicit incomplete-rollback error, strict `current` manifest shape and loop-safe resolution in the shim, mandatory deletion container.
- Third audit pass (0 blocker): absolute-only trusted `.livespec-path`, `current` manifest source/created_at validation, non-directory deletion refused.

## 2026-10-12 — [Test]: AC coverage re-certified after audit corrections

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** tests/test_runtime_project.py (1 appended test: `test_dev_from_pinned_moves_path_and_links_to_checkout`); run/acceptance/mapping.json (re-bound to HEAD 83a48c5, +11/−2 bindings, 177 total) and mapping-review-receipt.json (fresh review)
- **Coverage:** 18/18 AC covered (100%), 1 generated, 103/103 feature tests passing; full unit suite no failure outside baseline
- **Report:** `checks/2026-10-12-test.md`
- **Author:** Claude Code native spec-test (claude-opus-5-5)

## 2026-10-12 — [Feature]: Pipeline complete (/spec-feature --auto)

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** No (pipeline closure only)
- **Author:** Claude Code spec-feature supervisor (claude-opus-5-5)
- Specify, Clarify, Plan, Analyze, Preflight, Implement and Test phases done; three read-only audit passes with corrections (0 unresolved blockers); execution re-certified 18/18 AC after the corrections.

<!-- finalize:spec-feature:2026-10-12:21b73207 -->

### 2026-10-12 — Fix: documented migration command runs with LiveSpec's own venv (1 gap closed)

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** `README.md`, `docs/cli-reference.md`, `tests/test_runtime_docs.py`
- **Gaps closed:** FR-013/AC-018 — `python3 -m validator.cli runtime install` failed without the dependencies (`ModuleNotFoundError: typer`) and would have bound the shim to that interpreter; the docs now use `<livespec repo>/.venv/bin/python` (`uv sync` once) and the test runs the exact block without venv activation or a python3 shim.
- **Gate:** progression implement READY.
- **Remaining:** None.
- **Author:** spec-fix (claude-opus-5-5)

<!-- finalize:spec-fix:2026-10-12:5728df60 -->

## 2026-10-12 — [Bugfix]: Link discovery stays inside the project; unreadable path file is drift

- **Type:** Bugfix (PR #36 review)
- **Spec modified:** No
- **Code modified:** `validator/runtime/links.py` (a symlinked or escaping `.agent-sync.local/{skills,rules}` is never followed), `validator/runtime/inspection.py` (unreadable or non-UTF-8 `.specs/.livespec-path` becomes `runtime_reference_broken`), `tests/test_runtime_project.py`, `tests/test_runtime_inspection.py`
- **Cause:** `is_dir()`/`iterdir()` followed a symlinked link directory, so `runtime pin|upgrade|dev` could rewrite links outside the project; `read_text()` raised on invalid UTF-8 and hid the recovery diagnostics.
- **Proof:** both regression tests fail without the fix and pass with it.
- **Author:** spec-fix (claude-code)

## 2026-10-13 — [Bugfix]: Snapshots ship the conventions test evidence

- **Type:** Bugfix (Handy pinned runtime)
- **Spec modified:** Yes (FR-001, AC-001 and its Gherkin scenario: the conventions test evidence under `tests/` is shipped; the rest of `tests/` and `.specs/` stay excluded)
- **Code modified:** `validator/runtime/models.py` (`SNAPSHOT_TEST_EVIDENCE`, `ships_in_snapshot`), `validator/runtime/git_tree.py`, `docs/cli-reference.md`, `tests/test_runtime_snapshot_evidence.py`
- **Cause:** the snapshot dropped every top-level `tests/` path. `livespec conventions verify` resolves the AST fixtures and the deterministic test files cited by the bundled catalogs from the runtime root, so a pinned runtime reported `fixture missing: tests/fixtures/conventions_ast/ts/no_as_any/pass.ts` and 1,130 `rule_decision_manifest_invalid` blockers: the conventions gate was always BLOCKED.
- **Proof:** the regression test fails without the fix. A snapshot that holds only the shipped evidence reaches `Conventions verdict: PASS` on a TypeScript project where the installed `21-3c1e6a776500` snapshot is BLOCKED. A drift guard checks that every `tests/` path cited by the conventions catalogs and modules ships.
- **AC impacted:** AC-001
- **Author:** spec-fix (claude-code)

## 2026-10-15 — [Spec Update]: User approvals recorded; spec and plan reviews refreshed at a 120000-character budget

- **Type:** Spec Update (review refresh)
- **Spec modified:** Yes (Clarifications only: two entries record the user's 2026-10-15 approvals of `runtime install --no-activate`, the `pin` warning on a non-ignored `.specs/.livespec-path`, and plan decisions D-01 to D-15; no FR/AC/SC identifier or requirement meaning changed)
- **Plan modified:** Yes (D-11 recovery now uses LiveSpec's own venv, `cd <livespec repo> && uv sync && .venv/bin/python -m validator.cli runtime install`, as the docs have since 2026-10-12)
- **Code modified:** None
- **Cause:** the spec review was stale since c0381aa (FR-001/AC-001 changed on 2026-10-13 without a new review), which kept `--progression implement` at `BLOCKED: clarify_not_ready:stale_or_incomplete_spec_review`; the plan review was stale too. Independent reviewers then flagged plan and spec behaviors beyond the six decided items as unapproved business scope; the user approved them on 2026-10-15.
- **Budget:** reviews use `--review-max-chars 120000` instead of the 60000 default. At 60000 the plan review needs four batches and its synthesis prompt is 67069 characters (34559 of fixed cost), so it cannot be ingested; feature 089 (budget recorded in the receipt) is not in the installed runtime, so the gate must be run with the same `--review-max-chars 120000`. Tool defect recorded in `.specs/tool-defects/2026-10-15-review-synthesis-fixed-cost-exceeds-the-default-budget.md`.
- **Reviews:** one batch each, independent native claude-opus-5-5 reviewers. Spec: complete and ready, 34 covered and AC-016 ambiguous with a non-critical ambiguity (D-04 versus the single INFO for a dev lock). Plan: complete and ready, 35/35 covered. No blocking finding, no unapproved business scope. Receipts are disposable caches in the checkout that ran them (`.reviews/spec.json`, `.reviews/plan.json`, round 1).
- **Gate:** `livespec validate .specs/features/083-pinned-runtime-isolation --progression implement --model claude-opus-5-5 --review-max-chars 120000` → `Progression: READY`.
- **Carry over:** realign AC-016 and the Story 6 flow with D-04; D-11 adds `uv`, absent from the declared stack, and its message omits `--source`/`--ref <commit>` required by AC-005 (the shim's `CHECKOUT_INSTALL` still says `python3 -m validator.cli runtime install`); Step 2 does not restate the kept conventions test evidence; `cli.py`, `doctor/scanner.py` and `pipeline.py` stay over 300 lines; AC-016 versus AC-017 for an invalid lock in the LiveSpec repository.
- **Author:** spec-refine + native review refresh (claude-opus-5-5)

## 2026-10-15 — [Bugfix]: 2 gaps closed from the 2026-10-15 review (1 functional, 1 spec wording)

- **Type:** Bug Fix (review carry-over of the 2026-10-15 spec refresh)
- **Spec modified:** Yes (AC-016 text, the Story 6 Gherkin "Invalid lock and quiet cases" and flowchart: a dev lock whose source is not a LiveSpec root yields exactly one ERROR `runtime_dev_source_invalid` and no checkout finding, per approved D-04; no identifier changed; frontmatter `updated`)
- **Plan modified:** Yes (D-11 names `--source <livespec repo>` and `--ref <commit>` for a pinned lock, per AC-005; Step 2 states the kept conventions test evidence; Step 3 states the exit-3 recovery texts)
- **Code modified:** `validator/runtime/shim_core.py` (`CHECKOUT_INSTALL` is now `cd <livespec repo> && uv sync && .venv/bin/python -m validator.cli runtime install --source <livespec repo>`, plus `--ref <commit>` for a pinned lock without `current`), `tests/test_runtime_shim.py`, `docs/cli-reference.md` (dev-mode finding)
- **Cause:** the exit-3 message still printed `python3 -m validator.cli runtime install`, which lacks LiveSpec's dependencies and omitted `--source`; AC-016 promised one INFO for every dev lock although D-04 reports an ERROR for a non-root source.
- **Proof:** `test_exit_3_recovery_uses_the_checkout_venv` fails on the previous `shim_core.py` and passes after the fix; `pytest tests/test_runtime_*.py` 114 passed; `pytest tests/ --ignore=tests/integration` 4218 passed; `livespec conventions verify --feature 083-pinned-runtime-isolation` PASS.
- **Reviews:** spec and plan reviewed again at `--review-max-chars 120000` by independent native claude-opus-5-5 reviewers, one batch each, prepared by the installed runtime `21-71f1e0d1b3d3` (35/35 covered each, complete and ready, no blocker). The checkout code (feature 089 and 090 prompts) also reviewed both, ready, after one plan correction round (Steps 2 and 3); its receipts are not readable by the installed runtime (`reviewed` and `qe_assessment` fields), so the committed state keeps the installed-runtime receipts, which both runtimes accept.
- **Gate:** `livespec validate .specs/features/083-pinned-runtime-isolation --progression implement --model claude-opus-5-5 --review-max-chars 120000` → `Progression: READY`, with the installed `livespec` and with this checkout's CLI.
- **Gaps closed:** AC-005 recovery text (D-11), AC-016 dev-lock wording (D-04)
- **Remaining (non-blocking carry-over):** plan digest wording "sorted records" reads as kind-first order while the Definitions require path order (code sorts by path); the documented 300-line deviation of `cli.py`, `doctor/scanner.py` and `pipeline.py` has no explicit approval; D-02 and D-06 have no AC; the stack still lists pip + venv while D-11 uses `uv`; AC-016 "for any project" versus the LiveSpec-root precedence of AC-017.
- **Author:** spec-fix (claude-opus-5-5)

<!-- finalize:spec-fix:2026-10-15:5c6d3cbb -->

## 2026-10-15 — [Bugfix]: Install applies the evidence rules of the installed commit

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** `validator/runtime/evidence.py` (new), `validator/runtime/git_tree.py`, `validator/runtime/models.py`, `validator/runtime/snapshot.py`, `docs/cli-reference.md`, `tests/test_runtime_snapshot_evidence.py`, `tests/runtime_support.py`
- **Cause:** inclusion rules came only from the running CLI. `21-71f1e0d1b3d3` was built by the older `21-3c1e6a776500` and has no `tests/`, so `livespec conventions verify` fails with `fixture missing: tests/fixtures/conventions_ast/ts/no_as_any/pass.ts`; later installs reused it (`reused`) without noticing.
- **Fix:** the target commit's `SNAPSHOT_TEST_EVIDENCE` and its AST catalogs' cited fixtures and tests also ship; a build citing a missing file is refused before publication; a reused snapshot missing cited evidence is refused with the commands to rebuild it.
- **Proof:** the three regression tests failed before the fix (RED receipt) and pass after it (GREEN receipt). On a copy of the real `21-71f1e0d1b3d3`, install exits 1 and lists the 15 missing paths; a fresh install of `71f1e0d` into a temporary home has none. Full suite: 4152 passed, 56 skipped; the only failure, a `ui-form` generation witness, changes on each run and passes alone.
- **Gate:** bugfix gate FALLBACK (`tests/runtime_support.py` is an existing test support file); the complete gate is BLOCKED by `clarify_not_ready:stale_or_incomplete_spec_review`, stale since c0381aa changed FR-001 on 2026-10-13. Conventions PASS (repo and feature scope).
- **Gaps closed:** FR-001, FR-003 (snapshot completeness)
- **Remaining:** fresh spec review for 083 before the complete gate can pass.
- **Author:** spec-fix (claude-opus-5-5)


## 2026-10-15 — [Bugfix]: Declared evidence and lost install races checked for completeness

- **Type:** Bug Fix (PR #45 review)
- **Spec modified:** No
- **Code modified:** `validator/runtime/evidence.py` (`missing_evidence` also requires every `SNAPSHOT_TEST_EVIDENCE` entry the tree declares: a directory for an entry ending in `/`, a file otherwise), `validator/runtime/snapshot.py` (a concurrent install that loses the rename checks the winner's completeness before reusing it)
- **Cause:** completeness covered only AST catalog citations, so evidence declared only by the policy could be missing from a build or a reused snapshot; and the lost-race reuse path verified the digest but not completeness, so an older winner could be activated incomplete.
- **Proof:** `test_install_refuses_a_commit_missing_evidence_its_policy_declares` and `test_lost_rename_race_refuses_an_incomplete_winner` fail on the previous code and pass after the fix; `pytest tests/test_runtime_*.py` 120 passed; ruff, mypy and pyright clean.
- **Gaps closed:** FR-001, FR-003 (snapshot completeness)
- **Author:** claude-code
