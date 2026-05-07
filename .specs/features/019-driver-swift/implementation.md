---
type: implementation
title: Driver Swift — Built-in Test Orchestration Driver
feature: 019-driver-swift
spec_ref: spec.md
plan_ref: plan.md
created: 2026-05-07
updated: 2026-05-07
status: Implemented
---

# Implementation — Driver Swift

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `livespec/drivers/swift.yaml` | `@spec FR-001: Swift driver YAML with all 4 capabilities` | Implemented | 2026-05-07 |
| FR-002 | `livespec/drivers/scripts/swift-coverage-gate.sh` | `@spec FR-002: Swift coverage gate escape-hatch script` | Implemented | 2026-05-07 |
| FR-003 | `validator/drivers/swift_detector.py::parse_package_dependencies` | `@spec FR-003: Package.swift dependency parser` | Implemented | 2026-05-07 |
| FR-004 | `validator/drivers/swift_detector.py::is_xcode_only_project` | `@spec FR-004: Xcode project detection fallback` | Implemented | 2026-05-07 |
| FR-005 | `tests/integration/test_driver_swift.py` | `@spec FR-005: Integration tests for the Swift driver` | Implemented | 2026-05-07 |
| FR-006 | `tests/unit/test_swift_detector.py`, `tests/unit/test_swift_coverage_gate.py` | `@spec FR-006: Unit tests for detector and gate script` | Implemented | 2026-05-07 |

## Files Created

| File | Purpose |
|---|---|
| `livespec/drivers/scripts/swift-coverage-gate.sh` | Escape-hatch shell script that runs `swift test --enable-code-coverage`, exports lcov via `xcrun llvm-cov` (or `llvm-cov` on Linux), parses DA: lines, and gates on threshold. |
| `validator/drivers/swift_detector.py` | Pure-Python `Package.swift` parser + Xcode-only project fallback. |
| `tests/unit/test_swift_detector.py` | 11 unit tests for dependency parsing, case-insensitive lookup, and Xcode fallback. |
| `tests/unit/test_swift_coverage_gate.py` | 9 bash-script unit tests covering threshold pass/fail, default threshold, Xcode-only skip, no Swift project, and missing/empty lcov. |
| `tests/integration/test_driver_swift.py` | 11 integration tests covering manifest schema, registry detection, capability metadata, gate-script presence, Xcode-only non-match, and dependency detection on a SwiftPM fixture. |

## Files Modified

| File | Change |
|---|---|
| `livespec/drivers/swift.yaml` | Replaced Feature 016 stub with full 4-capability manifest (coverage uses `script:` escape hatch, snapshots/properties run `swift test`, mutation runs `muter run`). |

## Acceptance Criteria Mapping

| AC | Test Case(s) | Status |
|---|---|---|
| AC-001 | `test_registry_loads_swift_driver`, `test_swift_driver_detects_package_swift` | Implemented |
| AC-002 | `test_coverage_capability_uses_script_escape_hatch`, gate script `swift test --enable-code-coverage` invocation | Implemented |
| AC-003 | `test_gate_passes_when_above_threshold`, `test_gate_fails_when_below_threshold`, `test_gate_default_threshold_is_75` | Implemented |
| AC-004 | `test_gate_xcode_only_project_skips_with_hint`, `test_xcode_only_project_does_not_match_swift_driver`, `test_is_xcode_only_project_*` | Implemented |
| AC-005 | `test_dependency_detection_in_fixture_swiftpm`, `test_has_swift_dependency_case_insensitive`, `test_snapshots_capability_metadata` | Implemented |
| AC-006 | `test_dependency_detection_in_fixture_swiftpm`, `test_properties_capability_metadata` | Implemented |
| AC-007 | `test_mutation_capability_metadata` (muter command surfaces install hint via runner) | Implemented |
| AC-008 | `test_coverage_capability_uses_script_escape_hatch`, `test_coverage_gate_script_is_shipped_and_executable` | Implemented |
| AC-009 | `test_swift_driver_schema_validation`, `test_swift_driver_capabilities_exist` | Implemented |
| AC-010 | `test_parse_package_dependencies_*`, `test_dependency_detection_in_fixture_swiftpm` | Implemented |

## Test Results

- **New unit tests:** 20 (11 swift_detector + 9 swift_coverage_gate) — all pass.
- **New integration tests:** 11 — all pass.
- **Full suite:** 723 passed, 28 skipped, 0 failed.
- **Type audit:** `pyright validator/drivers/` — 0 errors, 0 warnings.
- **Lint audit:** `ruff check` on driver + new test files passes.

## Notes

- The coverage capability is wired through the `script:` escape hatch (vs `command:`) because Swift has no `--fail-under` flag and the threshold check must be performed after `xcrun llvm-cov export`. This is the exact use case the schema's `script` field documents.
- `swift-coverage-gate.sh` accepts `LIVESPEC_GATE_LCOV` to consume pre-existing lcov data — used by unit tests to exercise the parser deterministically without invoking the Swift toolchain.
- Linux fallback: when `xcrun` is unavailable the script transparently falls back to `llvm-cov` (EC-005). When neither is present, exit 1 with the clear "xcrun not found" message (EC-001).
- `swift_detector.parse_package_dependencies` recognises both URL-based and explicit-name forms, deduplicates `.git` vs non-`.git` URLs, and lowercases names for case-insensitive lookup matching how Swift libraries are referenced in code.
- The `livespec/drivers/scripts/` directory is automatically ignored by `DriverRegistry` (which globs `*.yaml` non-recursively), so no registry change is required.

## Implementation Summary

Feature 019 ships a complete Swift driver covering the 4 standard capabilities. Coverage is gated by a portable shell script (`script:` escape hatch) that runs Swift's coverage tooling and applies the threshold deterministically. Snapshots, properties, and mutation are wired through `swift test` and `muter`, with dependency detection (`swift-snapshot-testing`, `SwiftCheck`) handled by a small Python parser of `Package.swift`. The Xcode-only fallback degrades gracefully via the gate script, while the registry only matches projects with a SwiftPM manifest. All 31 new tests plus the existing 692-test base pass on Python 3.14.

---

*LiveSpec Feature 019 Implementation — Complete — 2026-05-07*
