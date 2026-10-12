---
type: implementation
title: Driver TypeScript/JavaScript — Built-in Test Orchestration Driver
feature: 018-driver-typescript-javascript
spec_ref: spec.md
plan_ref: plan.md
created: 2026-05-07
updated: 2026-05-07
status: Implemented
---

# Implementation — Driver TypeScript/JavaScript

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `livespec/drivers/typescript.yaml` | `@spec FR-001: TS/JS driver YAML with all 4 capabilities` | Implemented (commands use `{js_exec}`/`{js_coverage_args}`/`{js_test_args}`, 2026-10-12) | 2026-10-12 |
| FR-002 | `validator/drivers/typescript_detector.py`, `validator/drivers/placeholders.py` | `@spec FR-002: Test runner detection (vitest > jest)` | Implemented (wired into `livespec test`) | 2026-10-12 |
| FR-003 | `validator/drivers/stryker_parser.py` | `@spec FR-003: Stryker JSON report parser` | Implemented | 2026-05-07 |
| FR-004 | `validator/drivers/typescript_detector.py`, `validator/drivers/placeholders.py` | `@spec FR-004: Package manager detection` | Implemented (packageManager field, then lockfiles; wired into `livespec test`) | 2026-10-12 |
| FR-005 | `tests/integration/test_driver_typescript.py` | `@spec FR-005: Integration tests for the TS/JS driver` | Implemented | 2026-05-07 |
| FR-006 | `tests/unit/test_typescript_detector.py`, `tests/unit/test_stryker_parser.py` | `@spec FR-006: Unit tests for runner detection and parser` | Implemented | 2026-05-07 |

## Files Created

| File | Purpose |
|---|---|
| `validator/drivers/typescript_detector.py` | Runner / package-manager / dependency detection helpers |
| `validator/drivers/stryker_parser.py` | Stryker mutation report parser (`files` and `metrics` shapes) |
| `tests/unit/test_typescript_detector.py` | 16 unit tests for runner / package-manager / dependency detection |
| `tests/unit/test_stryker_parser.py` | 11 unit tests for Stryker parsing and kill-rate computation |
| `validator/drivers/preconditions.py` | Skips built-in `properties`/`mutation` with an install hint when `fast-check` / `@stryker-mutator/core` are absent (2026-10-12). |
| `tests/integration/test_driver_typescript_flow.py` | Level 3A: `livespec test` on jest+pnpm, vitest+bun (`packageManager`), project override priority, Stryker skip hint (2026-10-12). |
| `tests/integration/test_driver_typescript.py` | 2 integration tests: registry detection and schema-validated 4-capability manifest. Runner and package-manager detection live in `tests/unit/test_typescript_detector.py` (2026-10-12 cleanup removed duplicates and YAML value pins). |

## Files Modified

| File | Change |
|---|---|
| `livespec/drivers/typescript.yaml` | Replaced Feature 016 stub with full manifest (4 capabilities, npx defaults, lcov / Stryker report paths) |

## Acceptance Criteria Mapping

| AC | Test Case(s) | Status |
|---|---|---|
| AC-001 | `test_registry_loads_typescript_driver`, `test_typescript_driver_detects_package_json` | Implemented |
| AC-002 | `tests/integration/test_driver_typescript_flow.py::test_jest_project_with_pnpm_runs_jest_coverage`, `test_vitest_project_with_bun_package_manager_field_runs_vitest_coverage`, `test_detect_test_runner_*` | Implemented |
| AC-003 | `tests/integration/test_driver_typescript_flow.py` (both runners write the lcov report parsed by livespec test) | Implemented |
| AC-004 | `test_coverage_capability_metadata` (threshold field) | Implemented |
| AC-005 | `test_snapshots_capability_metadata` | Implemented |
| AC-006 | Encoded in YAML (vitest / jest native diff + `-u` hint surfaced by runner output) | Implemented |
| AC-007 | Encoded in YAML (no .snap → vitest reports zero, exit 0) | Implemented |
| AC-008 | `tests/unit/test_typescript_detector.py::test_custom_override_is_never_skipped`, `test_has_dependency_*` (runner skip via `validator/drivers/preconditions.py`) | Implemented |
| AC-009 | `tests/integration/test_driver_typescript_flow.py::test_mutation_without_stryker_emits_install_hint_and_succeeds` | Implemented |
| AC-010 | `test_parse_stryker_report_files_shape`, `test_parse_stryker_report_metrics_shape`, `test_compute_kill_rate_*` | Implemented |
| AC-011 | `test_typescript_driver_schema_validation` | Implemented |
| AC-012 | `tests/integration/test_driver_typescript_flow.py` (pnpm, bun, npx; override keeps priority), `test_package_manager_field_wins_over_lockfile`, `test_detect_package_manager_*` | Implemented |

## Test Results

- **New unit tests:** 27 (16 detector + 11 stryker parser) — all pass.
- **New integration tests:** 11 — all pass.
- **Repository lint audit:** `ruff check .` passes.
- **Repository type audit:** `mypy .` currently fails on pre-existing issues outside the Feature 018 file set.

## Notes

- Schema constraints keep YAML minimal: whole-token placeholders (`{js_exec}`, `{js_coverage_args}`, `{js_test_args}`) are expanded by `validator/drivers/placeholders.py` from `typescript_detector.py` (2026-10-12). A `.specs/drivers/typescript.yaml` override replaces the manifest and runs verbatim.
- Exec prefix: `npx` (npm or nothing declared), `pnpm exec`, `yarn`, `bunx`; the `packageManager` field wins over lockfiles. `livespec test-config` no longer writes `vitest.config.ts` into jest projects (it would flip runner detection).
- Stryker parser handles both report shapes (`files.<path>.mutants[]` and slim `metrics`) and treats `Timeout` as a kill (Stryker convention).
- Fast-check / Stryker absence is a graceful skip enforced by `run_capability` through `preconditions.py` (built-in manifest only).

---

*LiveSpec Feature 018 Implementation — Complete — 2026-05-07*
