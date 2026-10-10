# Changelog — Analyze Gate (070)

## 2026-09-06 — [Spec Update]: Grounded paraphrase coverage

- **AC impacted:** AC-005, AC-012. A fresh complete grounded review can cover obligations without literal ID references; structural findings remain visible at LOW severity. Structural-only diagnostics and invalid review blockers retain their prior severity. Read [feature 078](../078-requirement-evidence-integrity/spec.md) for the governing evidence policy.

## 2026-06-27 — [Feature]: Retroactive spec + code mapping for the Analyze gate

- **Type:** Feature (retroactive specification)
- **Spec modified:** Yes (created spec.md, plan.md, implementation.md)
- **Code modified:** validator/pre_impl_analysis.py, validator/cli.py, validator/pipeline.py (short `@spec` anchors only — no logic rewrite); tests/test_pre_impl_analysis.py, tests/test_pre_impl_analysis_cli.py (traceability headers)
- **AC impacted:** AC-001…AC-012
- **Author:** tool (/spec-feature)
- **Notes:** Code pre-existed on `main` (commit `c519f40`). Pipeline dogfooded: Clarify gate (Phase 1.6) ran with an empty queue (no ambiguities); Analyze gate (Phase 2.6) ran read-only and reported 0 CRITICAL / 0 HIGH, 100% requirement coverage, exit 0.

## 2026-09-06 — Requirement evidence policy

Updated affected requirements before behavior changes; read [feature 078](../078-requirement-evidence-integrity/spec.md) for the complete versioned contract. Preserved existing IDs and historical entries.


## 2026-09-06 — Align active clauses with approved evidence policy

- Read the [updated spec](spec.md) and [078 policy](../078-requirement-evidence-integrity/spec.md). Aligned active severity clauses, ACs, Gherkin, diagrams and classification with current grounded review evidence: missing literal references are HIGH without readiness and LOW only with complete grounded coverage. Structural coverage percentage remains distinct from semantic readiness; contradictions and missing evidence remain blocking. The June observation remains historical.
- Existing FR/AC/SC IDs retained; no code changed and no runtime or final acceptance verdict claimed.
