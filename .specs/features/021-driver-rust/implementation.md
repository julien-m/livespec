---
type: implementation
title: Driver Rust — Built-in Test Orchestration Driver
feature: 021-driver-rust
spec_ref: spec.md
plan_ref: plan.md
created: 2026-05-07
updated: 2026-05-07
status: Implemented
---

# Implementation — Driver Rust

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `livespec/drivers/rust.yaml` | `@spec FR-001: Rust driver YAML — .specs/features/021-driver-rust/spec.md#fr-001` | Implemented | 2026-05-07 |
| FR-002 | `validator/drivers/rust_detector.py::parse_cargo_dependencies` | `@spec FR-002: Cargo.toml dependency parser` | Implemented | 2026-05-07 |
| FR-003 | `validator/drivers/rust_detector.py::parse_cargo_mutants_json` | `@spec FR-003: cargo-mutants JSON parser` | Implemented | 2026-05-07 |
| FR-004 | `tests/integration/test_driver_rust.py` | `@spec FR-004: Integration tests for the Rust driver` | Implemented | 2026-05-07 |
| FR-005 | `tests/unit/test_rust_detector.py` | `@spec FR-005: Unit tests for Cargo.toml parser and cargo-mutants JSON parser` | Implemented | 2026-05-07 |

## Files Created

| File | Purpose |
|---|---|
| `livespec/drivers/rust.yaml` | Rust built-in driver manifest with all 4 capabilities — coverage uses pure `command:` (native `cargo llvm-cov --fail-under-lines`), no escape-hatch script. |
| `validator/drivers/rust_detector.py` | Pure-Python `Cargo.toml` parser via `tomllib` (extracts `[dependencies]`, `[dev-dependencies]`, `[build-dependencies]`) plus `cargo mutants --json` summary parser exposing caught/missed/timeout/unviable counts. |
| `tests/unit/test_rust_detector.py` | 18 unit tests covering Cargo.toml parsing (string + table value forms, dedup, malformed input), case-insensitive crate lookup, and the cargo-mutants JSON parser (single-object, nested, line-delimited, missing keys, malformed input). |
| `tests/integration/test_driver_rust.py` | 10 integration tests covering manifest schema, registry detection, all 4 capability metadata blocks, native-command coverage assertion (no script), and dependency detection on a Cargo fixture. |

## Files Modified

None — `livespec/drivers/rust.yaml` did not previously exist as a stub (unlike Swift/Go where Feature 016 had pre-seeded a placeholder).

## Acceptance Criteria Mapping

| AC | Test Case(s) | Status |
|---|---|---|
| AC-001 | `test_registry_loads_rust_driver`, `test_rust_driver_detects_cargo_toml` | Implemented |
| AC-002 | `test_coverage_capability_uses_native_command` (asserts `cargo llvm-cov --lcov --output-path lcov.info --fail-under-lines`) | Implemented |
| AC-003 | `test_coverage_capability_uses_native_command` (threshold 80) — runtime install hint surfaced by the existing capability runner | Implemented |
| AC-004 | `test_snapshots_capability_metadata`, `test_dependency_detection_in_fixture_cargo_project` | Implemented |
| AC-005 | `test_snapshots_capability_metadata` (asserts `--unreferenced=reject`) — review hint surfaced by runner on failure | Implemented |
| AC-006 | `test_properties_capability_metadata`, `test_dependency_detection_proptest_takes_priority_over_quickcheck` | Implemented |
| AC-007 | `test_mutation_capability_metadata` — install hint surfaced by runner when `cargo-mutants` absent | Implemented |
| AC-008 | `test_mutation_capability_metadata` (asserts `--json`), `test_parse_cargo_mutants_json_*` (6 unit tests) | Implemented |
| AC-009 | `test_rust_driver_schema_validation`, `test_rust_driver_capabilities_exist` | Implemented |
| AC-010 | `test_parse_cargo_dependencies_*` (string + table value forms, dedup, malformed) | Implemented |

## Test Results

- **New unit tests:** 18 (all in `test_rust_detector.py`) — all pass.
- **New integration tests:** 10 (all in `test_driver_rust.py`) — all pass.
- **Full suite:** 784 passed, 28 skipped, 0 failed.
- **Type audit:** `pyright validator/drivers/` — 0 errors, 0 warnings.
- **Lint audit:** `ruff check` on driver + new test files passes.

## Notes

- **No escape-hatch script.** Rust is the only stack in the test-driver batch (016–021) where every capability is a plain `command:` field. `cargo llvm-cov` provides `--fail-under-lines` natively, so the coverage gate is enforced inside the cargo subprocess — the Pydantic `DriverCapability` schema accepts this directly without changes (SC-001).
- **No `livespec/drivers/scripts/rust-*.sh` artifact** is shipped, by design.
- **Cargo.toml parsing uses `tomllib`** (Python 3.11+ stdlib), matching AC-010's "dedicated parser, not shell grep" requirement. The parser walks `[dependencies]`, `[dev-dependencies]`, and `[build-dependencies]`, supporting both `dep = "version"` (string value) and `dep = { version = "...", features = [...] }` (table value) syntaxes (SC-004).
- **cargo-mutants JSON parser is dual-form.** Different `cargo-mutants` versions emit either a single-object summary or one JSON object per mutant (line-delimited). The parser handles both: it first tries a whole-stdout `json.loads`, then falls back to per-line aggregation by `outcome`/`status` field. Unknown outcome strings are silently ignored; missing keys default to zero. Malformed input never raises.
- **Threshold default is 80%** matching the spec example (Story 1, AC-002). Higher than Swift (75) and Go (70) because Rust projects in the wild — and the cargo-llvm-cov reference doc — typically target 80%. Users override via `.specs/drivers/rust.yaml`.
- **`--all-features` is intentionally NOT included** in the default coverage command. EC-002 documents this as a configurable concern; baking `--all-features` into the default would slow down detection of CI regressions on minimal feature sets. Projects that want it override the command in `.specs/drivers/rust.yaml`.
- **proptest preferred over quickcheck** is encoded in the `parse_cargo_dependencies` ordering (preserves first-seen order across `[dev-dependencies]`), so a downstream caller iterating the list in order naturally gets proptest first when both are present (Story 3 priority rule).

## Implementation Summary

Feature 021 ships a complete Rust driver covering all 4 standard capabilities (coverage, snapshots, properties, mutation). It is the only driver in the test-driver batch (016–021) where every capability is a plain `command:` — no shell escape hatch, no gate script. Coverage is gated natively via `cargo llvm-cov --fail-under-lines 80`; snapshots run `cargo insta test --unreferenced=reject` to fail on stale `.snap` files; properties run `cargo test`; mutation runs `cargo mutants --json` whose output is parsed by a small `parse_cargo_mutants_json` helper that handles both single-object summaries and line-delimited per-mutant streams. Dependency detection (`insta`, `proptest`, `quickcheck`) is handled by a `tomllib`-based parser of `Cargo.toml` that walks `[dependencies]`, `[dev-dependencies]`, and `[build-dependencies]`. All 28 new tests plus the existing 756-test base pass on Python 3.14 (784 total).

---

*LiveSpec Feature 021 Implementation — Complete — 2026-05-07*
