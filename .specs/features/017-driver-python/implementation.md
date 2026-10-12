---
type: implementation
title: Driver Python — Built-in Test Orchestration Driver
feature: 017-driver-python
spec_ref: spec.md
plan_ref: plan.md
created: 2026-05-06
updated: 2026-05-06
status: Implemented
---

# Implementation — Driver Python — Built-in Test Orchestration Driver

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `livespec/drivers/python.yaml` | `@spec FR-001: Python driver YAML with all 4 capabilities` | ✅ Implemented | 2026-05-06 |
| FR-002 | `validator/drivers/python_detector.py`, `validator/drivers/placeholders.py` | `@spec FR-002: Module auto-detection logic` | ✅ Implemented (wired into `livespec test` via `{module}`) | 2026-10-12 |
| FR-003 | — | — | ❌ Removed 2026-10-12 (syrupy probe deleted: no production caller) | 2026-10-12 |
| FR-004 | — | — | ❌ Removed 2026-10-12 (first-run probe deleted: no production caller) | 2026-10-12 |
| FR-005 | `validator/drivers/mutmut_parser.py` | `@spec FR-005: Mutmut result parsing` | ✅ Implemented | 2026-05-06 |
| FR-006 | `tests/integration/test_driver_python.py` | `@spec FR-006: Integration tests for all 4 capabilities` | ✅ Implemented | 2026-05-06 |
| FR-007 | `tests/unit/test_python_detector.py`, `tests/unit/test_mutmut_parser.py` | `@spec FR-007: Unit tests for module detection` | ✅ Implemented | 2026-05-06 |

## Files Created

| File | Purpose |
|---|---|
| `livespec/drivers/python.yaml` | Python driver manifest — all 4 capabilities declared (coverage, snapshots, properties, mutation) |
| `validator/drivers/python_detector.py` | Module auto-detection from pyproject.toml or filesystem |
| `validator/drivers/mutmut_parser.py` | Mutmut result parsing and mutation score computation |
| `tests/unit/test_python_detector.py` | Unit tests for python_detector module (4 tests) |
| `tests/unit/test_mutmut_parser.py` | Unit tests for mutmut_parser module (7 tests) |
| `validator/drivers/placeholders.py` | Resolves `{module}` (via `detect_python_module`), `{report_path}` and `{threshold}` in driver commands before execution (2026-10-12). |
| `tests/test_driver_placeholders.py` | Unit tests for placeholder resolution (2026-10-12). |
| `tests/integration/test_driver_python_coverage_flow.py` | Level 3A test: `livespec test` runs pytest with the detected module and concrete report/threshold values (2026-10-12). |
| `tests/integration/test_driver_python.py` | 2 integration tests: registry detection and schema-validated 4-capability manifest (2026-10-12 cleanup removed YAML value pins). |

## Files Modified

| File | Change |
|---|---|
| (None) | Feature 017 is self-contained; uses Feature 016 API from validator/drivers/* without modification |

## Acceptance Criteria Mapping

| AC | Test Case | Status |
|---|---|---|
| AC-001 | `test_registry_loads_python_driver` | ✅ Implemented |
| AC-002 | `tests/integration/test_driver_python_coverage_flow.py::test_livespec_test_passes_detected_module_to_python_coverage`, `tests/test_driver_placeholders.py` | ✅ Implemented |
| AC-003 | (Implicit in python.yaml) | ✅ Implemented |
| AC-004 | `tests/integration/test_driver_python_coverage_flow.py::test_livespec_test_passes_detected_module_to_python_coverage`, `tests/unit/test_python_detector.py` | ✅ Implemented |
| AC-005 | — | ❌ Removed 2026-10-12 |
| AC-006 | (Part of snapshots capability declaration) | ✅ Implemented |
| AC-007 | — | ❌ Removed 2026-10-12 |
| AC-008 | `test_python_driver_capabilities_exist` | ✅ Implemented |
| AC-009 | (Mutation capability supports threshold) | ✅ Implemented |
| AC-010 | (Config fields in python.yaml) | ✅ Implemented |
| AC-011 | `test_python_driver_schema_validation` | ✅ Implemented |
| AC-012 | `test_python_driver_capabilities_exist` | ✅ Implemented |

## Test Results

- **Unit tests:** 11 tests pass (4 + 7)
- **Integration tests:** 6 tests pass
- **Feature 016 driver tests:** 35 tests pass (no regressions)
- **Total:** 52 tests pass

## Notes

- Python detector gracefully falls back to directory name if pyproject.toml is malformed or absent
- Mutmut parser handles both JSON and text output formats
- `validator/drivers/runner.py` substitutes the `{module}`, `{report_path}` and `{threshold}` command templates before execution (2026-10-12; previously they reached pytest literally and `livespec test` failed on Python projects)
- Feature 017 validates the Feature 016 driver architecture end-to-end using Python as the pilot stack

## Implementation Summary

Feature 017 delivers a complete Python driver (`python.yaml`) for the test orchestration system. The driver implements 4 capabilities:

1. **Coverage** — pytest-cov integration with lcov.info report generation
2. **Snapshots** — syrupy integration with first-run detection
3. **Properties** — hypothesis integration with statistics reporting
4. **Mutation** — mutmut integration with kill rate computation

Supporting utilities (python_detector, mutmut_parser; syrupy_detector removed 2026-10-12) handle environment detection, installation verification, and result parsing. All code includes `@spec` anchor comments linking to the spec.

Comprehensive unit and integration tests validate all 4 capabilities on fixture projects. The Python driver is now ready to be used by `/spec.test` and `/spec.feature` commands when Python projects are detected.

---

*LiveSpec Feature 017 Implementation — Complete — 2026-05-06*
