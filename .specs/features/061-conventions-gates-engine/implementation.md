---
title: "Implementation - Conventions Gates Engine"
spec_ref: spec.md
feature: 061-conventions-gates-engine
status: Implemented
created: 2026-06-12
updated: 2026-06-25
---

# Implementation — Conventions Gates Engine (061)

**Date:** 2026-06-12
**Status:** Implemented
**Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001](spec.md#fr-001) Gates model and generator | validator/conventions_gates.py, .specs/conventions-gates.yaml | `# @spec(FR-001)` | ✅ Implemented | 2026-06-25 |
| [FR-002](spec.md#fr-002) Deterministic verify engine | validator/conventions_gate.py | `# @spec(FR-002)` | ✅ Implemented | 2026-06-25 |
| [FR-003](spec.md#fr-003) Adapter registry | validator/conventions_lang/*.py | `# @spec(FR-003)` | ✅ Implemented | 2026-06-12 |
| [FR-004](spec.md#fr-004) Receipt and debt report | validator/conventions_receipt.py, validator/conventions_report.py | `# @spec(FR-004)` | ✅ Implemented | 2026-06-12 |
| [FR-005](spec.md#fr-005) CLI commands | validator/cli_commands/utility_cmd.py | `# @spec FR-001`, `# @spec FR-002`, `# @spec FR-005` | ✅ Implemented | 2026-06-12 |
| [FR-006](spec.md#fr-006) Tests | tests/test_conventions_gates_schema.py, tests/test_conventions_verify.py, tests/test_conventions_receipt.py | `# @spec(FR-001)`, `# @spec(FR-002)`, `# @spec(FR-003)`, `# @spec(FR-004)`, `# @spec(FR-005)` | ✅ Implemented | 2026-06-25 |
| [FR-007](spec.md#fr-007) Critic hardening and v1 anti-delegation schema | validator/conventions_gates.py, validator/conventions_linter.py, validator/conventions_gate.py, validator/conventions_receipt.py, .gitignore | `# @spec(FR-001)`, `# @spec(FR-002)`, `# @spec(FR-004)` | ✅ Implemented | 2026-06-12 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| [AC-001](spec.md#ac-001) | tests/test_conventions_gates_schema.py | ✅ |
| [AC-002](spec.md#ac-002) | tests/test_conventions_gates_schema.py, CLI run `livespec conventions gates init --repo .` | ✅ |
| [AC-003](spec.md#ac-003) | tests/test_conventions_verify.py | ✅ |
| [AC-004](spec.md#ac-004) | tests/test_conventions_verify.py | ✅ |
| [AC-005](spec.md#ac-005) | tests/test_conventions_verify.py | ✅ |
| [AC-006](spec.md#ac-006) | tests/test_conventions_verify.py, adapter unit coverage through engine fixtures | ✅ |
| [AC-007](spec.md#ac-007) | tests/test_conventions_receipt.py | ✅ |
| [AC-008](spec.md#ac-008) | tests/test_conventions_verify.py | ✅ |
| [AC-009](spec.md#ac-009) | tests/test_conventions_verify.py | ✅ |
| [AC-010](spec.md#ac-010) | `python3 -m pytest tests/test_conventions_*.py -q` -> 18 passed, 0 skipped | ✅ |
| [AC-011](spec.md#ac-011) | tests/test_conventions_verify.py::test_verify_extracts_ruff_flat_json_violations | ✅ |
| [AC-012](spec.md#ac-012) | tests/test_conventions_receipt.py::test_verify_rejects_receipt_when_gates_file_changed | ✅ |
| [AC-013](spec.md#ac-013) | tests/test_conventions_gates_schema.py::test_conventions_gates_v1_rejects_delegate_and_wiring_fields, tests/test_conventions_gates_schema.py::test_conventions_gates_v1_rejects_command_delegate_to_field | ✅ |
| [AC-014](spec.md#ac-014) | tests/test_conventions_verify.py::test_stale_constitution_hash_blocks_verification, .gitignore | ✅ |
| [AC-015](spec.md#ac-015) | spec.md | ✅ |
| [AC-016](spec.md#ac-016) | tests/test_conventions_verify.py::test_builtin_always_runs_regardless_of_declared_linter | ✅ |
| [AC-017](spec.md#ac-017) | tests/test_conventions_verify.py::test_unreadable_source_file_blocks_without_traceback | ✅ |
| Dependency/tool workspace exclusions | tests/test_conventions_verify.py::test_verify_ignores_generated_dependency_workspaces, tests/test_conventions_verify.py::test_verify_applies_exclusions_to_linter_output | ✅ |

## Files Created/Modified

**Created:**
- `.specs/conventions-gates.yaml`
- `.specs/features/061-conventions-gates-engine/spec.md`
- `.specs/features/061-conventions-gates-engine/plan.md`
- `.specs/features/061-conventions-gates-engine/implementation.md`
- `.specs/features/061-conventions-gates-engine/changelog.md`
- `validator/conventions_gates.py`
- `validator/conventions_gate.py`
- `validator/conventions_report.py`
- `validator/conventions_receipt.py`
- `validator/conventions_linter.py`
- `validator/conventions_lang/`
- `tests/test_conventions_gates_schema.py`
- `tests/test_conventions_verify.py`
- `tests/test_conventions_receipt.py`

**Modified:**
- `validator/cli_commands/utility_cmd.py`
- `.specs/conventions-gates.yaml`

## Visual Baselines

Not applicable — CLI/backend verifier feature, no UI screens.
