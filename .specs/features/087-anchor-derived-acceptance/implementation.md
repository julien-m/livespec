---
created: 2026-10-13
feature: 087-anchor-derived-acceptance
title: 'Implementation Map: Anchor-Derived Acceptance Mapping'
type: implementation
updated: 2026-10-13
---

# Implementation — Anchor-Derived Acceptance Mapping

> Read [spec](spec.md) and [plan](plan.md). Non-UI feature; no visual baselines.

## Requirement Mapping

| Requirement | File(s) | Status | Last Verified |
|---|---|---|---|
| [FR-001: anchor scan and binding](spec.md#fr-001) | `validator/acceptance_anchors.py` | ✅ Implemented | 2026-10-13 |
| [FR-002: derivation field](spec.md#fr-002) | `validator/execution_mapping.py` (`AcceptanceMapping.derivation`, `derived_mapping`) | ✅ Implemented | 2026-10-13 |
| [FR-003: Rust functions](spec.md#fr-003) | `validator/execution_rust_source.py::rust_functions` | ✅ Implemented | 2026-10-13 |
| [FR-004: --derive-mapping](spec.md#fr-004) | `validator/cli_commands/test_cmd.py`, `execution_io.py`, `operation_options.py` | ✅ Implemented | 2026-10-13 |
| [FR-005: anchored certification](spec.md#fr-005) | `validator/execution_mapping.py::_certify_anchored`, `validator/execution_evidence.py::_acceptance_input_gaps` | ✅ Implemented | 2026-10-13 |
| [FR-006: documentation](spec.md#fr-006) | `system/testing/execution-rules.md`, `.agent-sync/skills/spec-implement/SKILL.md` | ✅ Implemented | 2026-10-13 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 to AC-006 | `tests/test_acceptance_anchors.py` (derivation of this mapping is itself anchor-based) | ✅ Pass 2026-10-13 |
| AC-005 (exclusivity) | `tests/test_native_test_option_matrix.py` (`--derive-mapping` row) | ✅ Pass 2026-10-13 |

## Files Created/Modified

| File | Change |
|---|---|
| `validator/acceptance_anchors.py` | New: anchor blocks, Python and Rust targets, issues. |
| `validator/execution_mapping.py` | `derivation`, model validator, `derived_mapping`, `_certify_anchored`; review preparation excludes `derivation` so existing hashes are unchanged. |
| `validator/execution_rust_source.py` | `rust_functions` with inline module paths. |
| `validator/execution_evidence.py` | No review receipt input for a derived mapping. |
| `validator/cli_commands/*.py` | `--derive-mapping`, refusal of review on a derived mapping. |
