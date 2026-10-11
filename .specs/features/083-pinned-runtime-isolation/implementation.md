# Implementation — Pinned Runtime Isolation

> Read [spec](spec.md) and [plan](plan.md). Non-UI feature (CLI + files); no visual baselines.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Committed snapshot install](spec.md#fr-001) | `validator/runtime/snapshot.py`, `validator/runtime/git_tree.py`, `validator/runtime/errors.py`, `validator/cli_commands/runtime_cmd.py` | `@spec FR-001: Committed snapshot build — .specs/features/083-pinned-runtime-isolation/spec.md#fr-001` | ✅ Implemented | 2026-10-11 |
| [FR-002: Manifest and atomic read-only snapshot](spec.md#fr-002) | `validator/runtime/models.py`, `validator/runtime/manifest.py`, `validator/runtime/snapshot.py` | `@spec FR-002: Manifest model, Content digest — .specs/features/083-pinned-runtime-isolation/spec.md#fr-002` | ✅ Implemented | 2026-10-11 |
| [FR-003: Reuse, shim and activation](spec.md#fr-003) | `validator/runtime/snapshot.py`, `validator/runtime/shim.py` | `@spec FR-003: Reuse and activation, Shim on install — .specs/features/083-pinned-runtime-isolation/spec.md#fr-003` | ✅ Implemented | 2026-10-11 |
| [FR-004: Shim resolution and exit 3](spec.md#fr-004) | `validator/runtime/shim_core.py`, `validator/runtime/home.py` | `@spec FR-004: Shim resolution and exit 3 — .specs/features/083-pinned-runtime-isolation/spec.md#fr-004` | ✅ Implemented | 2026-10-11 |
| [FR-005: Pin](spec.md#fr-005) | `validator/runtime/project.py`, `validator/cli_commands/runtime_cmd.py` | `@spec FR-005: Pin writes — .specs/features/083-pinned-runtime-isolation/spec.md#fr-005` | ✅ Implemented | 2026-10-11 |
| [FR-006: Link retargeting](spec.md#fr-006) | `validator/runtime/links.py` | `@spec FR-006: Link retargeting — .specs/features/083-pinned-runtime-isolation/spec.md#fr-006` | ✅ Implemented | 2026-10-11 |
| [FR-007: Upgrade](spec.md#fr-007) | `validator/runtime/project.py`, `validator/cli_commands/runtime_cmd.py` | `@spec FR-007: Upgrade — .specs/features/083-pinned-runtime-isolation/spec.md#fr-007` | ✅ Implemented | 2026-10-11 |
| [FR-008: Dev lock](spec.md#fr-008) | `validator/runtime/project.py`, `validator/cli_commands/runtime_cmd.py` | `@spec FR-008: Dev lock — .specs/features/083-pinned-runtime-isolation/spec.md#fr-008` | ✅ Implemented | 2026-10-11 |
| [FR-009: Migration guard bypass](spec.md#fr-009) | `validator/version_guard.py`, `validator/cli_commands/runtime_cmd.py`, `validator/cli_commands/__init__.py` | `@spec FR-009: Guard bypass, Runtime group registration — .specs/features/083-pinned-runtime-isolation/spec.md#fr-009` | ✅ Implemented | 2026-10-11 |
| [FR-010: Boundary rule and references](spec.md#fr-010) | [`system/tool-project-boundary.md`](../../../system/tool-project-boundary.md), `system/spec-system.md`, `.specs/spec-system.md`, spec-feature/fix/implement/ship `SKILL.md` | `@spec FR-010: Tool/project boundary rule — .specs/features/083-pinned-runtime-isolation/spec.md#fr-010` | ✅ Implemented | 2026-10-11 |
| [FR-011: Defect report](spec.md#fr-011) | `validator/runtime/defects.py`, `validator/pipeline.py`, `validator/cli_commands/runtime_cmd.py` | `@spec FR-011: Report and blocked phase — .specs/features/083-pinned-runtime-isolation/spec.md#fr-011` | ✅ Implemented | 2026-10-11 |
| [FR-012: Runtime scanner, status and doctor](spec.md#fr-012) | `validator/runtime/inspection.py`, `validator/doctor/runtime_scan.py`, `validator/doctor/__init__.py`, `validator/cli_commands/runtime_cmd.py` | `@spec FR-012: Runtime scanner and doctor — .specs/features/083-pinned-runtime-isolation/spec.md#fr-012` | ✅ Implemented | 2026-10-11 |
| [FR-013: Docs and migration](spec.md#fr-013) | `README.md`, `docs/cli-reference.md` | `@spec FR-013: Docs and migration — .specs/features/083-pinned-runtime-isolation/spec.md#fr-013` | ✅ Implemented | 2026-10-11 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_runtime_snapshot.py` | ✅ Pass 2026-10-11 |
| AC-002 | `tests/test_runtime_snapshot.py` | ✅ Pass 2026-10-11 |
| AC-003 | `tests/test_runtime_snapshot.py` (post-refusal binding line 172) | ✅ Pass 2026-10-11 (spec-test) |
| AC-004 | `tests/test_runtime_shim.py` | ✅ Pass 2026-10-11 |
| AC-005 | `tests/test_runtime_shim.py` (incl. `test_manifest_runtime_id_differing_from_lock_exits_3`) | ✅ Pass 2026-10-11 (spec-test) |
| AC-006 | `tests/test_runtime_project.py` (incl. `test_pin_replaces_lock_pinned_to_another_runtime`) | ✅ Pass 2026-10-11 (spec-test) |
| AC-007 | `tests/test_runtime_project.py` | ✅ Pass 2026-10-11 |
| AC-008 | `tests/test_runtime_project.py` | ✅ Pass 2026-10-11 |
| AC-009 | `tests/test_runtime_project.py` | ✅ Pass 2026-10-11 |
| AC-010 | `tests/test_runtime_cli.py` | ✅ Pass 2026-10-11 |
| AC-011 | `tests/test_runtime_project.py` | ✅ Pass 2026-10-11 |
| AC-012 | `tests/test_runtime_docs.py` | ✅ Pass 2026-10-11 |
| AC-013 | `tests/test_runtime_defects.py` | ✅ Pass 2026-10-11 |
| AC-014 | `tests/test_runtime_defects.py` | ✅ Pass 2026-10-11 |
| AC-015 | `tests/test_runtime_inspection.py`, `tests/test_runtime_shim.py` | ✅ Pass 2026-10-11 |
| AC-016 | `tests/test_runtime_inspection.py`, `tests/test_runtime_shim.py` | ✅ Pass 2026-10-11 |
| AC-017 | `tests/test_runtime_inspection.py` (incl. `test_status_json_in_dev_mode`) | ✅ Pass 2026-10-11 (spec-test) |
| AC-018 | `tests/test_runtime_docs.py`, `tests/runtime_support.py` | ✅ Pass 2026-10-11 |

Shared fixtures: `tests/runtime_support.py` (temporary git sources with a real-code copy, consumer fixtures, independent digest, write-bit restoration, protected-set fingerprint).

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
