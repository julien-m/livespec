# Changelog: Multilang Convention AST Catalog + Enforce-by-Default (073)

## 2026-06-30 — [Fix]: Immediate non-conceptual sources executable through source families

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** validator/conventions_ast/source_decisions.py, validator/conventions_ast/source_decision_builders.py, validator/conventions_ast/source_decision_types.py, validator/conventions_ast/source_decision_validation.py, validator/conventions_ast/source_family_checks.py, tests/test_conventions_source_decisions.py, tests/test_conventions_generated_catalog.py, tests/test_conventions_css_tailwind.py, tests/test_conventions_sql.py, tests/test_conventions_source_family_checks.py
- **AC impacted:** AC-008, AC-009, AC-011, AC-012
- **Author:** spec-fix

### Highlights

- Replaced immediate-scope advisory/non-executable/unsupported decisions with executable or generated-executable source-backed decisions.
- Replaced the rejected generic `source-decision-contract` backend with 15 deterministic generated source families: `ai_prompt`, `code_prose`, `css_design_tokens`, `database_sql`, `delphi_code`, `design_system`, `go_code`, `javascript_code`, `json_yaml_config`, `markdown_docs`, `payment_contract`, `platform_ops`, `python_code`, `shell_code`, `typescript_ui`.
- Added `deferred_conceptual_editorial` decisions tied to Project Notion task `38fb8415-08de-8130-99a9-eff9a1cf5283`; these sources are visible but not counted as completed.
- Fresh feature-scoped receipt PASS: `.specs/conventions/runs/worker-073-executable-nonconceptual-cycle02/receipt.json`.
- Proven counts: 192 total, 192 decided, 0 undecided, 164 immediate scope, 3 executable, 161 generated-executable, 0 immediate-scope non-executable, 28 deferred conceptual/editorial, 60 excluded.

## 2026-06-30 — [Fix]: ARS source decision manifest and executable contract gate

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** validator/conventions_ast/source_decisions.py, validator/conventions_ast/{catalog.py,models.py,taxonomy.py}, validator/conventions_ast/rule_catalog/{ast_high,rust_high,swift_high,kotlin_high}.yaml, validator/conventions_gate.py, validator/conventions_receipt.py, validator/cli_commands/conventions_cmd.py, validator/conventions_rules.py
- **AC impacted:** AC-008, AC-009, AC-011, AC-012
- **Author:** spec-fix

### Highlights

- Added `rule_decision_manifest` with 192 decided sources, 0 undecided sources, explicit advisory/executable/non-executable/unsupported counts, and catalog-load errors surfaced as blockers.
- Hardened executable catalog entries with `decision_kind`, `domain`, `detector`, fixture family, and deterministic test evidence metadata.
- Fixed v1/feature-scoped `verify --json` to expose non-empty advisory/unsupported taxonomy lists, matching the written receipt.
- Fixed the strict rulebook compile schema so every declared item property is listed in `required`.
- Feature-scoped deterministic conventions receipt PASS: `.specs/conventions/runs/073-worker-final-20260630/receipt.json`. Provider-backed compile/semantic remains blocked until the rulebook provider returns successfully.

## 2026-06-30 — [Feature]: Exhaustive AI-res/ARS source manifest

- **Type:** Feature
- **Spec modified:** Yes (Story 3, AC-011/AC-012, FR-008/FR-009, SC-004)
- **Code modified:** validator/conventions_ast/corpus.py, validator/conventions_ast/taxonomy.py, validator/cli_commands/conventions_cmd.py, validator/conventions_receipt.py
- **AC impacted:** AC-011, AC-012
- **Author:** tool-worker

### Highlights

- Added deterministic AI-res/ARS corpus discovery from `.conventions/manifest.yaml`.
- Every in-scope Markdown/YAML convention source is classified with domains, languages, support status, and reason.
- Verify JSON now exposes `source_manifest` for existing v1-gates projects and new v2-gates projects.
- v2 receipts include `source_manifest` alongside advisory/unsupported taxonomy.
- Real AI-res evidence: 192 total in-scope sources, 192 classified, 0 unclassified, 36 excluded with reasons.

## 2026-06-29 — [Feature]: Multilang AST catalog, enforce-by-default, receipt taxonomy

- **Type:** Feature
- **Spec modified:** Yes (created spec.md, plan.md, implementation.md; supersedes 072 AC-001/AC-002/SC-001/SC-002)
- **Code modified:** validator/conventions_feature_scope.py, validator/conventions_lang/{rust_adapter,kotlin_adapter,registry}.py, validator/conventions_ast/backends/ast_grep.py, validator/conventions_ast/rule_catalog/{ast_high,rust_high,swift_high,kotlin_high}.yaml, validator/conventions_ast/taxonomy.py, validator/conventions_gates.py, validator/cli_commands/{conventions_cmd,conventions_scaffold}.py, validator/conventions_gate.py, validator/conventions_receipt.py
- **AC impacted:** AC-001..AC-010
- **Author:** tool-worker

### Highlights

- Multilang infra before rules: `.rs/.kt/.kts` suffixes, Rust/Kotlin adapters, multi-pattern backend (anti false-PASS).
- 7 sourced, hash-valid, `sg`-proven `enforced_ast` rules across TS/Rust/Swift/Kotlin (vs 1).
- `gates init` defaults to schema v2 `enforce`; `--ast-mode off` opts out to legacy v1; `observe` explicit.
- Receipt + `verify --json` now serialize `advisory_rules[]` / `unsupported_rules[]` (SQL/design/payment advisory; legal/copy/pricing + kotlin `!!`/swift `!` unsupported) — never blocking.
- 072 default-mode invariant superseded (recorded in 072 changelog).
