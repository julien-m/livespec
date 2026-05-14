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

## Summary

Purely additive feature shipped per `plan.md`:
- 1 canonical Markdown reference doc.
- 1 Python validator module (stdlib + already-pinned deps only).
- 1 unit-test file with the 5 mandated cases.

Zero modification of F041/042/043 spec.md files. Zero new third-party dependency.

## Files Created

| Path | Purpose | Plan step |
|------|---------|-----------|
| `system/grammar/behavioral-specs-v1.md` | Canonical grammar reference (8/8 mandatory sections per kind, 3-field LiveSpec frontmatter contract, `VALIDATION_RESULT` enum, minimal flow + screen fixtures, versioning policy). | Step 1 |
| `validator/behavioral_grammar.py` | Validator module exposing `validate_behavioral(path)`, `VALIDATION_RESULT`, `ValidationOutcome`, plus frozen module-level constants for mandatory/optional sections per kind. | Step 2 |
| `tests/test_behavioral_grammar.py` | 5 unit tests (flow PASS, flow optional WARNING, flow mandatory FAIL, screen PASS, screen missing-Acteur FAIL). | Step 3 |
| `.specs/features/044-behavioral-grammar-v1-shared/progress.md` | Step-by-step progress tracker. | (process) |
| `.specs/features/044-behavioral-grammar-v1-shared/implementation.md` | This file. | (process) |

## Files Modified

None. F044 is strictly additive (FR-011 / AC-012 / AC-014).

## FR / AC Coverage

| FR | Implementation site |
|----|---------------------|
| FR-001 | `system/grammar/behavioral-specs-v1.md` — full doc structure. |
| FR-002 | `system/grammar/behavioral-specs-v1.md` `## VALIDATION_RESULT Enum` — semantics byte-compatible with F041 (cross-checked against F041 spec.md FR-003 + Key Entities row). |
| FR-003 | `validator/behavioral_grammar.py` — public API (`validate_behavioral`, `VALIDATION_RESULT`, `ValidationOutcome`). |
| FR-004 | `_detect_kind` helper + module docstring. |
| FR-005 | `_check_sections` — FAIL on missing/empty mandatory; per-section diagnostics with file path. |
| FR-006 | `_check_sections` — WARNING on missing optional, extra unknown, wrong order. |
| FR-007 | `_check_sections` — PASS with `diagnostics=[]` when no deviation. |
| FR-008 | Importable as `from validator.behavioral_grammar import validate_behavioral, VALIDATION_RESULT, ValidationOutcome`. |
| FR-009 | Only `python-frontmatter`, `pyyaml`, stdlib used. `pyproject.toml` untouched. |
| FR-010 | `tests/test_behavioral_grammar.py` — 5 tests, 5 mandated cases, all pass. |
| FR-011 | Verified via `git diff main -- .specs/features/04{1,2,3}-*/spec.md` → empty. |
| FR-012 | Spec.md `## Out-of-Scope Guard` already present (no change). |

## Verification (Step 4 + Step 5)

```
$ ruff check validator/behavioral_grammar.py tests/test_behavioral_grammar.py
All checks passed!

$ pyright validator/behavioral_grammar.py tests/test_behavioral_grammar.py
0 errors, 0 warnings, 0 informations

$ pytest tests/test_behavioral_grammar.py -v
5 passed in 0.04s

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
