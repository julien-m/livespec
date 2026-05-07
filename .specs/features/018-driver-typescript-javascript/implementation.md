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
| FR-001 | `livespec/drivers/typescript.yaml` | `@spec FR-001: TS/JS driver YAML with all 4 capabilities` | Implemented | 2026-05-07 |
| FR-002 | `validator/drivers/typescript_detector.py::detect_test_runner` | `@spec FR-002: Test runner detection (vitest > jest)` | Implemented | 2026-05-07 |
| FR-003 | `validator/drivers/stryker_parser.py` | `@spec FR-003: Stryker JSON report parser` | Implemented | 2026-05-07 |
| FR-004 | `validator/drivers/typescript_detector.py::detect_package_manager` | `@spec FR-004: Package manager detection from lockfile presence` | Implemented | 2026-05-07 |
| FR-005 | `tests/integration/test_driver_typescript.py` | `@spec FR-005: Integration tests for the TS/JS driver` | Implemented | 2026-05-07 |
| FR-006 | `tests/unit/test_typescript_detector.py`, `tests/unit/test_stryker_parser.py` | `@spec FR-006: Unit tests for runner detection and parser` | Implemented | 2026-05-07 |

## Files Created

| File | Purpose |
|---|---|
| `validator/drivers/typescript_detector.py` | Runner / package-manager / dependency detection helpers |
| `validator/drivers/stryker_parser.py` | Stryker mutation report parser (`files` and `metrics` shapes) |
| `tests/unit/test_typescript_detector.py` | 16 unit tests for runner / package-manager / dependency detection |
| `tests/unit/test_stryker_parser.py` | 11 unit tests for Stryker parsing and kill-rate computation |
| `tests/integration/test_driver_typescript.py` | 11 integration tests for manifest, registry, capability metadata, fixture detection |

## Files Modified

| File | Change |
|---|---|
| `livespec/drivers/typescript.yaml` | Replaced Feature 016 stub with full manifest (4 capabilities, npx defaults, lcov / Stryker report paths) |

## Acceptance Criteria Mapping

| AC | Test Case(s) | Status |
|---|---|---|
| AC-001 | `test_registry_loads_typescript_driver`, `test_typescript_driver_detects_package_json` | Implemented |
| AC-002 | `test_detect_test_runner_*` (5 tests), `test_runner_detection_in_fixture_vitest`, `test_runner_detection_in_fixture_jest` | Implemented |
| AC-003 | `test_coverage_capability_metadata` | Implemented |
| AC-004 | `test_coverage_capability_metadata` (threshold field) | Implemented |
| AC-005 | `test_snapshots_capability_metadata` | Implemented |
| AC-006 | Encoded in YAML (vitest / jest native diff + `-u` hint surfaced by runner output) | Implemented |
| AC-007 | Encoded in YAML (no .snap → vitest reports zero, exit 0) | Implemented |
| AC-008 | `test_has_dependency_*` (covers `fast-check` lookup), `test_properties_capability_metadata` | Implemented |
| AC-009 | `test_has_dependency_finds_in_dev_dependencies`, `test_mutation_capability_metadata` | Implemented |
| AC-010 | `test_parse_stryker_report_files_shape`, `test_parse_stryker_report_metrics_shape`, `test_compute_kill_rate_*` | Implemented |
| AC-011 | `test_typescript_driver_schema_validation` | Implemented |
| AC-012 | `test_typescript_driver_capabilities_exist`, `test_detect_package_manager_*` (5 tests) | Implemented |

## Test Results

- **New unit tests:** 27 (16 detector + 11 stryker parser) — all pass.
- **New integration tests:** 11 — all pass.
- **Full suite:** 692 passed, 28 skipped, 0 failed.
- **Lint:** `ruff check validator/drivers/` — clean.

## Notes

- Schema constraints (`DriverCapability` only allows `command`, `script`, `report_path`, `threshold`, `patch_threshold`) keep YAML minimal. Per-runner / per-package-manager logic lives in `typescript_detector.py` and is consumed by callers (e.g. `/spec.test`).
- Default command prefix is `npx`, matching FR-004 default. Detected package managers (`npm`/`yarn`/`pnpm`/`bun`) are exposed via `detect_package_manager()` for callers that want to override the YAML command.
- Stryker parser handles both report shapes (`files.<path>.mutants[]` and slim `metrics`) and treats `Timeout` as a kill (Stryker convention).
- Fast-check / Stryker absence is treated as a graceful skip via `has_dependency()` — same policy as Feature 017's syrupy/hypothesis handling.

---

*LiveSpec Feature 018 Implementation — Complete — 2026-05-07*
