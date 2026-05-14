# Changelog — Feature 044

> Per-feature changelog for Behavioral Grammar v1.0 — Shared Canonical Reference & Validator.
> Global changes are tracked in `.specs/changelog.md`.

---

## Header

- **Feature:** Behavioral Grammar v1.0 — Shared Canonical Reference & Validator
- **Feature Number:** 044
- **Spec:** `.specs/features/044-behavioral-grammar-v1-shared/spec.md`

---

## Entry Types

| Type | When to Use |
|---|---|
| `Feature` | New functionality implemented |
| `Bugfix` | Defect corrected |
| `Refactor` | Internal improvement without behavior change |
| `Spec Update` | Spec or implementation artefacts updated |

---

## 2026-05-14 — [Feature]: Behavioral Grammar v1.0 — Shared Canonical Reference & Validator

- **Type:** Feature
- **Spec modified:** Yes (created: spec.md, plan.md, implementation.md, progress.md, pipeline.md, changelog.md, checks/2026-05-14.md)
- **Code modified:**
  - `system/grammar/behavioral-specs-v1.md` (created — canonical grammar doc, 8 mandatory flow + 8 mandatory screen sections, frontmatter contract, `VALIDATION_RESULT` enum, minimal valid fixtures, versioning policy)
  - `validator/behavioral_grammar.py` (created — public API: `validate_behavioral`, `VALIDATION_RESULT`, `ValidationOutcome`; stdlib + `python-frontmatter`/`pyyaml` only)
  - `tests/test_behavioral_grammar.py` (created — 5 unit tests, all pass)
  - `.specs/roadmap.md` (added F044 MVP entry)
- **AC impacted:** AC-001..AC-014 (14/14 covered, all PASS)
- **FR impacted:** FR-001..FR-012 (12/12 implemented)
- **Author:** Worker[W-native-behav-4231] via `/spec.feature --auto`
- **Notes:** Strictly additive — F041/042/043 spec.md files byte-identical (verified via `git diff main`). No new dependency. Validator coherent with F041's existing `VALIDATION_RESULT` references. Grammar v1.0 locked; future v1.1+ ships as sibling files leaving v1 untouched. Visual phase explicitly skipped (no UI surface).

---

## 2026-05-14 — [Spec Update]: Meta-doc compliance pass

- **Type:** Spec Update
- **Spec modified:** Yes (sections: `implementation.md` requirement mapping, acceptance criteria mapping, files inventory)
- **Code modified:** None
- **AC impacted:** None (meta-doc compliance only)
- **Author:** Worker[W-native-behav-4231] via meta-conformity iteration
- **Notes:** Brings F044 implementation artefacts in line with `system/templates/implementation-template.md` and `system/templates/changelog-template.md`. Adds historised `checks/2026-05-14.md` and formalises the per-feature `changelog.md` structure required by LiveSpec.

---

*Updated by `/spec.implement`, `/spec.check`, or manually — LiveSpec v1.0*
