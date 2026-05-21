# Legacy UI Contract Audit — 051-integrate-penflow-primary-ui-contract

**Date:** 2026-05-21
**Source mission:** `/Users/julienm/.orchestrate/tmp/livespec-penflow-ui-contract/brief.md`

## Classification

| Legacy surface | Evidence | Classification | Plan impact |
|---|---|---|---|
| `mockup-factory` | `system/integrations.md`, `examples/config/mockups.md.example` | Preserve as upstream visual production workflow | Do not make it the behavior contract source. It may produce Penflow/Pencil inputs later. |
| `mockup-derived` / native mockups | `validator/native_behavioral.py`, `validator/native_behavioral_templates.py`, `tests/test_native_behavioral_specs.py` | Deprecate as primary behavior source, keep as fallback | Penflow semantic tree becomes preferred when present; native generator remains fallback without inventing rules. |
| `.specs/flows` | F041/F042/F044/F045 specs, `validator/behavioral_grammar.py` | Deprecated for new primary UI contract | Keep validator for legacy imports; do not move Penflow flows into `.specs/features`. |
| `.specs/design/screens` | `spec-init`, `spec-plan`, `spec-test`, `spec-check` | Preserve as visual reference/export inventory | Screens stay useful for regression and docs; behavior resolves from `penflow/semantic-ui-tree.json`. |
| Pencil raw `.pen` | `spec-init`, F047, `validator/design_alignment/*` | Rebranch through Penflow enrichment | Root `penflow/ui.pen`/`ui.enriched.pen` carries context; `.specs/design/ui.pen` remains legacy design source. |
| Baselines / pixel diff | `spec-test`, `spec-check`, visual docs/tests | Preserve as complementary gate | Screenshots stay regression gates and never replace Penflow correctness. |
| `native_behavioral` | `validator/native_behavioral.py`, integration tests | Fallback only | Mentioned as legacy fallback when no Penflow workspace exists. |
| `behavioral_grammar` | `system/grammar/behavioral-specs-v1.md`, `validator/behavioral_grammar.py` | Legacy grammar | No extension to Penflow; Penflow uses its own `flow-ui-contract/` grammar. |
| `design-alignment` | F047, `validator/design_alignment/*`, `livespec design-alignment compare` | Preserve, lower priority than Penflow | It remains a visual/runtime layout alignment gate before baseline capture. |
| `/spec-init` | Step 3.6 imports brainstorm mockups into `.specs/design/` | Replace primary import path | If `.brainstorm/penflow/` exists, copy to root `penflow/`, validate, then treat `.specs/design/` as visual support. |
| `/spec-specify` | Brainstorm/native behavioral derivation | Replace for UI features when Penflow exists | Resolve `flow_id`, `screen_id`, `semantic_id`, `test_id` from `penflow/semantic-ui-tree.json`. |
| `/spec-plan` | Reads `.specs/design/screens` | Rebranch | Add `penflow/code-ir.json` as UI implementation input. |
| `/spec-implement` | Reads mockups/theme and preserves behavioral taxonomy | Rebranch | UI agents read `code-ir`, `expected-ui-tree`, and preserve Penflow IDs/bindings/entities/validations/side effects. |
| `/spec-test` | Visual gate + design alignment + baselines | Add blocking Penflow gate | Validate `actual-ui-tree.json`, compare expected vs actual, generate compare/review/fix reports before visual regression. |
| `/spec-check` | FR/AC + visual drift | Add Penflow status | Penflow is blocking for UI flow correctness; screenshots report visual regression separately. |
| Docs/tests | README, docs/visual-testing, command contract tests | Update | Document root `penflow/` workspace and add regression tests for helper/CLI/docs. |

## Optimized Plan

1. Add a small deterministic Penflow contract module and CLI gate; it validates workspace status without implementing runtime adapters.
2. Wire `/spec-init`, `/spec-specify`, `/spec-plan`, `/spec-implement`, `/spec-test`, and `/spec-check` docs to prefer root `penflow/`.
3. Preserve existing Playwright/simulator screenshot baselines as complementary visual regression gates.
4. Add regression tests for workspace bootstrap/status, CLI output, and command documentation.
5. Update README and feature mappings.
