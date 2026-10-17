# Changelog

> Global changelog for LiveSpec. One entry per feature/bugfix/refactor.
> Per-feature details live in `.specs/features/<feature-slug>/changelog.md`.
>
> Last updated: 2026-10-17

---

## 2026-10-17 — [Feature 081] Bugfix: honor spec-specify review opt-out in goals

- `--no-review` and `-N` select specification preparation without a spec-review task or receipt; default review, other commands and semantic progression guards remain required. Read the [regressions](../tests/test_specify_review_goal.py) for contract/checklist selection, native goal closure and review boundaries.

## 2026-10-16 — [Feature 078] Bugfix: verify documentary-only acceptance without unrelated execution

- Nonempty all-review inventories require complete current reviews at proof, archive and archive-read; mixed/runtime inventories retain execution receipts. Explicit success criteria and remote delivery evidence remain required.

## 2026-10-16 — [Feature 094] Bugfix: prevent Git revision batch pipe deadlocks

- Feed revision queries from a temporary file; raw commit verification, Git environment guards and the 60-second bound remain. Real 605-object duplex regression RED/GREEN and 22 targeted tests pass.

## 2026-10-16 — [Feature 063] Bugfix: resolve mapped CI/configuration and documentation scopes

- CI-only mappings now produce conventions receipts; source/AST support and declared-linter failures stay unchanged. Scope, mixed mappings, missing files and canonical path boundaries covered; independent native review PASS.

## 2026-10-16 — Bound test execution and require only necessary validation with declared long-running exceptions
<!-- finalize:spec-feature:2026-10-16:d775ec24 -->

## 2026-10-16 — [Feature 095] Test: 100% AC covered (5/5), 0 tests generated

- Inspect [the test report](features/095-test-time-budgets/run/2026-10-16-test.md): runner-owned certification PASS, 5 tests in 0.61s; independent delivery review pending.

## 2026-10-16 — Plan created: Test Time Budgets — 3 implementation steps, 1 state diagram; necessary tests and bounded recovery
<!-- finalize:spec-plan:2026-10-16:bb751413 -->

## 2026-10-16 — [Feature 095] Spec created: Test Time Budgets — 3 stories, 5 AC, 7 FR
<!-- finalize:spec-specify:2026-10-16:e7daafa0 -->

## 2026-10-15 — Bugfix: [093](features/093-configured-review-identity/changelog.md): a goal `--model` flag without value raises `review_model_required` instead of binding the configured model.

## 2026-10-15 — [Feature 083] Fix: install applies the installed commit's conventions evidence rules and refuses an incomplete snapshot (FR-001, FR-003)

## 2026-10-15 — [093](features/093-configured-review-identity/changelog.md): spec and plan reviews complete and ready (native, `claude-opus-5-5`); delivery lane now light.

## 2026-10-15 — [093](features/093-configured-review-identity/changelog.md): goal render, progressions and the delivery lane take the reviewer model and budget from `.specs/semantic/config.yaml` when no option names them, and stop with `review_model_required` otherwise; out-of-bounds budgets are refused, never clamped.
<!-- finalize:spec-implement:2026-10-15:8c213f7b -->

## 2026-10-15 — [Feature 083] Fix: 2/2 review gaps closed (shim exit-3 recovery uses LiveSpec's venv with --source/--ref; AC-016 dev-lock wording aligned with D-04); spec and plan reviews refreshed at 120000 characters, implement progression READY
<!-- finalize:spec-fix:2026-10-15:5c6d3cbb -->

## 2026-10-15 — [Feature 083] Spec refined: user approvals of `--no-activate`, the `.livespec-path` pin warning and plan decisions D-01 to D-15 recorded in Clarifications; plan D-11 uses LiveSpec's venv; spec and plan reviews refreshed at 120000 characters, implement progression READY

## 2026-10-15 — Bugfix: 090 carried review warnings closed

- [090](features/090-minimal-plan-scope/changelog.md): a release proof must name a path, URL or numbered identifier and announce nothing; fence, `Evidence-class`, `<strong>` and no-break-space forms no longer hide or slip past a declaration; step numbers are bounded; `--progression ship` blocks with `release_evidence_unreadable` instead of a raw `PermissionError`.

## 2026-10-15 — Feature: Minimal plan scope and release evidence

- [090](features/090-minimal-plan-scope/changelog.md): the native rule `system/minimal-spec-scope.md` and the plan review prompt report every mechanism no FR, AC or constitution rule asks for (blocking unless a justified technical necessity); a plan step may declare `**Evidence class:** release`, listed as pending by the implement goal without blocking `finalize` and required by `/spec-ship` through `livespec validate <feature-dir> --progression ship`.

## 2026-10-14 — Feature: Verified review continuity

- [094](features/094-verified-review-continuity/changelog.md): the reviewed context stores every source role, and a spec revision record is verified against the commit it was opened at, so a hand-written record no longer lets stale reviews pass implementation.

## 2026-10-13 — Feature: Reviews that stay current and a contestable criticality

- [089](features/089-stable-review-identity/changelog.md): spec and plan reviews become stale only when FR, AC or Gherkin change, never for edge cases, Quality Engineering, formatting or the review budget; `livespec delivery revision open|close|status` revises the spec during implementation with one new review at the end.
- [086](features/086-risk-proportional-delivery/changelog.md): the spec reviewer's `qe_assessment` can contest an author High criticality (`criticality_contested`) or raise it; the reviewed QE section is never lowered by a later edit.
- [093](features/093-configured-review-identity/changelog.md): specified with a plan, not implemented (configured reviewer model and budget, moved from 089).

## 2026-10-13 — 085 ai-ressources located through AIRESOURCES or the recorded project path, without hard-coded fallback
<!-- finalize:spec-feature:2026-10-13:72cf8076 -->

## 2026-10-13 — [Feature 085] Test: 100% AC covered (11/11), 0 tests generated
<!-- finalize:spec-test:2026-10-13:477becbc -->

## 2026-10-13 — [Feature 085] Implemented in code: shared ai-ressources resolution (AIRESOURCES, then recorded path, else explicit error) routed through 7 consumers; certification pending
<!-- finalize:spec-implement:2026-10-13:cedd6521 -->

## 2026-10-13 — [Feature 085] Plan created: Locate ai-ressources Without Hard-Coded Paths — 6 implementation steps, 1 diagram
<!-- finalize:spec-plan:2026-10-13:5f189e4f -->

## 2026-10-13 — [Feature 085] Spec created: Locate ai-ressources Without Hard-Coded Paths — 4 stories, 11 AC, 7 FR
<!-- finalize:spec-specify:2026-10-13:e8bcdd29 -->

## 2026-10-13 — Feature: Lighter delivery gates (Handy findings)

- [086](features/086-risk-proportional-delivery/changelog.md): `livespec delivery lane` selects a light or full lane from the reviewed QE classification; steps run only tests, lint, format and conventions; one independent native review of the complete diff at the end of the feature (`livespec delivery review prepare|record|verify`), capped at two correction rounds.
- [087](features/087-anchor-derived-acceptance/changelog.md): `livespec test --derive-mapping` derives the AC-to-assertion mapping from `@spec AC-xxx` test anchors; a derived mapping is certified without a mapping review.
- [088](features/088-capped-reviews/changelog.md): spec and plan reviews are ready once no blocker remains, carry warnings over, approve justified technical scope and report `round_cap_reached`; vague words no longer block.
- [090](features/090-minimal-plan-scope/changelog.md), [091](features/091-specify-close/changelog.md), [092](features/092-init-onboarding/changelog.md): specified with a plan, not implemented.

## 2026-10-13 — Feature: Cargo execution runner

- [085](features/085-cargo-execution-runner/changelog.md): `livespec test --execution-command 'cargo test ...' --report-adapter junit` certifies Rust tests through a trusted Cargo runner (target runner + workspace wrapper, one process per test, stable LLVM coverage assertion trace, faithful failed/ignored/filtered outcomes, explicit gaps).
## 2026-10-13 — Bugfix: Generated eslint gate uses the local binary

- [061](features/061-conventions-gates-engine/changelog.md): `conventions gates init` writes `node_modules/.bin/eslint . --format json` when eslint is installed or declared locally, instead of a bare `eslint` that fails with `command not found`.

## 2026-10-13 — Bugfix: Finalized changelog entries pass validation

- [058](features/058-deterministic-finalization/changelog.md): `finalize apply` writes `## YYYY-MM-DD — [Tag]: text`, the heading `livespec validate` requires, and the skill and template examples use it too; marked `###` entries from earlier finalizations stay valid.

## 2026-10-13 — Bugfix: Review status keeps semantic reviews current

- [078](features/078-requirement-evidence-integrity/changelog.md): a `finalize apply --status` transition to or from `Review` no longer makes spec and plan reviews stale; an AC change still does. A stale review caused by another reviewer model now reports `spec_review_model_mismatch`.

## 2026-10-13 — Bugfix: Pinned snapshots ship the conventions test evidence

- [083](features/083-pinned-runtime-isolation/changelog.md): `livespec runtime install` keeps `tests/fixtures/conventions_ast/` and the deterministic test files the bundled catalogs cite, so `conventions verify` no longer reports `fixture missing` and is no longer always BLOCKED under a pinned runtime.

## 2026-10-13 — Bugfix: Execution capture stays inside the project

- [078](features/078-requirement-evidence-integrity/changelog.md): `livespec test` no longer follows links that leave the project. Paths that git ignores and agent tooling directories (`.agent-sync.local`, `.claude`, `.agents`, `.codex`) are out of scope, and an external link is bound by its link text instead of invalidating the capture (scope policy 078.2).

## 2026-10-13 — [Feature 050] Bugfix: native quality review

- Read the [instruction correction](features/050-agent-sync-migration/changelog.md): successful steps and pre-commit finalization use an independent native reviewer with effort `high`, preserving check evidence, blocking findings and the index. Historical user-hook replacement is documented; typed LiveSpec gates remain required.

## 2026-10-13 — [Feature 079] Fix: 1/1 gaps closed (FR-002) — CI installs public Penflow pinned at dd356b9 without credential
<!-- finalize:spec-fix:2026-10-13:5a48c61f -->

## 2026-10-13 — [Feature 079] Check: 55% verified (3/5 FR, 3/6 AC) — FR-002 public Penflow pin missing in CI, AC-006 corpus drift, AC-005 pending
<!-- finalize:spec-check:2026-10-13:4cb75000 -->

## 2026-10-13 — [Feature 079] Spec refined: Penflow is a public dependency pinned to verified commit dd356b9 without credential — FR-002/AC-002 reworded, IDs preserved
<!-- finalize:spec-refine:2026-10-13:7747cdfe -->

