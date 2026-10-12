# Implementation: Conventions Gate Signal

> Feature 082 · Read [spec](spec.md) and [plan](plan.md). Updated by `/spec-implement`.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001](spec.md#fr-001) Fixture root excluded | [conventions_gates.py](../../../validator/conventions_gates.py), [conventions_gate.py](../../../validator/conventions_gate.py), [conventions_linter_runner.py](../../../validator/conventions_linter_runner.py) | `@spec FR-001: Declared detector fixtures are never sources` | ✅ Implemented | 2026-10-10 |
| [FR-002](spec.md#fr-002) Fixture contract | [ars_rules.py](../../../validator/conventions_ast/ars_rules.py) (`_fixture_inventory_id`), Swift [pass.swift](../../../tests/fixtures/conventions_ast/swift/no_try_force/pass.swift) / [fail.swift](../../../tests/fixtures/conventions_ast/swift/no_try_force/fail.swift) headers | `@spec FR-003, FR-004: Grouped and framework-gated ARS runtime` | ✅ Implemented | 2026-10-10 |
| [FR-003](spec.md#fr-003) Family grouping | [ars_grouping.py](../../../validator/conventions_ast/ars_grouping.py), [ars_rules.py](../../../validator/conventions_ast/ars_rules.py), [conventions_gate_types.py](../../../validator/conventions_gate_types.py) | `@spec FR-003: One violation per file and shared detector` | ✅ Implemented | 2026-10-10 |
| [FR-004](spec.md#fr-004) Framework applicability | [ars_applicability.py](../../../validator/conventions_ast/ars_applicability.py), [ars_rules.py](../../../validator/conventions_ast/ars_rules.py) | `@spec FR-004: Framework applicability for ARS rules` | ✅ Implemented | 2026-10-10 |
| [FR-005](spec.md#fr-005) Repo baseline partition | [conventions_baseline.py](../../../validator/conventions_baseline.py), [conventions_baseline_apply.py](../../../validator/conventions_baseline_apply.py), [conventions_gate_types.py](../../../validator/conventions_gate_types.py), [conventions_cmd.py](../../../validator/cli_commands/conventions_cmd.py) | `@spec FR-005, FR-007: Repo baseline partition and receipt binding` | ✅ Implemented | 2026-10-10 |
| [FR-006](spec.md#fr-006) `--write-baseline` | [conventions_cmd.py](../../../validator/cli_commands/conventions_cmd.py), [conventions_baseline.py](../../../validator/conventions_baseline.py) | `@spec FR-005, FR-006: Versioned repo baseline file` | ✅ Implemented | 2026-10-10 |
| [FR-007](spec.md#fr-007) Feature independence, binding, guard | [conventions_receipt.py](../../../validator/conventions_receipt.py), [conventions_diffguard.py](../../../validator/conventions_diffguard.py), [conventions_cmd.py](../../../validator/cli_commands/conventions_cmd.py) | `@spec FR-007: The repo baseline is a protected conventions input` | ✅ Implemented | 2026-10-10 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| [AC-001](spec.md#ac-001) | [test_conventions_gate_signal.py](../../../tests/test_conventions_gate_signal.py) | ✅ 2026-10-10 |
| [AC-002](spec.md#ac-002) | [test_conventions_gate_signal.py](../../../tests/test_conventions_gate_signal.py) | ✅ 2026-10-10 |
| [AC-003](spec.md#ac-003) | [test_conventions_gate_signal.py](../../../tests/test_conventions_gate_signal.py), [test_conventions_ars_rules.py](../../../tests/test_conventions_ars_rules.py) | ✅ 2026-10-10 |
| [AC-004](spec.md#ac-004) | [test_conventions_gate_signal.py](../../../tests/test_conventions_gate_signal.py) | ✅ 2026-10-10 |
| [AC-005](spec.md#ac-005) | [test_conventions_baseline.py](../../../tests/test_conventions_baseline.py) | ✅ 2026-10-10 |
| [AC-006](spec.md#ac-006) | [test_conventions_baseline.py](../../../tests/test_conventions_baseline.py) | ✅ 2026-10-10 |
| [AC-007](spec.md#ac-007) | [test_conventions_baseline.py](../../../tests/test_conventions_baseline.py) | ✅ 2026-10-10 |
| [AC-008](spec.md#ac-008) | [test_conventions_baseline.py](../../../tests/test_conventions_baseline.py) | ✅ 2026-10-10 |

## Files Created/Modified

- **Created:** `validator/conventions_ast/ars_applicability.py`, `validator/conventions_ast/ars_grouping.py`, `validator/conventions_baseline.py`, `validator/conventions_baseline_apply.py`, `tests/test_conventions_gate_signal.py`, `tests/test_conventions_baseline.py`, `.specs/conventions/baseline.json`.
- **Modified:** `validator/conventions_gates.py`, `validator/conventions_gate.py`, `validator/conventions_linter_runner.py` (fixture exclusion; linter violations now carry the project-relative path so baseline keys are portable), `validator/conventions_gate_types.py`, `validator/conventions_ast/ars_rules.py`, `validator/conventions_receipt.py`, `validator/conventions_diffguard.py`, `validator/cli_commands/conventions_cmd.py`, `tests/test_conventions_ars_rules.py` (membership in `rule_ids`), Swift AST fixtures (configured header), `system/conventions-enforcement.md`.
