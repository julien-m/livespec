---
title: "Implementation - Conventions Gates Engine"
spec_ref: spec.md
feature: 061-conventions-gates-engine
status: Implemented
created: 2026-06-12
updated: 2026-06-12
---

# Implementation — Conventions Gates Engine (061)

**Date:** 2026-06-12
**Status:** Implemented
**Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001](spec.md#fr-001) Gates model and generator | validator/conventions_gates.py, .specs/conventions-gates.yaml | `# @spec(FR-001)` | ✅ Implemented | 2026-06-12 |
| [FR-002](spec.md#fr-002) Deterministic verify engine | validator/conventions_gate.py | `# @spec(FR-002)` | ✅ Implemented | 2026-06-12 |
| [FR-003](spec.md#fr-003) Adapter registry | validator/conventions_lang/*.py | `# @spec(FR-003)` | ✅ Implemented | 2026-06-12 |
| [FR-004](spec.md#fr-004) Receipt and debt report | validator/conventions_receipt.py, validator/conventions_report.py | `# @spec(FR-004)` | ✅ Implemented | 2026-06-12 |
| [FR-005](spec.md#fr-005) CLI commands | validator/cli_commands/utility_cmd.py | `# @spec FR-001`, `# @spec FR-002`, `# @spec FR-005` | ✅ Implemented | 2026-06-12 |
| [FR-006](spec.md#fr-006) Tests | tests/test_conventions_gates_schema.py, tests/test_conventions_verify.py, tests/test_conventions_receipt.py | `# @spec(FR-001)`, `# @spec(FR-002)`, `# @spec(FR-003)`, `# @spec(FR-004)`, `# @spec(FR-005)` | ✅ Implemented | 2026-06-12 |

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
| [AC-010](spec.md#ac-010) | `python3 -m pytest tests/test_conventions_*.py -q` -> 9 passed, 0 skipped | ✅ |

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
- `validator/conventions_lang/`
- `tests/test_conventions_gates_schema.py`
- `tests/test_conventions_verify.py`
- `tests/test_conventions_receipt.py`

**Modified:**
- `validator/cli_commands/utility_cmd.py`

## Visual Baselines

Not applicable — CLI/backend verifier feature, no UI screens.
