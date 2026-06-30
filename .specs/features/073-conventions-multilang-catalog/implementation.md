---
created: 2026-06-29
feature: 073-conventions-multilang-catalog
title: "Implementation Map: Multilang Convention AST Catalog + Enforce-by-Default"
type: implementation
updated: 2026-06-30
---

# Implementation Map: Multilang Convention AST Catalog + Enforce-by-Default (073)

**Status:** Implemented (P0/P1 AST slice + exhaustive AI-res/ARS manifest + receipt taxonomy + governance).
**Mode:** Implemented from the approved plan; built on the 072 AST engine.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001, AC-004 | [conventions_feature_scope.py](../../../validator/conventions_feature_scope.py), [rust_adapter.py](../../../validator/conventions_lang/rust_adapter.py), [kotlin_adapter.py](../../../validator/conventions_lang/kotlin_adapter.py), [registry.py](../../../validator/conventions_lang/registry.py) | @spec FR-001 | ✅ | 2026-06-29 |
| FR-002, AC-006 | [ast_grep.py](../../../validator/conventions_ast/backends/ast_grep.py) | @spec FR-002 | ✅ | 2026-06-29 |
| FR-003, AC-005, AC-007 | [rust_high.yaml](../../../validator/conventions_ast/rule_catalog/rust_high.yaml), [swift_high.yaml](../../../validator/conventions_ast/rule_catalog/swift_high.yaml), [kotlin_high.yaml](../../../validator/conventions_ast/rule_catalog/kotlin_high.yaml), [ast_high.yaml](../../../validator/conventions_ast/rule_catalog/ast_high.yaml) | @spec FR-003 | ✅ | 2026-06-29 |
| FR-004, FR-005, AC-001, AC-002, AC-003 | [conventions_gates.py](../../../validator/conventions_gates.py), [conventions_cmd.py](../../../validator/cli_commands/conventions_cmd.py) | @spec FR-004 | ✅ | 2026-06-29 |
| FR-006, AC-008, AC-009 | [taxonomy.py](../../../validator/conventions_ast/taxonomy.py), [conventions_gate.py](../../../validator/conventions_gate.py), [conventions_receipt.py](../../../validator/conventions_receipt.py) | @spec FR-006 | ✅ | 2026-06-30 |
| FR-007, AC-010 | [conventions_gates.py](../../../validator/conventions_gates.py), [conventions_receipt.py](../../../validator/conventions_receipt.py) | @spec FR-007 | ✅ | 2026-06-29 |
| FR-008, FR-009, AC-011, AC-012 | [corpus.py](../../../validator/conventions_ast/corpus.py), [taxonomy.py](../../../validator/conventions_ast/taxonomy.py), [conventions_cmd.py](../../../validator/cli_commands/conventions_cmd.py), [conventions_receipt.py](../../../validator/conventions_receipt.py) | @spec FR-008, FR-009 | ✅ | 2026-06-30 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | [test_conventions_gates_schema.py](../../../tests/test_conventions_gates_schema.py) | ✅ |
| AC-002 | [test_conventions_gates_schema.py](../../../tests/test_conventions_gates_schema.py) | ✅ |
| AC-003 | [test_conventions_lang_multilang.py](../../../tests/test_conventions_lang_multilang.py) | ✅ |
| AC-004 | [test_conventions_lang_multilang.py](../../../tests/test_conventions_lang_multilang.py) | ✅ |
| AC-005 | [test_conventions_ast_multilang.py](../../../tests/test_conventions_ast_multilang.py) | ✅ |
| AC-006 | [test_conventions_ast_multilang.py](../../../tests/test_conventions_ast_multilang.py) | ✅ |
| AC-007 | [test_conventions_ast_multilang.py](../../../tests/test_conventions_ast_multilang.py) | ✅ |
| AC-008 | [test_conventions_taxonomy.py](../../../tests/test_conventions_taxonomy.py) | ✅ |
| AC-009 | [test_conventions_taxonomy.py](../../../tests/test_conventions_taxonomy.py) | ✅ |
| AC-010 | [test_conventions_lang_multilang.py](../../../tests/test_conventions_lang_multilang.py) | ✅ |
| AC-011 | [test_conventions_taxonomy.py](../../../tests/test_conventions_taxonomy.py) | ✅ |
| AC-012 | [test_conventions_taxonomy.py](../../../tests/test_conventions_taxonomy.py) | ✅ |

## Files Created/Modified

**Created:** `validator/conventions_lang/rust_adapter.py`, `validator/conventions_lang/kotlin_adapter.py`, `validator/conventions_ast/taxonomy.py`, `validator/conventions_ast/corpus.py`, `validator/conventions_ast/rule_catalog/{rust_high,swift_high,kotlin_high}.yaml`, fixtures under `tests/fixtures/conventions_ast/{rust,swift,kotlin,ts/no_commonjs_require}/`, tests `test_conventions_lang_multilang.py`, `test_conventions_ast_multilang.py`, `test_conventions_taxonomy.py`.

**Modified:** `validator/conventions_feature_scope.py`, `validator/conventions_lang/registry.py`, `validator/conventions_ast/backends/ast_grep.py`, `validator/conventions_ast/rule_catalog/ast_high.yaml`, `validator/conventions_gates.py`, `validator/cli_commands/conventions_cmd.py`, `validator/cli_commands/conventions_scaffold.py`, `validator/conventions_gate.py`, `validator/conventions_receipt.py`, `tests/test_conventions_gates_schema.py`, `tests/test_conventions_verify.py`.

## Notes

- Deferred (catalogued advisory/unsupported, not enforced): `kotlin.!!`, `swift.!`, DB/design/payment/legal/copy/pricing semantics — see `taxonomy.py`.
- Exhaustive source evidence: `source_manifest` is emitted in `verify --json` for existing v1 projects and in v2 receipts for new/enforce projects. Real AI-res evidence on 2026-06-30: 192 total in-scope sources, 192 classified, 0 unclassified, 36 excluded with reasons.
- Repo-scope `conventions verify` FAIL is pre-existing debt (scripts/templates), independent of 073; 0 new `error` introduced.
