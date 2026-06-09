---
feature: 024-patch-coverage-local
title: Implementation — 024 Patch Coverage Local Computation
---

# Implementation — 024 Patch Coverage Local Computation

- **Feature:** 024-patch-coverage-local
- **Date:** 2026-05-07
- **Status:** Done
- **Branch:** feature/024-patch-coverage-local

## Summary

Closes the patch coverage feature by adding the threshold gate (`evaluate_patch_gate`) and the `/spec.test`-friendly summary formatter (`summarise_patch_coverage`) on top of the parser/intersection foundation that shipped in feature 016. The full public API is now: `parse_lcov`, `parse_diff`, `compute_patch_coverage`, `evaluate_patch_gate`, `summarise_patch_coverage`, and the `git_diff` helper — all exported from `validator.drivers`.

## Module path deviation (vs. spec FR-001)

Spec FR-001 calls for `livespec/coverage/patch.py`. The foundation actually shipped in feature 016 at `validator/drivers/patch_coverage.py` and is exported via `validator.drivers`. We keep that location to avoid breaking the public surface that features 016 / 017 / 020-023 already depend on. The semantic contract from FR-001 (function name, signature, return type) is honoured — the function lives at `validator.drivers.compute_patch_coverage`. This deviation is intentional and documented here.

## Changes

| File | Change | ACs |
|------|--------|-----|
| `validator/drivers/patch_coverage.py` | Added `evaluate_patch_gate()` and `summarise_patch_coverage()`. Both are pure functions; the runner is unchanged. | AC-007, AC-009 |
| `validator/drivers/__init__.py` | Re-exports the two new helpers. | AC-001 |
| `tests/test_drivers.py` | Seven new tests covering the gate (3) and the summary formatter (4). | FR-006 |

## AC coverage

| AC | Status | Where |
|----|--------|-------|
| AC-001 | Done (016) | `validator.drivers.compute_patch_coverage` — see `test_compute_patch_coverage_full_partial_missing`. |
| AC-002 | Done (016) | `parse_lcov` — `test_parse_lcov_basic`. |
| AC-003 | Done (016) | `parse_diff` — `test_parse_diff_added_lines`. |
| AC-004 | Done (016) | Intersection logic in `compute_patch_coverage`. |
| AC-005 | Done (016) | Missing file → 0% + warning, see `test_compute_patch_coverage_full_partial_missing`. |
| AC-006 | Done (016) | Empty diff → empty `files`, `test_compute_patch_coverage_empty_diff` + `test_summarise_patch_coverage_not_applicable`. |
| AC-007 | **Done (024)** | `evaluate_patch_gate` + `summarise_patch_coverage(threshold=…)` — `test_evaluate_patch_gate_*`, `test_summarise_patch_coverage_threshold_*`. |
| AC-008 | Done (016) | `compute_patch_coverage` is pure file I/O + parsing — confirmed by absence of network imports. |
| AC-009 | **Done (024)** | `summarise_patch_coverage` returns the `/spec.test` summary block (overall + gate + warnings). |

## Verification

```
pytest tests/                  → 859 passed, 28 skipped (suite-wide)
pytest tests/test_drivers.py   → 51 passed (44 baseline + 7 new)
ruff check .                   → all checks passed
mypy validator/drivers/patch_coverage.py → 0 errors
```

`mypy .` currently fails in unrelated files outside this feature's allowed edit set (for example `validator/config.py`, `validator/parser.py`, and `tests/integration/helpers/sdk_runner.py`). `validator/drivers/patch_coverage.py` type-checks cleanly in isolation, but `tests/test_drivers.py` and `validator/drivers/__init__.py` pull in those broader repository issues during import analysis.

## Notes

- `summarise_patch_coverage` is the integration point for `/spec.test`: callers compute a `PatchCoverageReport` then format it. This keeps `run_capability` purely about subprocess execution (FR-003 from feature 016) and preserves AC-011 (missing-report-as-failure) intact.
- `evaluate_patch_gate` returns failing files in input (insertion) order — Python dict order is preserved, which is the contract the tests exercise.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `.specs/features/024-patch-coverage-local/implementation.md` | @spec(FR-001) | ✅ Implemented | 2026-06-08 |
| FR-002 | `.specs/features/024-patch-coverage-local/implementation.md` | @spec(FR-002) | ✅ Implemented | 2026-06-08 |
| FR-003 | `.specs/features/024-patch-coverage-local/implementation.md` | @spec(FR-003) | ✅ Implemented | 2026-06-08 |
| FR-004 | `.specs/features/024-patch-coverage-local/implementation.md` | @spec(FR-004) | ✅ Implemented | 2026-06-08 |
| FR-005 | `.specs/features/024-patch-coverage-local/implementation.md` | @spec(FR-005) | ✅ Implemented | 2026-06-08 |
| FR-006 | `.specs/features/024-patch-coverage-local/implementation.md` | @spec(FR-006) | ✅ Implemented | 2026-06-08 |
