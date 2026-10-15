---
created: 2026-10-11
feature: 083-pinned-runtime-isolation
title: 'Implementation Map: Pinned Runtime Isolation'
type: implementation
updated: 2026-10-15
---

# Implementation — Pinned Runtime Isolation

> Read [spec](spec.md) and [plan](plan.md). Non-UI feature (CLI + files); no visual baselines.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Committed snapshot install](spec.md#fr-001) | `validator/runtime/snapshot.py`, `validator/runtime/git_tree.py`, `validator/runtime/evidence.py`, `validator/runtime/errors.py`, `validator/cli_commands/runtime_cmd.py` | `@spec FR-001: Committed snapshot build — .specs/features/083-pinned-runtime-isolation/spec.md#fr-001` | ✅ Implemented | 2026-10-15 |
| [FR-002: Manifest and atomic read-only snapshot](spec.md#fr-002) | `validator/runtime/models.py`, `validator/runtime/manifest.py`, `validator/runtime/snapshot.py` | `@spec FR-002: Manifest model, Content digest — .specs/features/083-pinned-runtime-isolation/spec.md#fr-002` | ✅ Implemented | 2026-10-11 |
| [FR-003: Reuse, shim and activation](spec.md#fr-003) | `validator/runtime/snapshot.py`, `validator/runtime/shim.py` | `@spec FR-003: Reuse and activation, Shim on install — .specs/features/083-pinned-runtime-isolation/spec.md#fr-003` | ✅ Implemented | 2026-10-15 |
| [FR-004: Shim resolution and exit 3](spec.md#fr-004) | `validator/runtime/shim_core.py`, `validator/runtime/home.py` | `@spec FR-004: Shim resolution and exit 3 — .specs/features/083-pinned-runtime-isolation/spec.md#fr-004` | ✅ Implemented | 2026-10-11 |
| [FR-005: Pin](spec.md#fr-005) | `validator/runtime/project.py`, `validator/cli_commands/runtime_cmd.py` | `@spec FR-005: Pin writes — .specs/features/083-pinned-runtime-isolation/spec.md#fr-005` | ✅ Implemented | 2026-10-11 |
| [FR-006: Link retargeting](spec.md#fr-006) | `validator/runtime/links.py` | `@spec FR-006: Link retargeting — .specs/features/083-pinned-runtime-isolation/spec.md#fr-006` | ✅ Implemented | 2026-10-11 |
| [FR-007: Upgrade](spec.md#fr-007) | `validator/runtime/project.py`, `validator/cli_commands/runtime_cmd.py` | `@spec FR-007: Upgrade — .specs/features/083-pinned-runtime-isolation/spec.md#fr-007` | ✅ Implemented | 2026-10-11 |
| [FR-008: Dev lock](spec.md#fr-008) | `validator/runtime/project.py`, `validator/cli_commands/runtime_cmd.py` | `@spec FR-008: Dev lock — .specs/features/083-pinned-runtime-isolation/spec.md#fr-008` | ✅ Implemented | 2026-10-11 |
| [FR-009: Migration guard bypass](spec.md#fr-009) | `validator/version_guard.py`, `validator/cli_commands/runtime_cmd.py`, `validator/cli_commands/__init__.py` | `@spec FR-009: Guard bypass, Runtime group registration — .specs/features/083-pinned-runtime-isolation/spec.md#fr-009` | ✅ Implemented | 2026-10-11 |
| [FR-010: Boundary rule and references](spec.md#fr-010) | [`system/tool-project-boundary.md`](../../../system/tool-project-boundary.md), `system/spec-system.md`, `.specs/spec-system.md`, spec-feature/fix/implement/ship `SKILL.md` | `@spec FR-010: Tool/project boundary rule — .specs/features/083-pinned-runtime-isolation/spec.md#fr-010` | ✅ Implemented | 2026-10-11 |
| [FR-011: Defect report](spec.md#fr-011) | `validator/runtime/defects.py`, `validator/pipeline.py`, `validator/cli_commands/runtime_cmd.py` | `@spec FR-011: Report and blocked phase — .specs/features/083-pinned-runtime-isolation/spec.md#fr-011` | ✅ Implemented | 2026-10-11 |
| [FR-012: Runtime scanner, status and doctor](spec.md#fr-012) | `validator/runtime/inspection.py`, `validator/doctor/runtime_scan.py`, `validator/doctor/__init__.py`, `validator/cli_commands/runtime_cmd.py` | `@spec FR-012: Runtime scanner and doctor — .specs/features/083-pinned-runtime-isolation/spec.md#fr-012` | ✅ Implemented | 2026-10-11 |
| [FR-013: Docs and migration](spec.md#fr-013) | `README.md`, `docs/cli-reference.md` | `@spec FR-013: Docs and migration — .specs/features/083-pinned-runtime-isolation/spec.md#fr-013` | ✅ Implemented | 2026-10-12 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_runtime_snapshot.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-002 | `tests/test_runtime_snapshot.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-003 | `tests/test_runtime_snapshot.py` (incl. `test_staging_named_symlink_is_unlinked_without_following`) | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-004 | `tests/test_runtime_shim.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-005 | `tests/test_runtime_shim.py` (incl. `test_current_must_be_a_verified_snapshot`, `test_looping_current_symlink_exits_3_without_traceback`, `test_exit_3_recovery_uses_the_checkout_venv`) | ✅ Pass 2026-10-12 (spec-test re-certification); D-11 recovery regression added 2026-10-15 (spec-fix) |
| AC-006 | `tests/test_runtime_project.py` (incl. `test_pin_replaces_lock_pinned_to_another_runtime`) | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-007 | `tests/test_runtime_project.py` (incl. `test_broken_links_need_trusted_provenance`), `tests/test_runtime_cli.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-008 | `tests/test_runtime_project.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-009 | `tests/test_runtime_project.py`, `tests/test_runtime_cli.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-010 | `tests/test_runtime_cli.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-011 | `tests/test_runtime_project.py` (incl. generated `test_dev_from_pinned_moves_path_and_links_to_checkout`), `tests/test_runtime_cli.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-012 | `tests/test_runtime_docs.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-013 | `tests/test_runtime_defects.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-014 | `tests/test_runtime_defects.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-015 | `tests/test_runtime_inspection.py`, `tests/test_runtime_shim.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-016 | `tests/test_runtime_inspection.py`, `tests/test_runtime_shim.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-017 | `tests/test_runtime_inspection.py` (incl. `test_status_json_in_dev_mode`, `test_pinned_lock_without_livespec_path_warns`) | ✅ Pass 2026-10-12 (spec-test re-certification) |
| AC-018 | `tests/test_runtime_docs.py` (isolated HOME/TMPDIR/git config, written-path containment, fixture-tree hashes), `tests/runtime_support.py` | ✅ Pass 2026-10-12 (spec-test re-certification) |

Shared fixtures: `tests/runtime_support.py` (temporary git sources with a real-code copy, consumer fixtures, independent digest, write-bit restoration, tree hashes).

## Files Created/Modified

| File | Change |
|---|---|
| `validator/runtime/__init__.py` | New package docstring |
| `validator/runtime/models.py` | Manifest, results, findings, constants |
| `validator/runtime/home.py` | Home (`--home` > `$LIVESPEC_HOME` > `~/.livespec`), project/LiveSpec roots, executing root |
| `validator/runtime/git_tree.py` | Read-only git queries (`rev-parse`, `status --no-optional-locks`, `ls-tree`, `cat-file --batch`) |
| `validator/runtime/manifest.py` | Content digest, manifest I/O, snapshot verification |
| `validator/runtime/snapshot.py` | Install: validate, stage, seal read-only, same-parent rename, stale staging cleanup, activation |
| `validator/runtime/shim_core.py` | Stdlib-only shim logic and strict lock parser (embedded verbatim) |
| `validator/runtime/shim.py` | Shim rendering and atomic write (D-06) |
| `validator/runtime/links.py` | LiveSpec-owned link discovery and retargeting |
| `validator/runtime/project.py` | `pin`, `upgrade`, `dev` |
| `validator/runtime/inspection.py` | Shared drift scanner and status report |
| `validator/runtime/defects.py` | Defect report and blocked phase |
| `validator/cli_commands/runtime_cmd.py` | Thin `livespec runtime` command group |
| `validator/doctor/runtime_scan.py` | Doctor adapter (category `runtime`) and package-level `run_doctor` wrapper (scanner report + runtime findings, status recomputed with the scanner rules) |
| `validator/doctor/__init__.py` | Exports the wrapper as `run_doctor` (used by `livespec doctor`) |
| `validator/pipeline.py` | Public `write_phase_update` alias, `PHASE_UPDATE_ERRORS`, `report` keyword |
| `validator/cli_commands/__init__.py` | Registers the `runtime` group through `register_unified_commands` |
| `validator/version_guard.py` | `GUARD_EXEMPT_GROUPS` (`runtime`): `enforce_project_migrated` returns before enforcing |
| `validator/runtime/errors.py` | `LiveSpecRuntimeError` family |
| `system/tool-project-boundary.md` | Boundary rule (four rules, D-03 resume) |
| `system/spec-system.md`, `.specs/spec-system.md` | One boundary reference line each |
| `.agent-sync/skills/{spec-feature,spec-fix,spec-implement,spec-ship}/SKILL.md` | One boundary reference line before `## Internal Command Invocations` |
| `.agent-sync/skills/{spec-feature,spec-fix,spec-implement,spec-ship}/expectations.md` | `last_reviewed: 2026-10-11` |
| `README.md`, `docs/cli-reference.md` | Runtime install/pin/upgrade/dev/status/defect, PATH, fresh machine, deletion, Handy migration |
| `tests/runtime_support.py`, `tests/test_runtime_snapshot.py`, `tests/test_runtime_shim.py`, `tests/test_runtime_project.py`, `tests/test_runtime_cli.py`, `tests/test_runtime_inspection.py`, `tests/test_runtime_defects.py`, `tests/test_runtime_docs.py` | Feature tests (temporary directories only) |

## Notes

- Git input for `cat-file --batch` and shim test stdin are fed from temporary files: feeding a pipe while draining a large stdout through `communicate()` stalled on this macOS host.
- `livespec runtime status` reports mode `invalid` (lock `null`) when `.specs/livespec.lock` cannot be parsed; valid locks report `pinned`, `dev` or `unpinned`.
- Real installation into `~/.livespec`, the Handy migration and cc-hub steps remain operator actions; tests run the documented migration only on temporary copies.
- The legacy CLI entry module, the shared exceptions module and the doctor scanner are left unchanged: the runtime group registers through `register_unified_commands`, the guard bypass lives in the version guard, runtime errors live in the runtime package and doctor integration wraps the scanner.
- Install reuse, pinned status and the concurrent-install path verify that the snapshot manifest records the expected commit (install ref or lock), not only the runtime id.

## Execution Evidence

- Acceptance mapping: `.specs/features/083-pinned-runtime-isolation/run/acceptance/mapping.json` (157 single-assertion bindings, all 18 AC; mapping-review budget 200000 characters, its own schema-supported budget).
- Independent mapping review (claude-opus-5-5, 2 batches + synthesis): receipt `.specs/features/083-pinned-runtime-isolation/run/acceptance/mapping-review-receipt.json`, complete and ready, 18/18 covered. Non-blocking reviewer warnings kept for `/spec-test`: one AC-003 binding labelled "current unchanged after refusal" cites the pre-refusal check (the post-refusal assertion in the same test is unbound); manifest runtime_id≠lock is not exercised at shim level; pin replacing another pinned lock and `status` JSON in dev mode are not asserted.
- Runner-owned execution receipt: `.specs/.execution/d513ca6e4a0744b8a6a62ab564770a00/receipt.json` (61 tests passed, 18 AC certified, no gaps).
- `/spec-test` 2026-10-11: closed the four reviewer gaps (AC-003 rebind to line 172; new AC-005, AC-006, AC-017 tests). Mapping now 168 bindings; fresh mapping review receipt complete/ready 18/18; runner-owned execution receipt captured after these feature files were finalized (64 passed, 18 AC certified, no gaps; path recorded in the spec-test goal archive under `.specs/.runs/`, since editing this directory after capture would stale it). Report: [checks/2026-10-11-test.md](checks/2026-10-11-test.md).
- `/spec-test` 2026-10-12 (re-certification after the audit passes):
  - Mapping re-bound to HEAD 83a48c5: 95 of 168 spans moved; the AC-018 protected-path binding was re-pointed to the isolated fixture check.
  - Added 8 bindings for audit-pass tests.
  - The fresh independent mapping review (claude-opus-5-5, foreground) found the AC-011 path/link assertions non-discriminating. A test was generated for it (`test_dev_from_pinned_moves_path_and_links_to_checkout`), and the two old bindings were replaced.
  - Mapping: 177 bindings. Review receipt complete and ready, 18/18 covered.
  - The runner-owned execution receipt was captured after these feature files were finalized: 103 passed, 18 AC certified, no gaps. Its path is recorded in the spec-test goal archive under `.specs/.runs/`.
  - Report: [checks/2026-10-12-test.md](checks/2026-10-12-test.md).

## Audit Corrections (2026-10-11)

| Finding | Fix | Test |
|---|---|---|
| #7 defect `--feature`/`--phase` unvalidated (blocker) | `validate_target` in `validator/runtime/defects.py` (slug only, resolves directly under `.specs/features`, known phase) runs before any write; CLI maps `RuntimeDefectInputError` (`validator/runtime/errors.py`) to exit 2 | `tests/test_runtime_defects.py::test_unsafe_feature_is_refused_before_any_write`, `test_unknown_phase_is_refused_before_any_write` |
| #13 stale-staging symlink followed (blocker) | `remove_stale_staging` unlinks staging-named symlinks without following; `remove_tree` refuses symlinks and paths not directly under `<home>/versions` (`validator/runtime/snapshot.py`) | `tests/test_runtime_snapshot.py::test_staging_named_symlink_is_unlinked_without_following` |
| #8 untrusted Markdown in defect reports | one-line title and identity values; command and error in dynamically sized fences | `tests/test_runtime_defects.py::test_report_renders_untrusted_text_safely` |
| #9 lax manifest schema | strict `manifest_from_dict` (`validator/runtime/models.py`): int schema 1, id/commit formats and relation, `sha256:`+64 hex, UTC ISO-8601, absolute source | `tests/test_runtime_snapshot.py::test_manifest_schema_is_strict` |
| #10 writable snapshot accepted | `verify_snapshot` rejects symlinked snapshot dirs and any write bit (`writable_entries`, `validator/runtime/manifest.py`) | `tests/test_runtime_snapshot.py::test_writable_snapshot_is_refused` |
| #11 broken foreign links retargeted | broken links owned only when their root equals the recorded `.specs/.livespec-path` (`validator/runtime/links.py`) | `tests/test_runtime_project.py::test_broken_links_need_trusted_provenance` |
| #12 non-atomic selection | `_select` holds `.specs/.LOCK` (`validator.locks.acquire_lock`) and restores lock/path/links on failure (`validator/runtime/project.py`) | `tests/test_runtime_project.py::test_selection_failure_restores_previous_state` |
| #14 pinned lock without `.livespec-path` silent | WARNING `runtime_reference_missing` with `livespec runtime pin --runtime <id>` (`validator/runtime/inspection.py`) | `tests/test_runtime_inspection.py::test_pinned_lock_without_livespec_path_warns` |
| #15 shim accepted any LiveSpec-shaped `current` | `_current_snapshot` requires a snapshot under `<home>/versions` whose single manifest identity matches the directory (`validator/runtime/shim_core.py`), also on the runtime-subcommand fallback | `tests/test_runtime_shim.py::test_current_must_be_a_verified_snapshot` |
| #6 docs test touched real paths | `tests/test_runtime_docs.py` runs with HOME/TMPDIR/GIT_CONFIG_GLOBAL under `tmp_path`, asserts every selected path stays in the fixture and fixture sources keep their content hashes | `tests/test_runtime_docs.py::test_documented_migration_runs_on_consumer_fixture` |
| #3/#4/#5 docs | fresh machine starts with `cd <livespec repo> && python3 -m validator.cli runtime install …` (README and `docs/cli-reference.md`); stale "All six commands" sentence replaced | `tests/test_runtime_docs.py::test_docs_cover_every_runtime_command` |
| #2 progress resume line | updated in `progress.md` | — |
| #1 pipeline timestamps | no change (UTC by design) | — |

### Second audit pass (2026-10-12, applied by the supervisor after the implementing agent was interrupted)

| Finding | Fix | Test |
|---|---|---|
| R2#1 symlinked `.specs/features` redirect (blocker) | `_refuse_redirected` in `validator/runtime/defects.py` refuses symlinked or escaping `.specs`, `.specs/tool-defects`, `.specs/features` and feature components before any write | `tests/test_runtime_defects.py::test_symlinked_features_dir_is_refused_before_any_write` |
| R2#2 HTML in single-line values | `_one_line` escapes `&`, `<`, `>` after whitespace collapse (title, feature, phase, identity) | `tests/test_runtime_defects.py::test_title_html_cannot_hide_report_content` |
| R2#3 bytecode in docs fixture | `PYTHONDONTWRITEBYTECODE=1` and fixture-local `PYTHONPYCACHEPREFIX` in `tests/test_runtime_docs.py` | `tests/test_runtime_docs.py::test_documented_migration_runs_on_consumer_fixture` |
| R2#4 mixed generation for readers (blocker) | no reader locking (shim/status key on the lock only); `_publish` in `validator/runtime/project.py` writes `.livespec-path` and links first and the lock last | `tests/test_runtime_project.py::test_lock_is_published_last_and_rollback_failure_is_reported` |
| R2#5 rollback failure reported as success | `_publish` raises `RuntimeSelectionError("selection failed; rollback incomplete: …")` chaining the original error | same test |
| R2#6 incomplete `current` manifest (blocker) | `_manifest_identity_ok` in `validator/runtime/shim_core.py` checks exact key set, int schema 1 and digest format; digest is still not recomputed (FR-004) | `tests/test_runtime_shim.py::test_current_with_incomplete_manifest_exits_3` |
| R2#7 looping `current` traceback | `_current_snapshot` resolves strictly inside `try` and maps `OSError`/`RuntimeError` to the install recovery error | `tests/test_runtime_shim.py::test_looping_current_symlink_exits_3_without_traceback` |
| R2#8 optional deletion container | `remove_tree(root, container)` requires the container (`validator/runtime/snapshot.py`) | `tests/test_runtime_snapshot.py::test_remove_tree_requires_a_real_direct_child` |
| R3#3 untrusted recorded root | `recorded_root` in `validator/runtime/links.py` trusts only an absolute, decodable `.livespec-path` | `tests/test_runtime_project.py::test_untrusted_recorded_root_is_ignored` |
| R3#4 `current` manifest source/created_at | `_manifest_identity_ok` requires an absolute `source` and a UTC ISO-8601 `created_at` (`validator/runtime/shim_core.py`) | `tests/test_runtime_shim.py::test_current_with_malformed_source_or_timestamp_exits_3` |
| R3#5 non-directory deletion | `remove_tree` refuses non-directories (`validator/runtime/snapshot.py`) | `tests/test_runtime_snapshot.py::test_remove_tree_refuses_a_regular_file_child` |
| R3#1/#2 registry and resume line | README activity row and `progress.md` resume point updated | — |
| R2#9-#11 Markdown link style in feature docs | no change: implementation maps use code spans, parsed by the feature-scope resolver | — |

Execution certification is re-run after these corrections by `/spec-test`.

## 2026-10-12 — Executable migration command (spec-fix)

The documented first install runs the checkout's own venv (`.venv/bin/python -m validator.cli runtime install …`, created once by `uv sync`). A bare `python3` lacks LiveSpec's dependencies and would also become the shim interpreter. [test_runtime_docs.py](../../../tests/test_runtime_docs.py) runs the exact documented block with `PATH` limited to git and `/usr/bin:/bin`, without venv activation; the fixture checkout venv is an `exec` wrapper. Restoring the `python3` wording makes it fail with `ModuleNotFoundError: typer`.

## 2026-10-13 — Conventions test evidence in snapshots (spec-fix)

FR-001 / AC-001: `ships_in_snapshot` in `validator/runtime/models.py` keeps `.specs/` and `tests/` out of a snapshot, except `SNAPSHOT_TEST_EVIDENCE`. That set is the AST fixtures and the three deterministic test files the bundled catalogs cite, which `conventions verify` reads from the runtime root. `validator/runtime/git_tree.py` applies it. [test_runtime_snapshot_evidence.py](../../../tests/test_runtime_snapshot_evidence.py) installs a snapshot and checks that the evidence ships and that other `tests/` files do not. Its drift guard fails when a catalog cites a `tests/` path the policy does not ship.

## 2026-10-15 — Evidence rules of the installed commit (spec-fix)

FR-001 / FR-003: the code running `livespec runtime install` may predate the commit it installs. `21-71f1e0d1b3d3` was built by `21-3c1e6a776500`, whose policy dropped every `tests/` path, so it shipped without the fixtures its own catalogs cite and later installs reused it.

- [evidence.py](../../../validator/runtime/evidence.py) reads the target rules without running target code: the `SNAPSHOT_TEST_EVIDENCE` literal of the commit's `validator/runtime/models.py` (parsed with `ast`) and the `fixtures`/`deterministic_test_evidence` paths of its bundled `rule_catalog/*.yaml`.
- [git_tree.py](../../../validator/runtime/git_tree.py) `list_snapshot_entries` ships the running policy plus those target entries (`ships_in_snapshot(path, target_evidence)`).
- [snapshot.py](../../../validator/runtime/snapshot.py) checks the staging tree before sealing (a cited file absent from the commit is refused with `RuntimeSourceError`) and checks a reused snapshot (`RuntimeSnapshotError` listing the missing paths, with the commands to delete and rebuild it).
- [test_runtime_snapshot_evidence.py](../../../tests/test_runtime_snapshot_evidence.py) simulates an older builder (empty running policy, then no target reading and no check) and covers the three cases; a guard checks that this repository's own policy and catalogs parse back exactly. [runtime_support.py](../../../tests/runtime_support.py) now copies that evidence into the real-code source, which the new check otherwise refuses.

