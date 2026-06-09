---
created: 2026-04-15
feature: '007'
status: Complete
title: Structured Signal Extraction — Implementation
---

# Implementation: 007 — Structured Signal Extraction

## Summary

Refactored Step 5.7 sub-steps 2-3 in `.agent-sync/skills/spec-specify/SKILL.md` into a 3-phase pipeline and added 6 integration tests in `tests/test_specify_integration.py`.

## Files Modified

### .agent-sync/skills/spec-specify/SKILL.md

Replaced sub-steps 2-3 of Step 5.7 with:

- **Sub-step 2 (Phase 1):** LLM structured JSON signal extraction with `{"signals": string[]}` schema, retry on malformed JSON, fallback to `signals = []` with WARNING
- **Sub-step 3 (Phase 2):** Deterministic `validator.taxonomy.detect_traits(signals)` call — no hardcoded mapping table in the command file

Sub-steps 1 (taxonomy gate, `--no-behavioral`) and 4-8 (Gherkin injection) remain unchanged.

Added `@spec` anchors for FR-001, FR-002, FR-003.

## Files Created

### tests/test_specify_integration.py

6 pytest test functions validating the Phase 2 contract:

| # | Test | AC |
|---|------|----|
| 1 | `test_form_submit_signals_detect_is_submittable` | AC-005 |
| 2 | `test_modal_close_signals_detect_overlay_and_dismissible` | AC-006 |
| 3 | `test_empty_signals_produce_no_traits` | AC-007 |
| 4 | `test_ambiguous_save_signal_alone_produces_no_traits` | AC-008 |
| 5 | `test_duplicate_signals_normalized_double` | AC-010 |
| 6 | `test_duplicate_signals_normalized_triple` | AC-010 |

All tests call `detect_traits()` directly with fixed signal lists and real taxonomy data (no mocking).

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/test_specify_integration.py -v` | 6/6 passed |
| `pytest tests/test_taxonomy_detection.py -v` | 15/15 passed (non-regression) |
| `pytest tests/ --ignore=tests/integration -q` | 427 passed |
| `ruff check tests/test_specify_integration.py validator/` | 0 violations |
| `pyright tests/test_specify_integration.py` | 0 errors |
| `git diff HEAD -- validator/taxonomy.py` | Empty (SC-004) |
| `--no-behavioral` precedes `detect_traits` in specify.md | Lines 214 vs 229 (AC-011) |

## FR/AC Coverage

- FR-001: Pipeline refactoring — sub-steps 2-3 replaced in `.agent-sync/skills/spec-specify/SKILL.md`
- FR-002: Structured JSON prompt — Phase 1 instructions with retry/fallback
- FR-003: detect_traits delegation — Phase 2 in `.agent-sync/skills/spec-specify/SKILL.md`
- FR-004: Phase 3 unchanged — sub-steps 4-8 byte-identical
- FR-005: 6 integration tests in `tests/test_specify_integration.py`
- FR-006: Real taxonomy data, no mocking
- FR-007: 15/15 non-regression tests pass

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `.specs/features/007-structured-signal-extraction/implementation.md` | @spec(FR-001) | ✅ Implemented | 2026-06-08 |
| FR-002 | `.specs/features/007-structured-signal-extraction/implementation.md` | @spec(FR-002) | ✅ Implemented | 2026-06-08 |
| FR-003 | `.specs/features/007-structured-signal-extraction/implementation.md` | @spec(FR-003) | ✅ Implemented | 2026-06-08 |
| FR-004 | `.specs/features/007-structured-signal-extraction/implementation.md` | @spec(FR-004) | ✅ Implemented | 2026-06-08 |
| FR-005 | `.specs/features/007-structured-signal-extraction/implementation.md` | @spec(FR-005) | ✅ Implemented | 2026-06-08 |
| FR-006 | `.specs/features/007-structured-signal-extraction/implementation.md` | @spec(FR-006) | ✅ Implemented | 2026-06-08 |
| FR-007 | `.specs/features/007-structured-signal-extraction/implementation.md` | @spec(FR-007) | ✅ Implemented | 2026-06-08 |