## 2026-10-12 — Bugfix: Stop conditions keep the caller runtime

- Read [081's bugfix trace](features/081-lightweight-outcome-goals/changelog.md): a consumer-local `validator` package can no longer return a false successful outcome; both stop conditions retain the consumer working directory and their 300-second bound.

## 2026-10-12 — Bugfix: CI parity on Python 3.12

- [081](features/081-lightweight-outcome-goals/changelog.md): `goal prove --evidence '<json>'` no longer fails on Python 3.12 when the inline JSON exceeds the filename limit; the deadline test uses a real profile.
- [035](features/035-unified-cli-surface/changelog.md): the help-example test strips Rich ANSI styling emitted under GitHub Actions.

## 2026-10-12 — Bugfix: PR #36 review findings

- [081](features/081-lightweight-outcome-goals/changelog.md): `livespec validate <path>` fails (exit 2) for a missing explicit target, so a never-created feature cannot satisfy its goal stop condition.
- [083](features/083-pinned-runtime-isolation/changelog.md): runtime link discovery never follows a symlinked or escaping link directory; an unreadable `.specs/.livespec-path` is reported as a broken reference instead of crashing.

## 2026-10-12 — Bugfix: ReDoS in the Delphi family detector

- [082](features/082-conventions-gate-signal/changelog.md): the Delphi empty-handler detector uses an unambiguous `\bexcept\s+end\s*;` instead of a pattern with exponential backtracking (CodeQL py/redos, high).

## 2026-10-12 — Bugfix: CI uses the locked toolchain

- [079](features/079-validator-ci-prerequisites/changelog.md): both CI jobs install the exact `uv.lock` versions instead of the newest ruff/mypy, so CI and local runs agree; the mypy 2.4 return-type finding in `validator/init_profile.py` is fixed.

## 2026-10-12 — Bugfix: CI Ruff scope excludes external checkouts

- [079](features/079-validator-ci-prerequisites/changelog.md): `.ci-deps` (pinned ai-ressources and penflow checkouts) is excluded from Ruff, which failed CI on a Markdown code block in the external corpus.

## 2026-10-12 — Spec Update: registry statuses aligned after stabilization merges

- README registry aligned to spec.md for [028](features/028-ui-runner-web/spec.md), [030](features/030-ui-runner-ios-watchos/spec.md), [031](features/031-ui-runner-android/spec.md) and [033](features/033-smart-test-selection/spec.md) (Implemented); [036](features/036-multi-surface-detection-and-migration/changelog.md) spec.md moves Draft -> Planned (plan present, no implementation map). 035 and 080 were already aligned (In Progress) by their merged fixes.
- [056](features/056-executable-user-journeys/implementation.md) FR-007 status note no longer cites `surfaces.yaml` as a mapped source file (coherence R3.1). The autonomous-init recovery tests get a 30 s wrapper budget so `pytest -n auto` no longer times out; `.coverage` data files are ignored.
- `run_capability` (`validator/drivers/runner.py`) splits the skip result and the 035 AC-002 test-path append into helpers after the merge pushed it past the 60-line convention limit (behavior unchanged); `conventions verify --feature repo` passes again.

## 2026-10-12 — Bugfix: audit bugs through the bugfix lane (084)

- [055](features/055-spec-doctor-project-health/changelog.md): doctor reports suppressed in-progress coherence findings as INFO `[in-progress, Nmin]` and attributes findings through `dir_name` (R3 contexts gain `dir_name`); lane ELIGIBLE (3 files, 55 lines), RED/GREEN receipts in implementation.md.
- [014](features/014-supervisor-contracts/changelog.md): spec-feature `--resume` resolves the latest `pipeline.md` with `ls -t .specs/features/*/pipeline.md` instead of the nonexistent `livespec pipeline latest`; new guard test checks every `livespec` command path cited by a skill; lane ELIGIBLE (3 files, 60 lines).
- [016](features/016-cross-language-test-driver-architecture/changelog.md): built-in driver scripts resolve beside their shipped manifest (`livespec/drivers/scripts/`), custom `.specs/drivers` scripts stay project-relative; lane ELIGIBLE (2 files, 58 lines).
- [037](features/037-test-multi-runner-integration/changelog.md): Web/XCUITest/Maestro handlers accept the `RunnerHandler` keywords (`**kwargs: Any`) and `Path | str` baselines, XCUITest/Maestro reuse the web `UICapabilityResult`, the registry drops its `cast` (pyright clean) and stale yaml suppressions go; lane ELIGIBLE (5 files, 175 lines).

## 2026-10-12 — [Feature 084] Bugfix lane: livespec bugfix capture/gate/record and /spec-fix --bugfix (scoped gate, explicit fallback)
<!-- finalize:spec-feature:2026-10-12:a6abad0a -->

## 2026-10-12 — Bugfix: declare unit-test dependencies (audit batch)

- [079](features/079-validator-ci-prerequisites/changelog.md): `click`, `jsonschema` and `pluggy` move into the `dev` extra (typer 0.27 vendors its own click, so they only arrived through `integration`); `uv.lock` regenerated and a guard test checks every unit-suite third-party import against runtime/dev requirements.

## 2026-10-12 — Bugfix: missing requirements of features 035 and 056 implemented

- [Feature 056](features/056-executable-user-journeys/changelog.md) Fix: AC-003, AC-004 and AC-015 were marked done but not implemented on the v2 path. `wait` now takes `until`/`reason` (bounded waits in Playwright, XCUITest and Maestro, `wait_reason_missing` warning), and manual journeys require `manual_reason`. Also fixed: FR-005 `select` (Playwright) and FR-007 portable XCUITest destination, with no hardcoded `STRAPTUITests`. Spec clarified and plan rewritten on the v2 pipeline after independent reviews.
- [Feature 035](features/035-unified-cli-surface/changelog.md) Fix: every unified command's `--help` ends with an executable example (AC-013). Human decisions applied: constitution exit codes 0/1/2/3/130, base branch `origin/HEAD` then main/master/develop/dev, CI summary on stderr with `--json`, and real `--feature` selection through `SmartTestSelector` plus the additive driver field `test_selection: append` ([016](features/016-cross-language-test-driver-architecture/changelog.md)). implementation.md created; status In Progress pending the feature-scope conventions debt.

## 2026-10-12 — Refactor: dead-code resolution (wire or retire)

- Wired: the Python driver now resolves `{module}`/`{report_path}`/`{threshold}` (via the previously unused `detect_python_module`), fixing `livespec test` on Python projects (017); iOS/Android UI runner detection now reads the `ios.yaml`/`android.yaml` `detect:` blocks (030, 031).
- Retired (FR/AC marked Removed or remapped): Go, Swift and syrupy detectors and the unused Cargo.toml/JVM build-file helpers (017, 019–022); `deduplicate_tests` and a tautological test (006); journey assignment/bootstrap helpers and the native visual evaluator (057).
- Follow-up (user decisions): TypeScript commands now follow the detected jest/vitest runner and npm/pnpm/yarn/bun manager with override priority and Stryker/fast-check skip hints (018); web runner detection reads `web.yaml` (028); the iOS runner reads `test_scheme`/`scenarios` from the project `ios.yaml` (explicit > project config > detection) (030); LLM visual contracts are evaluated by the agent and verified by `livespec journey visual-verify`, replacing the unwired `llm_visual.py` (057). EC-002 stays a judgment call for `/spec-implement`.

## 2026-10-12 — Bugfix: [Feature 080] Unsupported manifests recorded, missing package manager warns; readiness gate closed

- User decision recorded in [080](features/080-autonomous-from-code-recovery/changelog.md) (FR-001, new AC-007, IDs preserved): an unsupported manifest (`go.mod`, `Gemfile`, `pom.xml`…) beside supported ones is recorded as unsupported/unknown in `bootstrap-profile.json`, `project.md` and `bootstrap-recap.md`, and bootstrap continues with the supported ecosystems (JavaScript/TypeScript with bun/npm/pnpm/yarn, Python via `pyproject.toml`, Rust, Tauri); unsupported-only projects fail naming the files; a `package.json` without manager evidence warns (`WARNING:` on stderr) and never fails.
- Code modified: `validator/init_profile.py`, `validator/init_documents.py`, `validator/init_from_code.py` (TDD). Spec status aligned to In Progress. Fresh independent spec and plan reviews are ready; `validate --progression implement` returns READY.

## 2026-10-12 — Spec Update: [Feature 077] AC-009 / FR-008 clarified, readiness gate closed

- User decision recorded in [077](features/077-penflow-cumulative-verdict-consumer/changelog.md): an authenticated, accepted Brainstorm import is the certifying `penflow authority collect` response (report SHA-256 plus exact sorted file inventory); a bounded archive is confined to `.specs/penflow-authority/<digest>/`, holds only inventoried files, admits no path escape and has no size cap. Current behavior, no code change; requirement IDs preserved.
- Fresh independent spec and plan reviews are ready; `validate --progression implement` returns READY, closing the pending Penflow CLI resolution spec-fix.

## 2026-10-12 — Refactor: test-suite cleanup lot 5

- Removed or replaced tautological, vacuous and always-skipped tests across features 001, 002, 007, 009, 019, 020, 022, 030, 031, 037, 046 and 078. This includes the unmapped `tests/test_ui_runner_cli.py` (a redundant registry check) and `tests/test_ui_runner_tauri.py`, where the driver-capability test now pins both states instead of asserting nothing when tauri-driver is installed. The semantic matrix went from 171 to 42 cases, the visual gate stays at 94.41% coverage, and no production code changed.
- Corrected traceability: feature 030 FR-007/FR-008 are Missing, because their mapped tests were unconditional skips. Feature 007's test table now matches FR-005 (5 tests).

## 2026-10-12 — Refactor: test cleanup lot 4 (legitimate assertions only)

- Plan-review exit-code tests run the CLI instead of recomputing its expression ([001](features/001-auto-llm-review/changelog.md)); web-runner output-path tests stub Playwright instead of launching `npx` ([028](features/028-ui-runner-web/changelog.md)); review-identity and Analyze combinations trimmed to one case per branch ([078](features/078-requirement-evidence-integrity/changelog.md)); preflight YAML parsing, link-capability fallback, schema and ship-header tests assert real values ([034](features/034-preflight-autofix/changelog.md) records an open `pip install -e` parsing defect).
- Kept on purpose: `tests/test_penflow_contract_command_contract.py` (documentation ACs of 051, 054, 066 and 077), `TestTruthFixes` in the run-artifact suite (039.1 AC-012), the per-runner dispatcher tests named by 037 SC-002, and `tests/test_review_api.py` (001 FR-010/FR-011).

## 2026-10-12 — Refactor: remove the `--mutate` and `--experimental-multi-model` stubs

- `livespec validate --mutate` only printed a hint to run this repository's own pytest and exited 0; `--experimental-multi-model` only printed "not yet integrated" and exited 0. Both options, their legacy-conflict entries and the never-imported modules behind them (`validator/semantic/mutations.py`, `validator/semantic/multi_model.py`) are removed. Static grep over `validator/`, `tests/`, `scripts/`, `.agent-sync/`, `templates/`, `hooks/` and `pyproject.toml` found no importer, no string-based import and no entry point. Driver mutation testing (`livespec mutation`, feature 016) is unaffected.
- The scorecard Axis 4 placeholder (constant 50) is kept: it still contributes to every published total and removing it would reweight the scorecard. Its pinning test and the weight-constant test are removed; `--contradiction-only` tests no longer depend on the machine's provider.
- No LiveSpec feature owns Layer 4. Code modified: `validator/cli.py`, `.specs/roadmap.md`, `tests/test_scorecard.py`, `tests/test_semantic_operation_matrix.py`.

## 2026-10-12 — Bugfix: coherence suppress_if_creating grace window never fired

- The rule engine looked up the feature under `context["feature_dir"]`, a key no coherence rule emits; it now reads the canonical `dir_name` key, so violations of R1.2, R1.3, R2.1, R4.2 and R4.3 on a spec edited less than 30 minutes ago are demoted to INFO with the `[in-progress, Nmin]` tag, as described in [the Layer 2 design](../docs/superpowers/specs/2026-04-02-layer2-coherence-validation-design.md). `--no-suppress` and the finalize verifier still see them.
- R2.2 no longer requests suppression, matching the design table.
- No LiveSpec feature owns the Layer 2 engine; `tests/test_rule_engine.py` now exercises the real demotion, the aged case and non-empty filter results. Code modified: `validator/coherence/rule_engine.py`, `validator/coherence/rules/r2_status_files.py`, `tests/test_rule_engine.py`, `tests/test_coherence_cli.py`.

## 2026-10-12 — Refactor: test-suite cleanup lot 3 (goal, journey, locks, manifests, Penflow models)

- 1033 -> 911 test cases in the lot with no validator line losing coverage (23800 -> 23807 covered lines); no new failure in the unit suite.
- Lying or vacuous tests corrected: the lock resume test now reaches the resume branch; 056 AC-004 (fixed-wait warning) and AC-015 (manual reason) were certified by tests that never exercised them and are now recorded as Missing.
- Constant, library and fixture self-checks replaced by observable behaviour (hook variables, slug regex doc, identity policy version, specStatus marker, Maestro detect rules, v21 scaffold wrapper).
- Label-only parametrization and duplicated cases removed from goal pairing/proof, goal contracts, graph builder, init goal profiles, journey fixtures and Penflow approval models; mapping rows of 031 and 059 updated.

## 2026-10-12 — Refactor: test suite cleanup lot 2 and dead embeddings stub removal

- Removed `validator/semantic/embeddings.py` (imported only by its own test; `compute_embedding` raised `NotImplementedError`), the `livespec validate --reindex` stub that only printed "not yet integrated", and their tests (`tests/test_embeddings.py`, `test_scorecard.py::test_reindex_stub`, the `--reindex` legacy-option case). The roadmap "Embedding reindex" item stays open.
- Weak tests now exercise the real behaviour: expectations rules are parsed with `validator.expectations`, the score clamp is proven at 0, economy-mode guards cannot pass on zero blocks, JS/TS syntax checks skip explicitly without node/`node_modules/typescript` instead of passing vacuously.
- Duplicated and label-only parametrised cases trimmed in features 026, 047, 063, 078 and 079 (see their changelogs); no production behaviour changed besides the removed stub.

## 2026-10-12 — Refactor: test-suite cleanup, lot 1

- Removed tests that exercised no LiveSpec code (self-tested helpers, Markdown word searches, a static fixture checked by test-only validators, Node failing on a missing file) and duplicates (command aliases, visual dispatch, driver detector cases, gates init, help smoke tests).
- Replaced prose pins with machine contracts: documented `livespec conventions` and `livespec hooks resolve` invocations must resolve in the real CLI; migration v22 runs end to end; surface generator tests parse the YAML they would write.
- Fixed weak or environment-dependent tests: coherence JSON, `--smart`, distinct AC/FR numbering, cwd-independent paths, explicit skips when `node` is absent.
- Feature changelogs: 002, 004, 005.1, 011, 014, 017 to 022, 026, 030, 031, 035, 037, 039, 048, 049, 050, 065, 073, 078.

## 2026-10-12 — [Feature 083] Fix: consumer migration command executable as documented (venv interpreter)
<!-- finalize:spec-fix:2026-10-12:5728df60 -->

## 2026-10-12 — [Feature 080] Fix: init probes tolerate zombie-group EPERM; init tests deterministic and hermetic (gate blocked on FR-001 decision)
<!-- finalize:spec-fix:2026-10-12:7710d267 -->

## 2026-10-12 — [Feature 079] Fix: convention manifest tests and CI cleanup step made hermetic
<!-- finalize:spec-fix:2026-10-12:7208ea4d -->

## 2026-10-12 — [Feature 078] Fix: warm-cache regression independent of PYTHONDONTWRITEBYTECODE
<!-- finalize:spec-fix:2026-10-12:b581f1b1 -->

## 2026-10-12 — [Feature 077] Fix: Penflow CLI resolved beside the interpreter before PATH (gate blocked on AC-009 decision)
<!-- finalize:spec-fix:2026-10-12:771b8f83 -->

## 2026-10-12 — Bugfix: integrate features 081, 082 and 083 on main

- Conventions source collection skips `.claude/worktrees/**`, `.worktrees/**` and any nested directory holding a `.git` entry; repo scope returns PASS against [the versioned baseline](conventions/baseline.json) without rewriting it.
- spec-system rules and the supervisor/verifier prompts describe the 082 ratchet: new repo-scope violations fail, recorded debt is reported separately, feature closure requires feature-scope PASS.
- Runtime receipts and review caches committed by 081/083 are no longer versioned, as required by the 082 ignore rules.

## 2026-10-12 — Feature 083 pipeline complete: pinned runtime isolation (18/18 AC certified, audit clean)
<!-- finalize:spec-feature:2026-10-12:21b73207 -->

## 2026-10-12 — [Feature 083] Test: 100% AC covered (18/18), 1 test generated (re-certification after audit corrections)

## 2026-10-12 — Feature 083 second audit pass: redirected-path refusal, escaped defect values, lock-last publication, strict shim current manifest

## 2026-10-11 — Feature 083 audit corrections: defect input validation, staging symlink containment, strict manifest, read-only verification, locked selection rollback
<!-- finalize:spec-implement:2026-10-11:c4506f10 -->

## 2026-10-11 — [Feature 083] Test: 100% AC covered (18/18), 3 tests generated

## 2026-10-11 — Feature 083 implemented: livespec runtime install/pin/upgrade/dev/status/defect, shim, drift scanner, tool/project boundary (18/18 AC certified)
<!-- finalize:spec-implement:2026-10-11:027bff35 -->

## 2026-10-11 — Feature 083 implementation: livespec runtime install/pin/upgrade/dev/status/defect, shim, drift scanner, boundary rule (In Progress; conventions certification pending)
<!-- finalize:spec-implement:2026-10-11:68d31117 -->

## 2026-10-11 — Feature 083 plan created: Pinned Runtime Isolation, 9 implementation steps, 3 diagrams, ADR-004
<!-- finalize:spec-plan:2026-10-11:5ddfddac -->

## 2026-10-11 — [Feature 083] Spec created: Pinned Runtime Isolation — 7 stories, 18 AC, 13 FR
<!-- finalize:spec-specify:2026-10-11:60b23cb4 -->

## 2026-10-11 — Feature 082 implemented: conventions gate signal (fixture exclusion, family grouping, framework applicability, repo baseline ratchet)
<!-- finalize:spec-implement:2026-10-11:41daaa07 -->

## 2026-10-10 — Feature 082 Plan created: Conventions Gate Signal — 6 implementation steps, 2 diagrams
<!-- finalize:spec-plan:2026-10-10:a5ebf692 -->

## 2026-10-10 — Feature 082 Spec created: Conventions Gate Signal — 3 stories, 8 AC, 7 FR
<!-- finalize:spec-specify:2026-10-10:e39214b3 -->

## 2026-10-10 — 081 Lightweight outcome-based goals — one stop condition per autonomous run, recoverable contracts, bounded retries
<!-- finalize:spec-feature:2026-10-10:2db73a41 -->

## 2026-10-09 — Bugfix: observed autonomous init and safe force recovery

- Read [the recovery implementation](features/080-autonomous-from-code-recovery/implementation.md): retain observed hybrid stacks, back up owned artifacts, isolate mutable agents, run bounded tooling probes and verify current hook/integration identity.
- Current init contracts distinguish preview, autonomous and interactive obligations; backend success still requires authentic goal closure.
- Shipping documentation uses feature 080 because existing feature 079 belongs to Validator CI Prerequisites. Historical local goals and archives keep their original identities; feature-wide conventions/review certification is not claimed.

## 2026-09-08 — Feature 076 V5 temporary ownership verified; native AC-006 only; full-feature and main delivery not certified.
<!-- finalize:spec-fix:2026-09-08:2d0a611e -->

## 2026-09-08 — Feature079 v5 fixture isolation verified; AC005 pending and AC006 partial; no lifecycle promotion.
<!-- finalize:spec-fix:2026-09-08:e063bb60 -->

## 2026-09-08 — Feature079 gen4 Fix: deterministic CI, pinned private corpus and AST backend repaired; all local checks pass, AC002 native only, final CI/main pending.
<!-- finalize:spec-fix:2026-09-08:effa6511 -->

## 2026-09-08 — Feature079 gen4 Check: deterministic CI, private corpus and AST prerequisites inspected; local gates verified, bounded native evidence separate, final CI/main pending.
<!-- finalize:spec-check:2026-09-08:a8b53723 -->

## 2026-09-08 — Feature079 Fix: four local acceptance checks verified; browser installer repaired without changing test runtime; final CI remains pending.
<!-- finalize:spec-fix:2026-09-08:f5eb771d -->

## 2026-09-08 — Feature079 Check: local repair and native AC-002 verified; progress structure fixed; exact CI acceptance remains pending.
<!-- finalize:spec-check:2026-09-08:42b65563 -->

## 2026-09-07 — [Feature 079] Check: Pre-fix audit resumed

- Read [the 079 check report](features/079-validator-ci-prerequisites/checks/2026-09-07.md): preparation readiness verified; final implementation and same-SHA CI proof remain pending.

## 2026-09-07 — Fix independent pipeline closure: bound CLI/runtime, explicit feature and review identity, reject usage exit2.
<!-- finalize:spec-fix:2026-09-07:8403a3bf -->

## 2026-09-07 — 078: repair reviewed-spec coordinator binding, reject incomplete mapping reviews before execution, preserve active child waits and isolated snapshot evidence.
<!-- finalize:spec-fix:2026-09-07:73d32812 -->

## 2026-09-07 — 078: correct coordinator reviewed-spec acceptance and isolated snapshot inputs; full feature closure remains pending.
<!-- finalize:spec-fix:2026-09-07:a8c7a397 -->

## 2026-09-07 — Fix: 1/3 targeted gaps closed; 258 runtime bindings certified, initial076 baseline and complete agentic success remain unproven.
<!-- finalize:spec-fix:2026-09-07:32825067 -->

## 2026-09-06 — [Feature 078] Test: 100% AC definitions covered (16/16), 0 tests generated; deterministic scope passed with historical limits retained
<!-- finalize:spec-test:2026-09-06:aebeee31 -->

## 2026-09-06 — [Feature 078] Implementation lifecycle: requirement evidence integrity
<!-- finalize:spec-implement:2026-09-06:183269a4 -->

## 2026-09-06 — Requirement Evidence Integrity: linked four success criteria to existing steps and evidence; scope unchanged
<!-- finalize:spec-plan:2026-09-06:b64026f3 -->

## 2026-09-06 — Requirement Evidence Integrity: plan created with eight steps across three lots and explicit proof boundaries
<!-- finalize:spec-plan:2026-09-06:752c710f -->

## 2026-09-06 — Feature078: specify requirement evidence integrity across five axes
<!-- finalize:spec-specify:2026-09-06:165bc17e -->

## 2026-09-05 — [Feature 077] Implemented: Penflow cumulative verification consumer and governed lifecycle closure
<!-- finalize:spec-implement:2026-09-05:6ce4661e -->

## 2026-09-05 — Feature 077: Composed procedure and selector authority

Automatic active-plan policy union preserves earlier required procedures; the read-only pre-review C20 selector gate delegates to Penflow. Canonical fixture tests use the real CLI. Native source approval accepted; final runtime/closure/import proofs remain pending.

## 2026-09-04 — Preserve Feature 076 eager legacy task validation with 179 regressions
<!-- finalize:spec-test:2026-09-04:79b41969 -->

## 2026-09-04 — Preserve Feature 076 legacy task-field compatibility with 179 regressions
<!-- finalize:spec-test:2026-09-04:1faecba9 -->

## 2026-09-04 — Preserve Feature 076 non-init compatibility and cooperative archive boundary
<!-- finalize:spec-test:2026-09-04:43831902 -->

## 2026-09-04 — Close Feature 076 boundary review with 185 feature tests and confined archive publication
<!-- finalize:spec-test:2026-09-04:9398704c -->

## 2026-09-04 — Feature 076 final concurrency review closed: 183 feature tests and locked exclusive archive publication
<!-- finalize:spec-test:2026-09-04:c7b5977d -->

## 2026-09-04 — Feature 076 final publication verified: 182 feature tests and exclusive inode-owned archive publication
<!-- finalize:spec-test:2026-09-04:128dece7 -->

## 2026-09-04 — Feature 076 final fingerprint verified: 180 feature tests and inode-owned archive writes
<!-- finalize:spec-test:2026-09-04:9637faa2 -->

## 2026-09-04 — Feature 076 final security review closed: 177 feature tests, pinned archive traversal and ownership verified
<!-- finalize:spec-test:2026-09-04:b5339c37 -->

## 2026-09-04 — [Feature 076] Second security review closed: 175 feature tests, descriptor lifetime and ownership verified
<!-- finalize:spec-test:2026-09-04:ac9f0e2b -->

## 2026-09-04 — [Feature 076] Final audit remediation verified: descriptor-safe archive, typed boundaries, 170 feature tests
<!-- finalize:spec-test:2026-09-04:5d267080 -->

## 2026-09-04 — [Feature 076] Test: 100% AC covered (10/10), 11 tests generated — Feature PASS; one external catalog regression and six non-feature format files remain repository follow-up
<!-- finalize:spec-test:2026-09-04:24b126d1 -->

## 2026-09-04 — [Feature 076] Implemented after independent review: complete schema pairing, 158 feature cases, confined archive writes, strict non-init compatibility
<!-- finalize:spec-implement:2026-09-04:9e1ef40b -->

## 2026-09-04 — [Feature 076] Initial implementation completed: canonical fresh root, fail-closed proof, contained archive, strict non-init compatibility
<!-- finalize:spec-implement:2026-09-04:a98e152e -->

## 2026-09-04 — [Feature 076] Plan refined: explicit SC-002, SC-003, and SC-004 mappings to existing steps, tests, and quality gates

## 2026-09-04 — [Feature 076] Plan created: Spec Init Goal Bootstrap — 6 implementation steps, 3 diagrams
<!-- finalize:spec-plan:2026-09-04:89422724 -->

## 2026-09-04 — [Feature 076] Plan finalized: approved six-step implementation and quality-gate sequence
<!-- finalize:spec-plan:2026-09-04:28e16cfb -->

## 2026-09-04 — [Feature 076] Spec created: Spec Init Goal Bootstrap — 3 stories, 10 AC, 12 FR
<!-- finalize:spec-specify:2026-09-04:14b0e052 -->

## 2026-09-04 — [Feature 076] Spec refined: archive confinement, atomic pairing, external evidence boundary, and goal-state transitions clarified

## 2026-07-04 -- [Feature 075] Implemented: Design Direction Carry -- optional informative design direction line through generated specs without validation use

## 2026-07-04 -- [Feature 074] Implemented: Agent Device Proof Adapter -- journey run receipts, `livespec device proof`, fail-fast bundle guards, watchOS guidance, and tests

## 2026-06-30 — [Feature 073 Fix] Ship hygiene — full Ruff excludes only generated detector fixture payloads and local `.claude/output/`, Validator receipt kept as proof

## 2026-06-30 — [Feature 073 Fix] Reviewer FAIL follow-up — 564 ARS rules now have 564 callable wrappers/execution paths, 0 unreachable language-specific rules, and real-project ARS violations are blocking errors

## 2026-06-30 — [Feature 073 Fix] ARS row-level runtime — 564 executable CSV rows now map to 564 individual runtime rules with PASS/FAIL fixtures, 0 missing

## 2026-06-30 — [Feature 073 Fix] Immediate source decisions executable — 164 immediate sources executable/generated through 15 deterministic families, 28 conceptual/editorial deferred to Notion, 0 immediate non-executable

## 2026-06-30 — [Feature 073 Fix] ARS source decision manifest — 192/192 sources decided, 0 undecided; executable rules now require decision_kind/domain/detector metadata

## 2026-06-30 — [Feature 073 Fix] Feature-scoped verify JSON now exposes advisory/unsupported taxonomy in schema v1, matching receipt evidence

## 2026-06-30 — [Feature 073] Implemented: Exhaustive AI-res/ARS source manifest — verify JSON now proves 192/192 in-scope sources classified, 0 unclassified, with language/domain matrix and explicit exclusions

## 2026-06-29 — [Feature 072 Fix] Corrected AC-014 implementation map paths for `livespec doctor`

## 2026-06-29 — [Feature 072] Check: 100% verified (18/18 FR, 17/17 AC); conventions receipt PASS with 10 warnings

## 2026-06-29 — [Feature 072] /spec-feature complete: AST conventions rollout engine — implement/test/audit all green, full pytest 2281 passed, conventions receipt PASS
<!-- finalize:spec-feature:2026-06-29:3ef3e24f -->

## 2026-06-29 — [Feature 072] Test: 100% AC covered (17/17), 0 tests generated — targeted Ruff, pytest 177 passed, `.specs` validation, and conventions receipt PASS

## 2026-06-29 — [Feature 072] Implemented: Conventions AST Rule Engine — v1/v2 gates, AST observe/enforce engine, v2 receipts, mode-aware policy, active ast/high catalogue, and scoped conventions receipt repair
<!-- finalize:spec-implement:2026-06-29:7d37e57a -->
<!-- finalize:spec-implement:2026-06-29:58f6d072 -->

## 2026-06-29 — [Feature 072] Plan created: Conventions AST Rule Engine — phased AST conventions rollout with v1/v2 gates, receipts, backend, doctor/spec-check, and catalogue activation
<!-- finalize:spec-plan:2026-06-29:fdbed7ea -->

## 2026-06-29 — [Feature 072] Spec created: Conventions AST Rule Engine — 4 stories, 17 AC, 18 FR
<!-- finalize:spec-specify:2026-06-29:4d481d61 -->

## 2026-06-27 — [Feature 071] Check: 100% FR/AC verified; implementation and conventions PASS; AC format warning remains

## 2026-06-27 — [Feature 071] Implemented: QE Analysis Native Module — native QE context, `qe.analysis` goal task, structured evidence validation, additive user hooks

## 2026-06-27 — [Feature 070] Analyze Gate — retroactive spec+plan+mapping for read-only pre-impl gate; dogfooded Clarify (empty queue) + Analyze (0 CRITICAL/HIGH, exit 0)

## 2026-06-27 — [Feature 069] Plan created: Clarify Gate — 7 implementation steps (retroactive, maps to existing code), 1 state diagram
<!-- finalize:spec-plan:2026-06-27:d8275811 -->

## 2026-06-27 — [Feature 069] Spec created: Clarify Gate — 4 stories, 12 AC, 12 FR
<!-- finalize:spec-specify:2026-06-27:6ceeb87f -->

## 2026-06-26 — [Doctor Fix] Cleared all repo-level `livespec doctor` INFO traceability findings by adding missing source `@spec(...)` anchors.

## 2026-06-26 — [Feature 068] Check: spec-check PASS; tree validation, command audit, doctor, static tests, and Ruff checks green for evidence-first retry contract

## 2026-06-26 — [Feature 068] Implemented: Evidence-First Retry Contract — retry_hypothesis, retry_evidence, retry_result for failed commands and terminal interactions

## 2026-06-25 — [Feature 063 Fix] Feature-scoped conventions verification now uses current implementation mappings plus dirty source/test files, avoiding historical artifact link aggregation.

## 2026-06-25 — [Feature 063] Check: 100% FR/AC verified; conventions gate PASS (receipt `.specs/conventions/runs/20260625T194319Z/receipt.json`); Feature 063 artifacts PASS; project-wide tree validation PASS

## 2026-06-25 — [Feature 063 Fix] Conventions verify JSON now emits project-local receipts when `--feature` is explicit; repo-scope proof uses `--feature repo`.

## 2026-06-25 — [Feature 061 Fix] Conventions scanner now excludes generated dependency workspaces, including `node_modules/**`, `.mimocode/**`, caches, build outputs, and matching linter-reported paths.

## 2026-06-25 — [Feature 052 Fix] Stale-project migration recovery now allows internal `livespec goal render spec-migrate --save`, unblocking `/spec-migrate` Step 0 while keeping normal commands migration-gated.

## 2026-06-25 — [Feature 067] Check: clean after structural artifact fixes; 6/6 FR and 7/7 AC verified

## 2026-06-25 — [Feature 067 Fix] Closed structural artifact gaps: plan spec_ref, Mermaid block, progress Step table

## 2026-06-25 — [Feature 067] Check: 100% FR/AC verified; 3 structural artifact gaps in plan/progress

## 2026-06-25 — [Feature 067] Implemented: Visual Preview Proof Publishing — Markdown proof, Browser annotation URL, visual-preview fallback, receipt boundary

## 2026-06-17 — [Quality Gate] Make `mypy .` pass and add it to CI

## 2026-06-17 — [Feature 054 Fix] Block stale projects before normal LiveSpec commands and require migration

## 2026-06-17 — [Feature 046 Test] Measure visual_gate branch coverage and add targeted coverage tests

## 2026-06-15 — [Feature 066] Implemented: Handoff Input Compatibility — handoff-first Brainstorm import docs, Penflow bootstrap source resolution, lifecycle sync contract

## 2026-06-13 — [Feature 065 Fix] Make migration v22 scripts advisory, move SET_VERSION last, remove invalid semantic flag

## 2026-06-13 — [Feature 065] Implemented: Conventions Migration Docs — migration v22, conventions enforcement reference, README/spec-system/agent docs

## 2026-06-13 — [Feature 064 Fix] Correct Ruff scaffold semantics: remove file line-count as Ruff line-length and enable PLR

## 2026-06-13 — [Feature 064] Implemented: Conventions Bootstrap Remediation — preflight gates checks, scaffold templates, spec-fix conventions mode, split conventions CLI

## 2026-06-13 — [Feature 063 Fix] Wire supervisor-gate CLI, fix R7.2 denominator, scope conventions receipt to implementation commands

## 2026-06-13 — [Feature 063] Implemented: Conventions Blocking Pipeline — hard conventions receipt gate, R7 coherence, supervisor diff/hash/fresh locks

## 2026-06-12 — [Feature 062] Implemented: Conventions Rulebook Semantic — self-contained rulebook compiler, direct provider Engine C, waiver-aware verdicts, compile CLI
<!-- finalize:spec-implement:2026-06-12:3e197383 -->

## 2026-06-12 — [Feature 061 Refactor] Remove delegate_to and command wiring from conventions gates schema v1

## 2026-06-12 — [Feature 061 Fix] Critic cycle 4: bind delegate_to to executable basename and block unreadable source files

## 2026-06-12 — [Feature 061 Fix] Critic cycle 3: ignore freestyle delegate wiring, block timeout/encoding failures, document receipt audit boundary

## 2026-06-12 — [Feature 061 Fix] Critic P0/P1 hardening: Ruff JSON parsing, gates hash receipt validation, rule-specific delegate_to, stale gates blocking, ignored debt.json

## 2026-06-12 — [Feature 061] Feature: Initial conventions gates engine
<!-- finalize:spec-feature:2026-06-12:a140dc75 -->

## 2026-06-11 — [Feature 060] ### Pipeline: /spec-feature completed end-to-end
<!-- finalize:spec-feature:2026-06-11:61c37125 -->

## 2026-06-11 — [Feature 060] Test: 100% AC covered (15/15), 0 tests generated — 102/102 feature tests (0 skips), full no-LLM suite green, ruff + pyright clean

## 2026-06-11 — [Feature 060] Implemented: Journey Fixture Bootstrap Contract — fixtures.yaml contract, derived XCUITest bootstrap waits, 5 blocking validation rules, journeys-v2-3 + contract hash staleness, bootstrap failure reclassification, scaffold CLI + migration v21
<!-- finalize:spec-implement:2026-06-11:b2cd1c13 -->

## 2026-06-11 — Plan created: Journey Fixture Bootstrap Contract — 11 implementation steps, 4 diagrams
<!-- finalize:spec-plan:2026-06-11:8bbd6ff2 -->

## 2026-06-11 — [Feature 060] Spec created: Journey Fixture Bootstrap Contract — 5 stories, 15 AC, 11 FR
<!-- finalize:spec-specify:2026-06-11:15d1d511 -->

## 2026-06-11 — [Feature 059] /spec-feature pipeline complete — all phases done, 15 audit findings fixed, target gates green; full baseline has 1 pre-existing protected failure
<!-- finalize:spec-feature:2026-06-11:4089ae8a -->

## 2026-06-11 — [Feature 059] Check: 100% verified (11/11 FR, 15/15 AC); target implementation healthy, global tree/spec hygiene warnings recorded

## 2026-06-11 — [Feature 059] Test: 100% AC covered (15/15), 0 tests generated — targeted 218/218, unit 1824 passed (1 pre-existing protected failure), integration 3a 75/75
<!-- finalize:spec-test:2026-06-11:58a3c008 -->

## 2026-06-11 — [Feature 059] Implemented: Pipeline Verify Phase — enforced archive.run, supervisor Verify phase, artifact-backed SHIP_RESULT, transcript capture
<!-- finalize:spec-implement:2026-06-11:0cb1ffd0 -->

## 2026-06-11 — [Feature 059] Plan created: Pipeline Verify Phase — 10 implementation steps, 3 diagrams
<!-- finalize:spec-plan:2026-06-11:79911967 -->

## 2026-06-11 — [Feature 059] Spec created: Pipeline Verify Phase — 4 stories, 15 AC, 11 FR
<!-- finalize:spec-specify:2026-06-11:799a2740 -->

## 2026-06-11 — [Feature 039.1] Check: 100% verified (11/11 FR, 13/13 AC); warnings recorded for AC format, tree hygiene, and oversized tests

## 2026-06-10 — [Feature 039.1] /spec-feature pipeline complete — all phases done, audit findings fixed, gates green
<!-- finalize:spec-feature:2026-06-10:645cecd3 -->

## 2026-06-10 — [Feature 039.1] Test: 100% AC covered (13/13), 0 tests generated, feature suite green; full baseline has 1 pre-existing failure
<!-- finalize:spec-test:2026-06-10:cea2d0c7 -->

## 2026-06-10 — [Feature 039.1] Implemented: Goal Archive & Run Artifacts v2 — livespec goal archive (RunArtifact v2), shared verify-output engine, real preview.py, 039/040 truth-fixes
<!-- finalize:spec-implement:2026-06-10:2395e303 -->

## 2026-06-10 — [Feature 039.1] Plan created: Goal Archive & Run Artifacts v2 — 9 implementation steps, 4 diagrams
<!-- finalize:spec-plan:2026-06-10:362ef347 -->

## 2026-06-10 — [Feature 039.1] Spec created: Goal Archive & Run Artifacts v2 — 5 stories, 13 AC, 11 FR
<!-- finalize:spec-specify:2026-06-10:de700238 -->

## 2026-06-10 — 001 auto-llm-review: fix cc-hub codex provider schema passing (temp file + envelope unwrap + strict-mode normalization)
<!-- finalize:spec-fix:2026-06-10:24ee3265 -->

## 2026-06-10 — 058 deterministic-finalization: full /spec-feature pipeline complete (specify, plan, implement, test all green)
<!-- finalize:spec-feature:2026-06-10:96deb6de -->

## 2026-06-10 — [Feature 058] Test: 100% AC covered (12/12), 0 tests generated — 135/135 feature tests passing incl. chaos

## 2026-06-10 — [Feature 058] Implemented: Deterministic Finalization — livespec finalize apply/verify, finalize.registry goal evidence family, opt-in lock retry
<!-- finalize:spec-implement:2026-06-10:9a1dbf71 -->

## 2026-06-10 — [Feature 058] Plan created: Deterministic Finalization — 9 implementation steps, 4 diagrams

## 2026-06-10 — [Feature 058] Spec created: Deterministic Finalization — 4 stories, 12 AC, 10 FR

## 2026-06-09 — [Feature 057] Fix: 7/7 gaps closed (7 functional, 0 visual) — W51/W53 runner-ranking

## 2026-06-09 — [Feature 057] Fix: 3/3 gaps closed (3 functional, 0 visual) — XCUITest pre-suite hang

## 2026-06-09 — [Feature 057 Fix]: Closed the W31/W33/W35/W37 XCUITest simulator-destination correction chain accepted by V22 using the V21 W37 scope proof: journey runs resolve iOS/watchOS destinations from available `simctl` devices, pass `id=<UDID>` to `xcodebuild`, and boot/await the selected simulator instead of defaulting to unavailable `iPhone 16`. Strapt recompile, `$spec-test`, journey runs, `$git-commit`, and push remain out of scope.

## 2026-06-09 — [Feature 057] Fix: 3/3 gaps closed — XCUITest journey assertions now use generated `waitForExistence` helpers for `assert` and `assert_not`, eliminating immediate `.exists` reads from compiled Swift steps.

## 2026-06-09 — [Feature 057 Fix]: Requalified W15 validation docs so `mypy .` is recorded as pre-existing project-wide type debt, while touched journey compiler files pass targeted `mypy` and `pyright`.

## 2026-06-09 — [Feature 057 Fix]: Closed W14 compiler audit majors with explicit `journey_source_unreadable` failures before artifact writes, XCUITest auth/feature-flag launch assertions, centralized journey launch-environment keys, and compiler validation docs.

## 2026-06-09 — [Feature 057 Fix]: XCUITest journey compilation now injects declared auth/fixtures/mocks/feature flags before `app.launch()` and renders `open` with `XCUIApplication.open(URL)` instead of `Process`/`simctl` or post-launch launch-environment mutation.

## 2026-06-09 — [Feature 057 Fix]: Native journey compilation now fails before writing incomplete artifacts for unsupported or malformed actions, emits concrete XCUITest code for supported fill/assert_not/URL-open/screenshot flows, bounds simctl openurl with a timeout, uses named test methods, and writes newline-terminated manifests.

## 2026-06-09 — [Feature 057 Fix]: Migration 20 now force-runs `livespec journey compile --force` for downstream projects, regenerating old `journeys-v2-1` manifests during migration instead of requiring a manual compile after version 20.

## 2026-06-08 — [Feature 057 Fix]: User Journeys v2 now execute compiled native artifacts during `journey run`/`livespec test`, refresh XcodeGen projects after XCUITest compilation, and Migration 20 forces old compiled manifests to be regenerated.

## 2026-06-07 — [Feature 057 Fix]: Added Migration 19 so existing v18 projects receive `$spec-journey`, User Journeys v2 routing, and updated command guidance through `$spec-migrate`; updated root README command documentation.

## 2026-06-05 — [Feature 057 Fix]: Closed the `$spec-check` gaps for Cross-Feature User Journeys v2 — canonical 41 FR / 46 AC implementation mapping, global v2 journey skill wording, compiled-only journey gates, tighter impact detection, and Python convention fixes. Report: `features/057-cross-feature-user-journeys-v2/checks/2026-06-05.md`.

## 2026-06-04 — [Feature 057] Check: Partial alignment — tests pass, but canonical traceability is incomplete (0/41 FR, 0/46 AC mapped in `implementation.md`) and stale v1/compile-at-test journey instructions remain in command skills. Report: `features/057-cross-feature-user-journeys-v2/checks/2026-06-04.md`.

## 2026-06-04 — [Feature 057]: Implemented Cross-Feature User Journeys v2 — global journey directories, qualified cross-feature refs, history/decision governance, bootstrap/impact services, compiled-only runs, native/LLM visual checks, v1 migration, doctor findings, `$spec-journey`, and full non-integration suite verification.

---

## 2026-06-03 — [Feature 055 Fix]: Migration 18 refreshes agent-sync assets so existing v17 projects receive `spec-doctor` and the journey-aware command skill updates via `$spec-migrate`.

## 2026-06-03 — [Feature 055] Check: 100% verified (12/12 FR, 14/14 AC) — `$spec-check --fix` verified Spec Doctor Project Health with a dated zero-gap check report and no feature-scoped gaps.

## 2026-06-03 — [Feature 056] Check: 100% verified (13/13 FR, 15/15 AC) — `$spec-check --fix` verified Executable User Journeys; AC-013/AC-015 gained direct tests, plan metadata/diagrams were repaired, and a dated zero-gap check report was saved.

## 2026-06-02 — [Feature 056]: Implemented Executable User Journeys — `livespec journey validate/compile/test`, canonical YAML format reference, Playwright/XCUITest/Maestro compilers with source hashes, separated journey/manual/direct test reporting, and Spec Doctor stale/AC-FR drift checks.

## 2026-06-02 — [Feature 056]: Plan created: Executable User Journeys — 10 implementation steps, 4 diagrams, no API contracts; adds canonical YAML journey validation, native compilers, category-aware test reporting, and Spec Doctor journey drift checks.

## 2026-06-02 — [Feature 055]: Implemented Spec Doctor Project Health — `livespec doctor`, `$spec-doctor` docs, stale mapping/test/runner/hook/lifecycle/visual audits, safe cleanup planning, JSON output, strict mode, and focused tests.

## 2026-06-01 — [Feature 056]: Spec created: Executable User Journeys — canonical YAML user journeys, ahead-of-time compilation to native test frameworks, distinct functional regression reporting, and Spec Doctor stale-artifact checks.

## 2026-06-01 — [Feature 055]: Spec created: Spec Doctor Project Health — project-level doctor command for stale mappings, missing tests, runner inclusion, hooks, lifecycle drift, visual evidence, and future journey health.

## 2026-06-01 — [Feature 054]: Implemented metadata-aware migration planning and Migration 17 Penflow backfill reporting; `/spec-migrate` now documents planner-first execution, restore-point invalidation, and safe non-generation when runtime UI is unavailable.

## 2026-06-01 — [Feature 053]: Implemented goal task convention replay; every rendered goal task records required conventions and `livespec goal prove` rejects evidence missing convention usage.

## 2026-05-26 — [Feature 051 Fix]: LiveSpec now treats root `penflow/ui.pen` as the only allowed `.pen`, imports explicit Brainstorm `penflow/` sources, blocks duplicate `.pen` files, and removes `.specs/design/ui.pen` requirements from active command/docs paths.

## 2026-05-26 — [Feature 051 Check]: Single `penflow/ui.pen` contract verified against real Brainstorm project `/Users/julienm/projects/project-brainstorm/projects/orch-single-uipen-20260526T152606Z`; virgin LiveSpec import produced only `penflow/ui.pen`.

## 2026-05-23 — [Feature 052 Fix]: Visual goal proof now requires a deterministic `visual_evidence_receipt_path`; `visual-gate certify` writes verified PNG hash/diff receipts and visual commands validate receipts instead of worker-declared diffs.

## 2026-05-23 — [Feature 004 Fix]: Visual gate now enforces legacy `baseline.manifest.yml` mockup evidence, supports `mockup_path` for runtime-state screenshots, and blocks missing/stale design mockups before PASS.

## 2026-05-23 — [Feature 052 Fix]: Internal `/spec-*` subagent invocations now propagate the current LiveSpec project root/cwd and command audit rejects missing workdir guards.

## 2026-05-23 — [Feature 052 Fix]: Goal rendering now ignores documentary `/spec-*` examples/recovery hints, skips Markdown checkboxes inside `Execution Tasks`, exposes top-level `worker_may_mark_tasks_complete=false`, and adds machine Goal Lock tasks to `/spec-status` + `/spec-explain`.

## 2026-05-23 — [Feature 052 Fix]: Deterministic command goals now write `contract.json` + `state.json`, require `livespec goal prove/status`, and reject visual design-fidelity completion when mockup/baseline/runtime PNG proof is missing.

## 2026-05-21 — [Feature 052] Fix: 4/4 anchor gaps closed — FR-011/012/014/015 `@spec` annotations added (100% FR verified)

## 2026-05-21 — [Feature 052] Check: 73% FR verified (11/15), 100% AC verified (13/13), 4 FR with anchor gaps only — code complete, tests 12/12

## 2026-05-21 — [Feature 052 Fix]: Deterministic command goals now embed applicable `.conventions/index.md` domains, including code conventions by default and design conventions for UI/mockup/visual tasks.

## 2026-05-21 — [Feature 052]: Implemented: Deterministic Command Goal Contracts — `livespec goal render/verify`, canonical hashable goal payloads, expectation-backed completion gates, and shared anti-drift goal protocol.

## 2026-05-21 — [Feature 051 Bugfix]: Penflow actual-tree absence now reports `ABSENT` for from-scratch/non-UI runs and `BLOCKED` when UI runtime comparison requires `actual-ui-tree.json`; command expectations now include Penflow verdict outputs.

## 2026-05-21 — [Feature 051]: Implemented: Integrate Penflow as LiveSpec primary UI contract — root `penflow/` workspace helper + CLI, command docs for init/specify/plan/implement/test/check, Penflow contract gate workflow, and screenshot regression gates preserved.

## 2026-05-20 — [Bugfix]: Agent-sync project rule sync now links individual LiveSpec rule files before `cc-hub rule build`, so newly initialized projects receive usable `.agent-sync/rules/*.md` and provider rule outputs alongside the 20 `spec-*` skills and 4 `livespec-*` agents.

## 2026-05-20 — [Bugfix]: Downstream LiveSpec links now install under `.agent-sync.local/` instead of project `.agent-sync/`, preserving `.agent-sync/` for global/shared project assets while provider outputs still resolve through `cc-hub`.

## 2026-05-18 — [Bugfix]: Completed command-name normalization leftovers — active docs, agent-sync skills/agents, CLI help, state-file schema, and project state files now use canonical `spec-*`; state-file migration now rewrites legacy dotted `owner_command` values and validates them; agent-sync migration now ignores provider outputs and removes relative legacy command symlinks.

## 2026-05-18 — [Bugfix]: Global bootstrap now installs only `spec-init` and `spec-migrate` — `scripts/install.sh` no longer links LiveSpec rules globally; project rules remain synced by `/spec-init` through `.agent-sync` and `cc-hub`.

## 2026-05-18 — [Feature 050]: Implemented: Agent Sync Migration — moved commands, expectations, agents, and routing rules to `.agent-sync`; init/install/migration now sync through `cc-hub`; legacy `commands/`, `agents/`, and tracked `.claude/rules/livespec-*` sources removed; Migration 16 added; command-audit reports 20/20 commands at score 5.

## 2026-05-18 — [Feature 049]: Implemented: Command Naming Normalization — `/spec-*` is now canonical across registry, docs, local/bootstrap links, hooks, integrations, command-audit, verify-output, and run finalization; dotted `/spec.*` links remain as legacy aliases; Migration 15 added; full suite 1506 passed, 32 skipped.

## 2026-05-18 — [Feature 048]: Implemented: Command Validation Hardening — added canonical command registry, `livespec command-audit`, strengthened expectations guard checks, `livespec run finalize`, deterministic `status`/`play-coverage`/`conventions refresh` backends, audit-backed coherence script, Migration 14, and tests; command-audit reports 20/20 commands at score 5.

## 2026-05-18 — [Feature 049]: Spec created: Command Naming Normalization — canonical slash commands move from dotted `/spec.*` names to hyphenated `/spec-*` names after Feature 048; dotted names remain backward-compatible aliases during migration; registry, docs, hooks, verify-output, and migration tooling must agree on canonical names.

## 2026-05-18 — [Feature 048]: Spec created: Command Validation Hardening — plan created for 5/5 command validation: canonical command registry, deterministic command audit, mandatory run finalization for state-changing commands, fresh coherence checks, script-backed validation for status/play-coverage/refresh-conventions, and migration v14.

## 2026-05-17 -- [Feature 047] Implemented: Design Alignment Gate — global `ui.pen` → runtime alignment protocol, support-quality contract, manifest schema, reusable Python comparator, `livespec design-alignment compare`, `/spec-test --visual` Phase 4.5.0 integration, +8 regression tests.

## 2026-05-17 -- [Feature 046] Implemented: Visual Implementation Gate — `/spec-implement` now requires `/spec-test <feature> --auto --visual` before finalizing UI features; visual tooling failures and `--no-visual` keep status `In Progress`; `/spec-test` emits `Visual Gate Verdict: PASS | FAIL | BLOCKED`; +5 regression tests.

## 2026-05-13 -- [Feature 043] Spec created: `/spec.sync-brainstorm` — Living Bridge to Brainstorm — 5 stories, 17 AC, 18 FR (new slash-command detecting stale/orphaned/manual flows; Mode A re-pull for flows with `--apply` + per-file confirmation; Mode B inviolable for derived feature AC/FR; `--prune-orphaned` with explicit confirmation; integrates 4 new gap categories into `/spec-check`)
## 2026-05-13 -- [Feature 042] Spec created: `/spec-specify` Derives from Imported Brainstorm Flows — 3 stories, 13 AC, 13 FR (transcribes Mermaid + AC + FR from `.specs/flows/<slug>.md` produced by Feature 041; Mode B locking; classic-fallback when no flow matches)
## 2026-05-13 -- [Feature 041] Spec created: Brainstorm Flow & Screen Specs Ingestion — 3 stories, 14 AC, 12 FR (extends `spec.init` Step 3.6 to ingest `.brainstorm/specs/{flows,screens}/*.md` produced by brainstorm `specify-flows`)
## 2026-05-13 -- [Migration v13] Backfill command-expectations wiring — re-link `.claude/commands/` (drops orphan `spec.*.expectations.md` symlinks left by pre-fix `link-local.sh`, adds `/spec-verify-output`), install `last_reviewed` pre-commit hook, append `.specs/.runs/` and `.specs/.previews/` to `.gitignore`; `install-hooks.sh` accepts `<project> <livespec>` args; `/spec-init` now wires the hook automatically (features 039, 040)
## 2026-05-12 -- [Feature 040] Implemented: Rich Expectations Format & Verify Preview — Section 13 (Demo Session) mandatory across the 20 builtin expectations files, new `livespec verify-output --preview [--save]` mode that resolves placeholders from `.specs/stacks/_default.md`, `.specs/features/`, `.specs/design/screens/`, `.conventions/manifest.yaml`; +15 tests, 0 regressions (depends on feature 039)
## 2026-05-12 -- [Feature 039] Implemented: Command Expectations & /spec-verify-output — 20 builtin expectations files, RunArtifact JSON schema, verify-output CLI + slash-command, pre-commit last_reviewed hook, override resolver, 4-state outcome classifier (no-short-circuit invariant)
## 2026-05-08 -- [Feature 037] Implemented: Test Multi-Runner Integration — runner-aware Phase 4.5 dispatcher, multi-target Xcode pbxproj parsing, --visual flag documented; +32 Python tests +5 JS tests, 0 regressions
## 2026-05-08 -- [Feature 037] Plan created: Test Multi-Runner Integration — 17 implementation steps, 4 diagrams (sequence + flow + state + ER), 15+ files
## 2026-05-08 -- [Feature 037] Spec created: Test Multi-Runner Integration — 5 stories, 15 AC, 15 FR
## 2026-05-07 -- [Feature 036] Test: 92% AC covered (11/12), 906 tests passing (22 JS + 884 Python), 0 generated
## 2026-05-07 -- [Feature 036] Plan created: Multi-Surface Detection and Migration — 5 implementation steps, 2 diagrams (sequence + state), 4 files
## 2026-05-07 -- [Feature 036] Spec created: Multi-Surface Detection and Migration — 4 stories, 12 AC, 8 FR
## 2026-05-07 -- [Feature 033] In progress: Smart Test Selection — core selector module + 22 unit tests; selector logic landed, hook/CLI/migration work still pending
## 2026-05-07 -- [Feature 028] In progress: UI Runner Web (Playwright Refactor) — added web.yaml manifest and Playwright handler scaffold
## 2026-05-07 -- [Feature 026] Implemented: Conventions Propagation by Stack — 3 stories, 8 AC, 7 FR; 43 new tests pass (917 total)
## 2026-05-07 -- [Feature 025] Implemented: Mutation Testing On-Demand — 2 stories, 7 AC, 6 FR; 15 new tests pass (874 total)
## 2026-05-07 -- [Feature 019] Implemented: Driver Swift — 4 stories, 10 AC, 6 FR; 31 new tests pass (723 total)
## 2026-05-06 -- [Feature 016] Implemented: Cross-Language Test Driver Architecture — 5 stories, 15 AC, 8 FR; 35 tests pass
## 2026-05-06 -- [Feature 034] Spec created: Preflight Auto-Install & Init via /spec-preflight --fix — 5 stories, 14 AC, 11 FR
## 2026-05-06 -- [Feature 033] Spec created: Smart Test Selection — 4 stories, 12 AC, 10 FR
## 2026-05-06 -- [Feature 032] Spec created: Pre-commit / Pre-push Test Hooks — 5 stories, 13 AC, 10 FR
## 2026-05-06 -- [Feature 031] Spec created: UI Runner Android (Maestro) — 3 stories, 13 AC, 8 FR
## 2026-05-06 -- [Feature 030] Spec created: UI Runner iOS / watchOS (XCUITest) — 4 stories, 14 AC, 9 FR
## 2026-05-06 -- [Feature 029] Spec created: UI Runner Tauri — 3 stories, 12 AC, 7 FR
## 2026-05-06 -- [Feature 028] Spec created: UI Runner Web (Playwright Refactor) — 2 stories, 8 AC, 5 FR
## 2026-05-06 -- [Feature 027] Spec created: UI Runner Architecture — 4 stories, 12 AC, 8 FR
## 2026-05-06 -- [Features 013, 014, 015] Fix: implementation.md created (post-merge bookkeeping for Chantiers 4/2/3)
## 2026-05-06 -- [Feature 026] Spec created: Conventions Propagation by Stack — 3 stories, 8 AC, 7 FR
## 2026-05-06 -- [Feature 025] Spec created: Mutation Testing On-Demand — 2 stories, 7 AC, 6 FR
## 2026-05-06 -- [Feature 024] Spec created: Patch Coverage Local Computation — 2 stories, 9 AC, 6 FR
## 2026-05-06 -- [Feature 023] Spec created: Driver Custom Scaffolding & Graceful Degradation — 3 stories, 10 AC, 6 FR
## 2026-05-06 -- [Feature 022] Spec created: Driver JVM (Java + Kotlin) — 4 stories, 11 AC, 6 FR
## 2026-05-06 -- [Feature 021] Spec created: Driver Rust — 4 stories, 10 AC, 5 FR
## 2026-05-06 -- [Feature 020] Spec created: Driver Go — 4 stories, 9 AC, 5 FR
## 2026-05-06 -- [Feature 019] Spec created: Driver Swift — 4 stories, 10 AC, 6 FR
## 2026-05-06 -- [Feature 018] Spec created: Driver TypeScript/JavaScript — 4 stories, 12 AC, 6 FR
## 2026-05-06 -- [Feature 017] Spec created: Driver Python — 4 stories, 12 AC, 7 FR
## 2026-05-06 -- [Feature 016] Spec created: Cross-Language Test Driver Architecture — 5 stories, 15 AC, 8 FR

## 2026-05-04 -- Fix: Feature 010 monorepo path resolution

[Feature 010] Fix: 2/2 gaps closed — generated test templates now resolve `MOCKUP_DIR` from `import.meta.url` (parent walker for `.specs/`) instead of `process.cwd()`, and `detectRoutesDir()` consults surface-aware paths from `surfaces.yaml` before falling back to repo-root scan. Unblocks Playwright runs from sub-apps in monorepos.

---

## 2026-05-03 -- Spec: Feature 015 Global Write Locks & Atomic NNN Reservation

[Feature 015] Spec created: Global Write Locks & Atomic NNN Reservation — 5 stories, 10 AC, 10 FR. Implements file locks on shared .specs files + post-write re-read assertions + atomic NNN reservation for spec.specify to prevent race conditions and silent data corruption.

---

## 2026-05-03 -- Spec: Feature 014 Supervisor↔Subagent Return Contracts

[Feature 014] Spec created: Supervisor↔Subagent Return Contracts — 5 stories, 10 AC, 10 FR. Defines typed JSON schemas (PHASE_RESULT, SHIP_RESULT, Superpowers return) + regex-anchored parsers + active filesystem verification in Activation Contracts to harden supervisor↔subagent communication.

---

## 2026-05-03 -- Spec: Feature 013 State Model & Identity Resolution (Chantier 4)

[Feature 013] Spec created: State Model & Identity Resolution — 5 stories, 10 AC, 10 FR. Addresses the most critical defects from AUDIT.md: literal `NNN-feature-name` propagation in `/spec-feature`, log path incoherence, internal contradictions in `/spec-implement`, undefined `--resume` semantics on `Blocked`, absence of shared state-file frontmatter schema.

---

## 2026-04-18 -- Fix: Feature 011 generator template quality (3 issues)

[Feature 011] Fix: 3 template quality issues in `scripts/migrate-visual-tests.js` — (1) mockup comparison no longer creates wrong auto-baseline (now documents as reference); (2) header selector extracted from existing project tests instead of generic fallback; (3) empty-state test uses detected `mockEmpty*` fixture from `fixtures.ts` instead of hardcoded inline routes. 11/11 tests pass.

---

## 2026-04-18 -- Fix: Feature 010 generated test template upgraded

[Feature 010] Fix: Playwright API bug fixed (`toMatchSnapshot` → Playwright `toHaveScreenshot` assertions), generated E2E tests now exhaustive (4 state-based tests: full data, empty state, header, mobile), fixtures detection auto-imports `mockAuthenticatedAPIs`/`mockEmptyDashboardAPIs`, bad route inference corrected for 003/006/007.

---

## 2026-04-18 -- Fix: Feature 010 migration tool architecture corrected

[Feature 010] Fix: Migration tool now uses adaptive detection — `frontend/tests/e2e/` mode targets correct dirs (frontend/tests/e2e/, .specs/design/screens/ Pencil mockups, frontend/playwright.config.ts); legacy fallback unchanged. Legacy config cleanup preserved. 205/205 meta-tests pass.

---

## 2026-04-17 -- Fix: Feature 010 migration tool gaps closed

[Feature 010] Fix: 4/4 gaps closed — `playwright.visual.config.ts` auto-generated on `--generate`, test templates improved (route inference, page screenshots, fullpage+responsive tests), completion report printed. 11 integration tests still pass.

---

## 2026-04-17 -- Test: Feature 011 validated

[Feature 011] Test: 11 feature integration tests passing; command-layer guards reviewed in `commands/spec-migrate.md`; AC coverage report updated.

---

## 2026-04-17 -- Feature: Feature 011 implemented

[Feature 011] Implemented: Visual Migrate Integration -- sentinel output added to migrate-visual-tests.js, visual scaffolding step added to commands/spec-migrate.md (unconditional, silent, graceful degradation), 11 integration tests (level_3a), fixture project with 4 features, and baseline placeholders for generated visual scaffolds.

---

## 2026-04-17 -- Plan: Feature 011 planned (regenerated)

[Feature 011] Plan regenerated: Visual Migrate Integration — 4 implementation steps (commands/spec-migrate.md + migrate-visual-tests.js sentinel output + integration test fixture + tests/integration/test_migrate_visual.py), 1 sequence diagram, 1 state diagram, no API contracts. Visual scaffolding invoked unconditionally from command layer (including "already up to date" path), not from migrate.sh. Safe subprocess capture via set +e/set -e. Tests at tests/integration/test_migrate_visual.py for level_3a discovery.

---

## 2026-04-17 -- Spec: Feature 011 created

[Feature 011] Spec created: Visual Migrate Integration — 4 stories, 12 AC, 11 FR. Automatic visual test scaffolding during spec.migrate: silent generation of Playwright test files + baseline directories for all UI features, idempotent, with post-migration summary and graceful degradation.

---

## 2026-04-17 -- Implement: Feature 010 implemented

[Feature 010] Implemented: Visual Testing Complete — downstream Playwright scaffolding added across templates, scripts, documentation, workflow artifacts, and baseline placeholders. Python regression suite remains green at 464 passed. No Python modules modified.

---

## 2026-04-17 -- Plan: Feature 010 planned

[Feature 010] Plan created: Visual Testing Complete — 8 steps (Step 0–7), 4 TS test templates, 3 Node.js scripts, 8 Markdown guides, 1 CI workflow, 1 meta-test suite. Artifacts are framework tooling for downstream projects; no Python modules modified; meta-tests validate artifact existence only (constitution "No Visual Testing" preserved).

---

## 2026-04-17 -- Spec: Feature 010 created

[Feature 010] Spec created: Visual Testing Complete — 7 stories, 30 AC, 25 FR. Framework tooling and templates for downstream projects: mockup-driven baselines, full-page layout validation, responsive (3 viewports), cross-browser (3 engines), animation keyframes, migration tool, CI/CD visual diff PR workflow.

---

## 2026-04-17 -- Implement: Feature 005.2 implemented

[Feature 005.2] Implemented: Taxonomy Complete Expansion -- 17 new traits (22 total), 3 new transversal patterns (6 total), taxonomy v2.0.0. 478 tests passing (18 new detection tests). 100% classification on 15-component crash test. Parser required no code changes (additive schema).

---

## 2026-04-17 -- Plan: Feature 005.2 planned

[Feature 005.2] Plan created: Taxonomy Complete Expansion -- 6 implementation steps, 15 new traits + 3 transversal patterns + 15 detection tests + crash test + parser validation + docs. All 12 FR covered.

---

## 2026-04-17 -- Spec: Feature 005.2 created

[Feature 005.2] Spec created: Taxonomy Complete Expansion — 5 stories, 20 AC, 12 FR. Adds 15 new behavioral traits across 5 categories, 3 new transversal patterns, taxonomy v2.0.0 targeting >95% coverage.

---

## 2026-04-17 -- Fix: Feature 005.1 gaps closed

[Feature 005.1] Fix: 4/4 gaps closed (100% → 100% alignment) — crash test report created, AC-012/013/014/015 validated

---

## 2026-04-17 -- Test: Feature 009 spec.md corrected + full suite revalidated

[Feature 009] Test (run 2): 3/3 Python-testable ACs (100%), 446 unit tests passing, spec.md status Draft → Implemented, --regenerate-missing scan: EC-004 (0 features missing tests)

---

## 2026-04-17 -- Test: Feature 009 test validation

[Feature 009] Test: 3/3 Python-testable ACs covered (100%), 441 unit tests passing, 0 tests generated (EC-004: nothing to regenerate)

---

## 2026-04-17 -- Plan: Feature 009 planned

[Feature 009] Plan created: Visual State Baselines — 6 implementation steps, 2 diagrams (ER + state), M-size scope

---

## 2026-04-17 -- Spec: Feature 009 created

[Feature 009] Spec created: Visual State Baselines — 5 stories, 15 AC, 11 FR

---

## 2026-04-16 -- Feature: Feature 008 implemented

[Feature 008] Implemented: Feature Seed — 2 files modified (commands/spec-specify.md, spec-system.md), 7 FR, 11 AC all satisfied

---

## 2026-04-16 -- Plan: Feature 008 planned

[Feature 008] Plan created: Feature Seed — 5 implementation steps, 3 diagrams

---

## 2026-04-16 -- Spec: Feature 008 created

[Feature 008] Spec created: Feature Seed — 5 stories, 11 AC, 7 FR

---

## 2026-04-15 -- Plan: Feature 007 planned

[Feature 007] Plan created: Structured Signal Extraction — 3 implementation steps, 1 diagram

---

## 2026-04-15 -- Spec: Feature 007 regenerated (9 review findings addressed)

[Feature 007] Spec regenerated: Structured Signal Extraction — 4 stories, 11 AC, 7 FR. Addressed F-001 through F-009: added AC-009/AC-010/AC-011, fixed drawer scenario, replaced spec_specify() with detect_traits() contract tests, added Step 5.7 refactoring map.

---

## 2026-04-15 -- Spec: Feature 007 created

[Feature 007] Spec created: Structured Signal Extraction — 4 stories, 8 AC, 7 FR

---

## 2026-04-15 -- Plan: Feature 006 planned

[Feature 006] Plan created: Taxonomy Testing Infrastructure — 3 implementation steps, 2 diagrams

---

## 2026-04-15 -- Spec: Feature 006 created

[Feature 006] Spec created: Taxonomy Testing Infrastructure — 4 stories, 15 AC, 8 FR

---

## 2026-04-14 -- Check: Feature 005 checked

[Feature 005] Check: 100% verified (9/9 FR, 13/13 AC) — Healthy. All plan-review mandatory findings satisfied.

---

## 2026-04-14 -- Plan: Feature 005 plan created

[Feature 005] Plan created: UI Behavioral Testing — 5 implementation steps, 4 diagrams

---

## 2026-04-14 -- Spec: Feature 005 created

[Feature 005] Spec created: UI Behavioral Testing — 5 stories, 13 AC, 9 FR

---

## 2026-04-14 -- Feature: Feature 004 implemented

[Feature 004] Implemented: Visual Testing Governance — 4 new files created, 2 modified, 41 tests added, 406 total pass

---

## 2026-04-14 -- Plan: Feature 004 planned

[Feature 004] Plan created: Visual Testing Governance — 7 implementation steps, 4 diagrams

---

## 2026-04-14 -- Spec: Feature 004 created

[Feature 004] Spec created: Visual Testing Governance — 4 stories, 12 AC, 8 FR

---

## 2026-04-14 -- Feature: Feature 003 implemented

[Feature 003] Implemented: Visual Testing Fidelity — 6 files modified, 2 files created, 14/14 AC implemented

---

## 2026-04-14 -- Plan: Feature 003 planned

[Feature 003] Plan created: Visual Testing Fidelity — 8 implementation steps, 3 diagrams, 2 new files + 5 modified

---

## 2026-04-14 -- Spec: Feature 003 created

[Feature 003] Spec created: Visual Testing Fidelity — 6 stories, 14 AC, 10 FR

---

## 2026-04-13 -- Fix: Feature 002 anchors fixed

[Feature 002] Fix: Added 3 missing @spec anchors (FR-006, FR-007, FR-009), normalized all to single-line convention — 100% anchor alignment (9/9)

---

## 2026-04-13 -- Check: Feature 002 checked

[Feature 002] Check: 100% functional (9/9 FR, 10/10 AC), 67% anchors (6/9) — 3 missing @spec anchors

---

## 2026-04-13 -- Plan: Feature 002 planned

[Feature 002] Plan created: Layer 3 CLI Surface -- 7 implementation steps, 3 diagrams, 1 new file + 2 modified + 2 test files

---

## 2026-04-13 -- Spec: Feature 002 created

[Feature 002] Spec created: Layer 3 CLI Surface -- 4 stories, 10 AC, 9 FR

---

## 2026-04-13 -- Check: Feature 001 aligned

[Feature 001] Check: 100% verified (11/11 FR, 14/14 AC) — ✅ Healthy

---

## 2026-04-13 -- Feature: Feature 001 implemented

[Feature 001] Implemented: Auto LLM Review -- 4 new files, 3 modified, 36 new tests, 331 total pass

---

## 2026-04-13 -- Plan: Feature 001 planned

[Feature 001] Plan created: Auto LLM Review -- 6 implementation steps, 3 diagrams

---

## 2026-04-13 -- Spec: Feature 001 created

[Feature 001] Spec created: Auto LLM Review -- 4 stories, 14 AC, 11 FR

---

## 2026-04-13 -- Setup: LiveSpec initialized via spec.init --from-code

- **Type:** Setup
- **Scope:** Project-wide
- **Description:** LiveSpec initialized on existing codebase. Reverse-engineered project profile, stack (Python/Typer/Pydantic/pytest/ruff/pyright), 3 ADRs, testing strategy, and roadmap from codebase scan.
- **Author:** spec.init --from-code

---

- 2026-09-07 — [Feature078] Check ciblé : trois écarts de fermeture, aucune certification actuelle. Consulter le [rapport](features/078-requirement-evidence-integrity/checks/2026-09-07.md).

- 2026-09-07 — [Feature078] Check afc4d58b :G1certifié avant écritures,G2partiel,G3incomplet. Consulter le [rapport de clôture](features/078-requirement-evidence-integrity/checks/2026-09-07-closure.md).

- 2026-09-07 — [Feature078] Check93766262 :FR-009 et packaging inspectés; fermeture partielle. Lire le [rapport coordinateur](features/078-requirement-evidence-integrity/checks/2026-09-07-coordinator.md).

- 2026-09-07 — [Feature078] Check qualitéa0cfa9f9 :suivi clôture sans nouveau finding;full078partiel. Lire le [rapport](features/078-requirement-evidence-integrity/checks/2026-09-07-closure-followup.md).

## 2026-09-07 — [Fix] Validator CI prerequisites 079

- Read [the scoped repair report](features/079-validator-ci-prerequisites/checks/2026-09-07.md): local lint, typing, units, integration and coverage repaired; native partial acceptance and exact same-SHA remote CI remain distinct proof obligations.

## 2026-09-08 — User-authorized CI policy amendment

- Read [feature079](features/079-validator-ci-prerequisites/spec.md): deterministic GitHub validation and private pinned corpus; local model evaluation remains opt-in. Prior evidence stays historical.

### 2026-09-08 — Feature079 v5 fixture isolation

Read the [implementation checkpoint](features/079-validator-ci-prerequisites/implementation.md) for the public synthetic corpus repair and correction of the earlier full-suite parity claim. Independent post-check and delivery gates remain pending; no lifecycle promotion.

### 2026-09-08 — Feature079 v5 independent verification

Read the [post-check gap report](features/079-validator-ci-prerequisites/checks/2026-09-08-v5-postcheck.md): the bounded fixture-isolation cause is fixed, with45/45 targeted tests and16 preserved node IDs. AC-005 remains pending and AC-006 partial; feature076 and final delivery remain separate.

## 2026-10-16 — Feature 078: ignored acceptance inputs

- Bugfix: execution capture explicitly binds mapping and raw review bytes stored in ignored caches; strict verification and tamper rejection remain unchanged. RED/GREEN receipts recorded in the feature implementation map.
