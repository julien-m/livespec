---
created: 2026-10-13
feature: 085-cargo-execution-runner
title: 'Implementation Map: Cargo Execution Runner'
type: implementation
updated: 2026-10-13
---

# Implementation — Cargo Execution Runner

> Read [spec](spec.md) and [plan](plan.md). Non-UI feature (runner and evidence); no visual baselines.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Trusted Cargo routing](spec.md#fr-001) | `validator/execution_cargo_command.py`, `validator/execution_cargo.py`, `validator/execution_runner.py`, `validator/execution_capture.py` | `@spec FR-001: Recognize cargo test commands`, `@spec FR-001: Trusted Cargo runner entry`, `@spec FR-001: Route cargo test through the trusted Cargo runner` | ✅ Implemented | 2026-10-13 |
| [FR-002: Per-test libtest execution](spec.md#fr-002) | `validator/execution_cargo_hook.py` | `@spec FR-002: Per-test libtest execution` | ✅ Implemented | 2026-10-13 |
| [FR-003: Executed assertions](spec.md#fr-003) | `validator/execution_cargo_coverage.py`, `validator/execution_cargo_rustc.sh` | `@spec FR-003: Executed assertions from per-test coverage` | ✅ Implemented | 2026-10-13 |
| [FR-004: Rust assertion identity](spec.md#fr-004) | `validator/execution_rust_source.py`, `validator/execution_mapping.py` | `@spec FR-004: Rust assertion identity`, `@spec FR-004: Rust assertion bindings` | ✅ Implemented | 2026-10-13 |
| [FR-005: Report, trace and gaps](spec.md#fr-005) | `validator/execution_cargo_driver.py`, `validator/execution_capture.py` | `@spec FR-005: Cargo report and trace publication` | ✅ Implemented | 2026-10-13 |
| [FR-006: Cargo test identity](spec.md#fr-006) | `validator/execution_reports.py`, `validator/execution_mapping.py` | `@spec FR-006: Cargo test identity` | ✅ Implemented | 2026-10-13 |
| [FR-007: Pinned provenance](spec.md#fr-007) | `validator/execution_cargo_toolchain.py`, `validator/execution_evidence.py` | `@spec FR-007: Pinned Cargo runner provenance` | ✅ Implemented | 2026-10-13 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_execution_cargo.py` (`test_mapped_integration_assertion_is_certified`) | ✅ Pass 2026-10-13 |
| AC-002 | `tests/test_execution_cargo.py` (`test_bare_test_path_resolves_to_the_unique_binary`), `tests/test_execution_rust_source.py` (`test_cargo_test_ids_resolve_bare_paths_only_when_unique`) | ✅ Pass 2026-10-13 |
| AC-003 | `tests/test_execution_cargo.py` (`test_unreached_assertion_cannot_certify`, `test_binding_must_cite_one_complete_rust_assertion`), `tests/test_execution_rust_source.py` | ✅ Pass 2026-10-13 |
| AC-004 | `tests/test_execution_cargo.py` (`test_failed_ignored_and_filtered_tests_are_reported_faithfully`) | ✅ Pass 2026-10-13 |
| AC-005 | `tests/test_execution_cargo.py` (`test_caller_environment_reaches_the_tests`) | ✅ Pass 2026-10-13 |
| AC-006 | `tests/test_execution_cargo.py` (doctests, missing tools, provenance, runner-owned options, build failure), `tests/test_execution_cargo_command.py` | ✅ Pass 2026-10-13 |

## Files Created/Modified

| File | Change |
|---|---|
| `validator/execution_cargo.py` | Entry point run as `python -I` (`drive`, `hook`). |
| `validator/execution_cargo_driver.py` | Build with `--no-run`, run Cargo with the hook, publish JUnit report, trace and runner gaps. |
| `validator/execution_cargo_hook.py` | Cargo target runner: `--list`, one process per test with libtest log and coverage profile. |
| `validator/execution_cargo_coverage.py` | Merge/export profiles, region lookup, panic locations. |
| `validator/execution_cargo_command.py` | Cargo/libtest argument classification. |
| `validator/execution_cargo_toolchain.py` | Host triple, LLVM tools location, provenance. |
| `validator/execution_cargo_rustc.sh` | `RUSTC_WORKSPACE_WRAPPER` instrumenting `rustc --test` crates. |
| `validator/execution_rust_source.py` | Rust assertion lexer. |
| `validator/execution_runner.py` | Routes `cargo test` to the Cargo runner. |
| `validator/execution_capture.py` | `CargoRunnerUnavailable` gap, `runner-gaps` consumption. |
| `validator/execution_evidence.py` | Provenance recomputed by runner kind. |
| `validator/execution_mapping.py` | Rust binding span and observed expression checks, bare-path resolution. |
| `validator/execution_reports.py` | Cargo test identity helpers. |
| `system/testing/execution-rules.md` | Cargo usage, requirements and limits. |
| `tests/execution_cargo_support.py`, `tests/test_execution_cargo.py`, `tests/test_execution_cargo_command.py`, `tests/test_execution_rust_source.py` | Fixture crate and tests. |
