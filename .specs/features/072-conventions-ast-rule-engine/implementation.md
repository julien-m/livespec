---
created: 2026-06-29
feature: 072-conventions-ast-rule-engine
title: "Implementation Map: Conventions AST Rule Engine"
type: implementation
updated: 2026-06-29
---

# Implementation Map: Conventions AST Rule Engine (072)

**Status:** Implemented.
**Mode:** Implemented from the approved plan with targeted AST, receipt, CLI, doctor, and feature-scope repair coverage.

## Requirement Mapping

| Req | Behavior | Source File | @spec Anchor | Test |
|---|---|---|---|---|
| FR-001, FR-002, AC-013, AC-014 | Separate AST rule layer while LiveSpec keeps receipt/verdict authority | [models.py](../../../validator/conventions_ast/models.py), [engine.py](../../../validator/conventions_ast/engine.py) | @spec FR-001, @spec FR-002 | test_ast_observe_records_matches_without_ast_violations |
| FR-003, FR-004, FR-005, AC-001, AC-002, AC-003 | Compatible gates v1/v2 and opt-in AST rollout init | [conventions_gates.py](../../../validator/conventions_gates.py), [conventions_cmd.py](../../../validator/cli_commands/conventions_cmd.py) | @spec FR-003, @spec FR-004, @spec FR-005 | test_generate_gates_keeps_v1_default_and_writes_v2_only_for_ast_mode |
| FR-006, FR-007, FR-008, FR-009, FR-010, AC-004, AC-005, AC-006, AC-007, AC-008 | off/observe/enforce mode conversion, backend absence behavior, and `SourceKind="ast"` | [conventions_gate_types.py](../../../validator/conventions_gate_types.py), [engine.py](../../../validator/conventions_ast/engine.py), [base.py](../../../validator/conventions_ast/backends/base.py), [fake.py](../../../validator/conventions_ast/backends/fake.py), [ast_grep.py](../../../validator/conventions_ast/backends/ast_grep.py) | @spec FR-006, @spec FR-007, @spec FR-008, @spec FR-009, @spec FR-010 | test_ast_off_mode_skips_backend_and_has_no_receipt_effect; test_ast_enforce_converts_matches_to_ast_violations |
| FR-011, FR-012, FR-013, AC-009, AC-010, AC-011 | v1-compatible receipt verification and v2 AST receipt fields | [conventions_receipt.py](../../../validator/conventions_receipt.py) | @spec FR-011, @spec FR-012, @spec FR-013 | test_write_and_verify_v2_ast_observe_receipt; test_v2_observe_receipt_rejects_ast_violations |
| FR-014, AC-012 | Mode-aware receipt consumer policy for doctor/spec-check style callers | [conventions_receipt_policy.py](../../../validator/conventions_receipt_policy.py) | @spec FR-014 | test_policy_observe_warns_without_blocking; test_policy_enforce_blocks_when_receipt_absent_or_not_pass |
| FR-015, FR-016, AC-015, AC-016 | Active high-precision AST catalogue validation and traceable rules | [catalog.py](../../../validator/conventions_ast/catalog.py), [ast_high.yaml](../../../validator/conventions_ast/rule_catalog/ast_high.yaml) | @spec FR-015, @spec FR-016 | test_load_ast_catalog_accepts_high_precision_ast_rule_with_traceability |
| FR-017, FR-018, AC-017 | Out-of-scope categories stay inactive and JSON exposes `ast_summary` only for v2 AST mode | [conventions_cmd.py](../../../validator/cli_commands/conventions_cmd.py), [engine.py](../../../validator/conventions_ast/engine.py) | @spec FR-017, @spec FR-018 | test_cli_verify_json_omits_ast_summary_for_v1_and_includes_observe_summary |

## AC Coverage

| AC | Covered by | Status |
|---|---|---|
| AC-001 | gates init default v1 and explicit `--ast-mode` v2 path | Implemented |
| AC-002 | gates loader accepts schema v1 and v2 | Implemented |
| AC-003 | pydantic mode validation for `off`, `observe`, `enforce` | Implemented |
| AC-004 | AST off returns no summary, no backend scan, no AST violation | Implemented |
| AC-005 | observe emits summary fields without AST violations | Implemented |
| AC-006 | enforce converts AST matches into `GateViolation(source="ast")` | Implemented |
| AC-007 | `SourceKind` includes `ast` | Implemented |
| AC-008 | backend absence is warning metadata in observe and blocker in enforce | Implemented |
| AC-009 | v1 receipt verification remains supported | Implemented |
| AC-010 | v2 receipt fields validated, AST violations rejected outside enforce | Implemented |
| AC-011 | receipt hash covers gates hash plus v2 AST summary fields | Implemented |
| AC-012 | receipt policy maps off/v1 to unchanged, observe to warning, enforce to block | Implemented |
| AC-013 | AST backend remains detection-only; LiveSpec creates violations and receipts | Implemented |
| AC-014 | [`validator/conventions_lang/`](../../../validator/conventions_lang/) remains source metadata provider; [`validator/conventions_ast/`](../../../validator/conventions_ast/) is separate | Implemented |
| AC-015 | first catalogue accepts only ast/high rules | Implemented |
| AC-016 | active rules require pass/fail fixtures and ai-ressources traceability | Implemented |
| AC-017 | JSON `ast_summary` appears only for v2 AST-enabled verification | Implemented |

## Verification

| Command | Result |
|---|---|
| `ruff check validator/conventions_ast validator/conventions_gates.py validator/conventions_receipt.py validator/conventions_receipt_policy.py validator/conventions_gate.py validator/cli_commands/conventions_cmd.py validator/doctor/scanner.py tests/test_conventions_ast_engine.py tests/test_conventions_ast_catalog.py tests/test_conventions_receipt_policy.py tests/test_conventions_verify.py tests/test_conventions_verify_scope.py tests/test_doctor.py` | PASS |
| `pytest tests/test_conventions_gates_schema.py tests/test_conventions_receipt.py tests/test_conventions_ast_engine.py tests/test_conventions_ast_catalog.py tests/test_conventions_receipt_policy.py tests/test_conventions_verify.py tests/test_conventions_verify_scope.py tests/test_doctor.py tests/test_run_receipts.py tests/test_goal_contracts.py -q` | PASS: 177 passed |
| `pytest tests/test_conventions_verify_scope.py -q` | PASS: 13 passed |

## Notes

- `validator/conventions_feature_scope.py` now uses dirty source fallback only before `implementation.md` exists. Once the implementation map exists, conventions receipts follow explicit feature mappings instead of all dirty workspace files.
