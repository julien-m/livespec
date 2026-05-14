---
title: Behavioral Grammar v1.0 — Implementation Log
feature: 044-behavioral-grammar-v1-shared
spec_ref: ./spec.md
plan_ref: ./plan.md
status: Done
created: 2026-05-14
updated: 2026-05-14
---

# Implementation — 044-behavioral-grammar-v1-shared

## Header

- **Feature:** Behavioral Grammar v1.0 — Shared Canonical Reference & Validator
- **Feature Number:** 044
- **Last Updated:** 2026-05-14
- **Feature Spec:** `.specs/features/044-behavioral-grammar-v1-shared/spec.md`
- **Feature Plan:** `.specs/features/044-behavioral-grammar-v1-shared/plan.md`

---

## Status Legend

| Status | Meaning |
|---|---|
| ✅ Implemented | Fully implemented and tested |
| ⚠️ Partial | Implementation exists but is incomplete or not fully verified |
| ❌ Missing | No implementation found |
| 🔄 Modified | Implementation changed after the initial spec |

---

## Summary

Purely additive feature shipped per `plan.md`:
- 1 canonical Markdown reference doc (`system/grammar/behavioral-specs-v1.md`).
- 1 Python validator module (stdlib + already-pinned `python-frontmatter`/`pyyaml` only).
- 1 unit-test file with the 5 mandated cases.

Zero modification of F041/042/043 spec.md files. Zero new third-party dependency.

---

## Requirement Mapping

