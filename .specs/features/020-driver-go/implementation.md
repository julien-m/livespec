---
type: implementation
title: Driver Go — Built-in Test Orchestration Driver
feature: 020-driver-go
spec_ref: spec.md
plan_ref: plan.md
created: 2026-05-07
updated: 2026-05-07
status: Implemented
---

# Implementation — Driver Go

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `livespec/drivers/go.yaml` | `@spec FR-001: Go driver YAML — .specs/features/020-driver-go/spec.md#fr-001` | Implemented | 2026-05-07 |
| FR-002 | `livespec/drivers/scripts/go-coverage-gate.sh` | `@spec FR-002: Go coverage gate escape-hatch script` | Implemented | 2026-05-07 |
| FR-003 | `validator/drivers/go_detector.py` | `@spec FR-003: go.mod dependency parser` | Implemented | 2026-05-07 |
| FR-004 | `tests/integration/test_driver_go.py` | `@spec FR-004: Integration tests for the Go driver` | Implemented | 2026-05-07 |
| FR-005 | `tests/unit/test_go_detector.py`, `tests/unit/test_go_coverage_gate.py` | `@spec FR-005: Unit tests for go.mod parser and gate script` | Implemented | 2026-05-07 |

## Files Created

| File | Purpose |
|---|---|
| `livespec/drivers/scripts/go-coverage-gate.sh` | Escape-hatch shell script: runs `go test -coverprofile=...`, applies threshold via `go tool cover -func` (with awk fallback), and writes inline-converted lcov.info per EC-004. |
| `validator/drivers/go_detector.py` | Pure-Python `go.mod` parser: module path + single-line and multi-line `require` blocks, with `// indirect` stripping. |
| `tests/unit/test_go_detector.py` | 14 unit tests covering module parsing, single/multi-line `require`, dedup, comment stripping, case-insensitive substring lookup. |
| `tests/unit/test_go_coverage_gate.py` | 9 bash-script unit tests: above/below threshold, default 70 threshold, no go.mod, empty coverprofile, missing coverprofile, and lcov grouping per source file. |
| `tests/integration/test_driver_go.py` | 10 integration tests covering manifest schema, registry detection, capability metadata, mutation absence, and dependency detection on a Go fixture. |

## Files Modified

| File | Change |
|---|---|
| `livespec/drivers/go.yaml` | Replaced Feature 016 stub with full 3-capability manifest (coverage uses `script:` escape hatch, snapshots and properties run `go test`, mutation intentionally omitted). |

## Acceptance Criteria Mapping

| AC | Test Case(s) | Status |
|---|---|---|
| AC-001 | `test_registry_loads_go_driver`, `test_go_driver_detects_go_mod` | Implemented |
| AC-002 | `test_coverage_capability_uses_script_escape_hatch`, gate script `go test -coverprofile` invocation | Implemented |
| AC-003 | `test_gate_passes_when_above_threshold`, `test_gate_fails_when_below_threshold`, `test_gate_default_threshold_is_70` | Implemented |
| AC-004 | `test_snapshots_capability_metadata`, `test_dependency_detection_in_fixture_go_module`, `test_has_go_dependency_substring_match` | Implemented |
| AC-005 | `test_properties_capability_metadata`, `test_dependency_detection_in_fixture_go_module` | Implemented |
| AC-006 | `test_mutation_capability_is_absent`, `test_go_driver_capabilities_exist` | Implemented |
| AC-007 | `test_coverage_gate_script_is_shipped_and_executable`, `test_gate_lcov_groups_lines_per_file` | Implemented |
| AC-008 | `test_go_driver_schema_validation` | Implemented |
| AC-009 | `test_parse_go_module_*`, `test_parse_go_dependencies_*` | Implemented |

## Test Results

- **New unit tests:** 23 (14 go_detector + 9 go_coverage_gate) — all pass.
- **New integration tests:** 10 — all pass.
- **Full suite:** 756 passed, 28 skipped, 0 failed.
- **Type audit:** `pyright validator/drivers/` — 0 errors, 0 warnings.
- **Lint audit:** `ruff check` on driver + new test files passes.

## Notes

- Mutation capability is intentionally absent from `go.yaml`. The existing `DriverManifest` schema treats omitted capability blocks as unsupported, and the runner emits the canonical "mutation: not implemented for go driver" message via `CapabilityNotImplementedError` (Feature 016). The YAML carries a comment block explaining the rationale (`go-mutesting` is unmaintained) so users discover the gap when reading the manifest.
- The coverage capability uses the `script:` escape hatch (vs `command:`) because `go test` has no `--fail-under` flag and the threshold check must be performed after coverage parsing — same pattern as Feature 019 (Swift).
- The gate script accepts `LIVESPEC_GATE_COVERPROFILE` to consume pre-existing coverprofile data — used by unit tests to exercise the parser deterministically without invoking `go test`.
- lcov conversion is implemented inline in awk (EC-004): the script does NOT depend on `gocov-xml`, `gcov2lcov`, or any external converter. The conversion sums execution counts when multiple statement ranges share a starting line, ensuring a single `DA:<line>,<count>` entry per source line.
- `go_detector.parse_go_dependencies` recognises both single-line `require` and multi-line `require ( ... )` blocks, strips `// indirect` and other inline comments, and lowercases module paths. `has_go_dependency` does substring matching so callers can lookup either short names (`gopter`) or full paths (`github.com/leanovate/gopter`).
- The gate script defaults to a threshold of **70** (lower than Swift's 75) — Go projects in the wild tend to land around 70-80% coverage, and AC-003 example uses 70%.

## Implementation Summary

Feature 020 ships a complete Go driver covering 3 of the 4 standard capabilities: coverage, snapshots, and properties. Mutation is intentionally omitted because there is no maintained Go mutation testing tool; the omission surfaces a clear "not implemented" message via the existing capability-resolver path. Coverage is gated by a portable shell script (`script:` escape hatch) that runs `go test -coverprofile`, computes the percentage via `go tool cover -func` (with an inline awk fallback), and converts the coverprofile to lcov.info inline — no external converter required (EC-004). Snapshot and property capabilities run `go test ./...` and rely on `go.mod` dependency presence (`go-snaps`, `cupaloy`, `gopter`) discovered by a small Python parser. All 33 new tests plus the existing 723-test base pass on Python 3.14.

---

*LiveSpec Feature 020 Implementation — Complete — 2026-05-07*