> Maps each Functional Requirement to the files and `@spec` anchor comments where it is implemented.

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Canonical grammar doc](spec.md#fr-001) | `system/grammar/behavioral-specs-v1.md` | `@spec FR-001: Canonical behavioral grammar v1.0 reference doc` (`system/grammar/behavioral-specs-v1.md:1`) | ✅ Implemented | 2026-05-14 |
| [FR-002: VALIDATION_RESULT enum coherent with F041](spec.md#fr-002) | `system/grammar/behavioral-specs-v1.md`, `validator/behavioral_grammar.py` | `@spec FR-002: VALIDATION_RESULT enum byte-compatible with F041` (`system/grammar/behavioral-specs-v1.md:2`) | ✅ Implemented | 2026-05-14 |
| [FR-003: `validate_behavioral` public API](spec.md#fr-003) | `validator/behavioral_grammar.py` | `# @spec FR-003: validate_behavioral public API` (validator/behavioral_grammar.py:1) | ✅ Implemented | 2026-05-14 |
| [FR-004: Kind detection rule](spec.md#fr-004) | `validator/behavioral_grammar.py` (`_detect_kind`) | `# @spec FR-004: Kind detection rule` (validator/behavioral_grammar.py:3) | ✅ Implemented | 2026-05-14 |
| [FR-005: FAIL on missing mandatory](spec.md#fr-005) | `validator/behavioral_grammar.py` (`_check_sections`) | `# @spec FR-005, FR-006, FR-007: PASS/WARNING/FAIL` (validator/behavioral_grammar.py:5) | ✅ Implemented | 2026-05-14 |
| [FR-006: WARNING on missing optional / wrong order](spec.md#fr-006) | `validator/behavioral_grammar.py` (`_check_sections`) | `# @spec FR-005, FR-006, FR-007` (validator/behavioral_grammar.py:5) | ✅ Implemented | 2026-05-14 |
| [FR-007: PASS with empty diagnostics](spec.md#fr-007) | `validator/behavioral_grammar.py` (`_check_sections`) | `# @spec FR-005, FR-006, FR-007` (validator/behavioral_grammar.py:5) | ✅ Implemented | 2026-05-14 |
| [FR-008: Canonical import path](spec.md#fr-008) | `validator/behavioral_grammar.py` | `# @spec FR-008: Canonical import path` (validator/behavioral_grammar.py:7) | ✅ Implemented | 2026-05-14 |
| [FR-009: Stdlib + pinned deps only](spec.md#fr-009) | `validator/behavioral_grammar.py`, `pyproject.toml` (untouched) | `# @spec FR-009: Stdlib + pinned deps only` (validator/behavioral_grammar.py:9) | ✅ Implemented | 2026-05-14 |
| [FR-010: 5 unit tests](spec.md#fr-010) | `tests/test_behavioral_grammar.py` | `# @spec FR-010: 5 mandatory unit tests` (tests/test_behavioral_grammar.py:1) | ✅ Implemented | 2026-05-14 |
| [FR-011: Strict additivity](spec.md#fr-011) | — (verified by `git diff main -- .specs/features/04{1,2,3}-*/spec.md` empty) | — (negative requirement — verified externally) | ✅ Implemented | 2026-05-14 |
| [FR-012: Out-of-Scope Guard preserved](spec.md#fr-012) | `.specs/features/044-behavioral-grammar-v1-shared/spec.md` § Out-of-Scope Guard | inline in spec.md | ✅ Implemented | 2026-05-14 |

> **How `@spec` anchors work:** Requirement anchors live in implementation source files, not in `implementation.md`. For this feature they appear in `system/grammar/behavioral-specs-v1.md`, `validator/behavioral_grammar.py`, and `tests/test_behavioral_grammar.py`. Use `grep -rn "@spec FR-003" system/grammar validator tests` to locate them.

---

## Acceptance Criteria Mapping

> Maps each Acceptance Criterion to the test (or verification artefact) that covers it.

| AC | Test File | Status |
|---|---|---|
| [AC-001: Grammar doc exists](spec.md#ac-001) | `system/grammar/behavioral-specs-v1.md` existence check (`test -f`) | ✅ Passing |
| [AC-002: Grammar version 1.0 declared](spec.md#ac-002) | `system/grammar/behavioral-specs-v1.md` (`Grammar version: 1.0`) | ✅ Passing |
| [AC-003: 8 mandatory flow sections](spec.md#ac-003) | `system/grammar/behavioral-specs-v1.md` § Mandatory Flow Sections; `validator/behavioral_grammar.py` `MANDATORY_FLOW_SECTIONS` | ✅ Passing |
| [AC-004: 8 mandatory screen sections](spec.md#ac-004) | `system/grammar/behavioral-specs-v1.md` § Mandatory Screen Sections; `validator/behavioral_grammar.py` `MANDATORY_SCREEN_SECTIONS` | ✅ Passing |
| [AC-005: Frontmatter contract](spec.md#ac-005) | `system/grammar/behavioral-specs-v1.md` § LiveSpec Frontmatter Contract | ✅ Passing |
| [AC-006: VALIDATION_RESULT enum (PASS/WARNING/FAIL)](spec.md#ac-006) | `system/grammar/behavioral-specs-v1.md` § VALIDATION_RESULT Enum; `validator/behavioral_grammar.py` enum definition | ✅ Passing |
| [AC-007: Minimal fixtures](spec.md#ac-007) | `system/grammar/behavioral-specs-v1.md` § Minimal Valid Examples; `tests/test_behavioral_grammar.py::test_flow_valid_returns_pass` | ✅ Passing |
| [AC-008: Versioning policy](spec.md#ac-008) | `system/grammar/behavioral-specs-v1.md` § Versioning Policy | ✅ Passing |
| [AC-009: Validator module exists](spec.md#ac-009) | `validator/behavioral_grammar.py`; import check via `python -c "from validator.behavioral_grammar import validate_behavioral"` | ✅ Passing |
| [AC-010: ValidationOutcome shape](spec.md#ac-010) | `tests/test_behavioral_grammar.py` (`test_flow_valid_returns_pass`, `test_flow_mandatory_section_absent_returns_fail`) | ✅ Passing |
| [AC-011: 5 unit tests pass](spec.md#ac-011) | `tests/test_behavioral_grammar.py` (5 mandated test cases) | ✅ Passing |
| [AC-012: F041/042/043 byte-identical](spec.md#ac-012) | `git diff main -- .specs/features/041-*/spec.md .specs/features/042-*/spec.md .specs/features/043-*/spec.md` | ✅ Passing |
| [AC-013: No new dep](spec.md#ac-013) | `git diff main -- pyproject.toml` | ✅ Passing |
| [AC-014: Out-of-Scope Guard present](spec.md#ac-014) | `.specs/features/044-behavioral-grammar-v1-shared/spec.md` § Out-of-Scope Guard | ✅ Passing |

**Coverage: 14/14 ACs.**

---

## Files Created

| Path | Purpose | Plan step |
|------|---------|-----------|
| `system/grammar/behavioral-specs-v1.md` | Canonical grammar reference (8/8 mandatory sections per kind, 3-field LiveSpec frontmatter contract, `VALIDATION_RESULT` enum, minimal flow + screen fixtures, versioning policy). | Step 1 |
| `validator/behavioral_grammar.py` | Validator module exposing `validate_behavioral(path)`, `VALIDATION_RESULT`, `ValidationOutcome`, plus frozen module-level constants for mandatory/optional sections per kind. | Step 2 |
| `tests/test_behavioral_grammar.py` | 5 unit tests (flow PASS, flow optional WARNING, flow mandatory FAIL, screen PASS, screen missing-Acteur FAIL). | Step 3 |
| `.specs/features/044-behavioral-grammar-v1-shared/progress.md` | Step-by-step progress tracker. | (process) |
| `.specs/features/044-behavioral-grammar-v1-shared/implementation.md` | This file. | (process) |
| `.specs/features/044-behavioral-grammar-v1-shared/changelog.md` | Per-feature changelog. | (process — meta-conformity pass 2026-05-14) |
| `.specs/features/044-behavioral-grammar-v1-shared/checks/2026-05-14.md` | Historised `/spec.check` report. | (process — meta-conformity pass 2026-05-14) |

---

## Files Modified

| Path | Type | Description |
|---|---|---|
| `.specs/roadmap.md` | Spec registry | Added the F044 MVP roadmap entry while keeping prior feature specs untouched. |

No implementation source files were modified beyond the new F044 artefacts; the feature remains strictly additive (FR-011 / AC-012 / AC-014).

---

## Verification (Step 4 + Step 5)

```
$ ruff check validator/behavioral_grammar.py tests/test_behavioral_grammar.py
All checks passed!

$ pyright validator/behavioral_grammar.py tests/test_behavioral_grammar.py
0 errors, 0 warnings, 0 informations

$ pytest tests/test_behavioral_grammar.py -v
5 passed in 0.04s

$ pytest -q  # full repo suite
1391 passed, 32 skipped

$ git diff main -- .specs/features/041-*/spec.md .specs/features/042-*/spec.md .specs/features/043-*/spec.md
(empty)

$ git diff main -- pyproject.toml
(empty)

$ grep -c "VALIDATION_RESULT" system/grammar/behavioral-specs-v1.md
7   # ≥3 required

$ python3 -c "from validator.behavioral_grammar import validate_behavioral, VALIDATION_RESULT; print(VALIDATION_RESULT.PASS)"
VALIDATION_RESULT.PASS
```

Adjacent-test regression check (validator + locks + coherence + commit_context):
`80 passed in 2.28s`.

---

## Notes / Decisions

- The brainstorm `specify-flows` skill defines a different mandatory-section
  set (oriented around AC/FR/Gherkin/Mermaid). F044's spec.md / plan.md
  explicitly mandate 8 *behavioral* mandatory sections per kind, distinct
  from the brainstorm grammar. The 8 names chosen mirror plan.md Step 1
  guidance: `Acteur, Préconditions, Déclencheur, Étapes nominales, Règles
  métier, Erreurs & exceptions, Side-effects, Postconditions` for flows;
  `Acteur, Source d'entrée, Sortie principale, Données affichées, Actions,
  Validations, États UI, Erreurs` for screens. This is a deliberate
  re-statement, not a copy of the brainstorm grammar — F044 is the LiveSpec-
  side canonical reference for *behavioral* specs.
- `VALIDATION_RESULT` is implemented as `class VALIDATION_RESULT(str, Enum)`
  (not `StrEnum`) to keep the enum members behave as strings (`PASS == "PASS"`)
  without binding to Python 3.11+ `StrEnum` semantics; lint suppression
  added inline (`noqa: UP042`) with rationale.
- Optional sections absent IS treated as a non-fatal deviation (WARNING) —
  consequently the PASS test fixtures include the optional `## Notes`
  (and `## Side effects locaux` for screens). This reconciles the otherwise
  contradictory spec.md scenarios "valid → PASS" vs "optional absent →
  WARNING" running against identical fixtures.

---

*Generated by `/spec.implement` — LiveSpec v1.0 — meta-conformity pass 2026-05-14.*
