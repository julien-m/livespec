---
title: "Deterministic Command Goal Contracts Implementation"
feature: "052-deterministic-command-goal-contracts"
---

# Implementation — 052-deterministic-command-goal-contracts

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `validator/goal_contracts.py` | Module-level `@spec FR-001` | ✅ Implemented | 2026-05-21 |
| FR-002 | `validator/goal_contracts.py` | Module-level `@spec FR-002` | ✅ Implemented | 2026-05-21 |
| FR-003 | `validator/goal_contracts.py` | Module-level `@spec FR-003` | ✅ Implemented | 2026-05-21 |
| FR-004 | `validator/goal_contracts.py` | Module-level `@spec FR-004` | ✅ Implemented | 2026-05-21 |
| FR-005 | `validator/goal_contracts.py` | Module-level `@spec FR-005` | ✅ Implemented | 2026-05-21 |
| FR-006 | `validator/goal_contracts.py` | Module-level `@spec FR-006` | ✅ Implemented | 2026-05-21 |
| FR-007 | `validator/goal_contracts.py` | Module-level `@spec FR-007` | ✅ Implemented | 2026-05-21 |
| FR-008 | `validator/cli_commands/goal_cmd.py`, `validator/cli.py` | CLI module `@spec FR-008` | ✅ Implemented | 2026-05-21 |
| FR-009 | `validator/cli_commands/goal_cmd.py`, `validator/goal_contracts.py` | CLI module `@spec FR-009` | ✅ Implemented | 2026-05-21 |
| FR-010 | `validator/goal_contracts.py` | Module-level `@spec FR-010` | ✅ Implemented | 2026-05-21 |
| FR-011 | `system/anti-drift-block.md`, `system/expectations.md` | `@spec FR-011` anchor in both files | ✅ Implemented | 2026-05-21 |
| FR-012 | `validator/goal_contracts.py` | Module-level `@spec FR-012` | ✅ Implemented | 2026-05-21 |
| FR-013 | `validator/goal_contracts.py` | Module-level `@spec FR-013` | ✅ Implemented | 2026-05-21 |
| FR-014 | `validator/goal_contracts.py` | `@spec FR-014` on `_build_convention_signal_text()` (l.524) | ✅ Implemented | 2026-05-21 |
| FR-015 | `validator/goal_contracts.py` | `@spec FR-015` on `_render_convention_domain()` (l.561) | ✅ Implemented | 2026-05-21 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_goal_contracts.py::test_compile_command_goal_is_reproducible_for_same_inputs` | ✅ Implemented |
| AC-002 | `tests/test_goal_contracts.py::test_compile_command_goal_is_reproducible_for_same_inputs` | ✅ Implemented |
| AC-003 | `tests/test_goal_contracts.py::test_compile_command_goal_is_reproducible_for_same_inputs` | ✅ Implemented |
| AC-004 | `tests/test_goal_contracts.py::test_normalize_goal_flags_is_order_independent_and_preserves_values` | ✅ Implemented |
| AC-005 | `tests/test_goal_contracts_cli.py::test_goal_render_json_outputs_hash_and_canonical_payload` | ✅ Implemented |
| AC-006 | `tests/test_goal_contracts_cli.py::{test_goal_verify_success_uses_expectations_gate,test_goal_verify_drift_exits_one,test_goal_verify_missing_artifact_exits_two}` | ✅ Implemented |
| AC-007 | `tests/test_goal_contracts.py::test_anti_drift_block_documents_shared_goal_protocol` | ✅ Implemented |
| AC-008 | `tests/test_goal_contracts_cli.py::test_goal_render_json_outputs_hash_and_canonical_payload` | ✅ Implemented |
| AC-009 | `tests/test_goal_contracts.py`, `tests/test_goal_contracts_cli.py` | ✅ Implemented |
| AC-010 | `system/expectations.md` | ✅ Implemented |
| AC-011 | `tests/test_goal_contracts.py::test_compile_command_goal_embeds_code_convention_domains` | ✅ Implemented |
| AC-012 | `tests/test_goal_contracts.py::test_compile_command_goal_embeds_code_convention_domains` | ✅ Implemented |
| AC-013 | `tests/test_goal_contracts.py::test_compile_command_goal_adds_design_domain_for_ui_feature` | ✅ Implemented |

## Files Created/Modified

| File | Purpose |
|---|---|
| `validator/goal_contracts.py` | Deterministic command goal compiler and verifier |
| `validator/cli_commands/goal_cmd.py` | `livespec goal render/verify` CLI |
| `validator/cli.py` | Registers the `goal` subcommand |
| `tests/test_goal_contracts.py` | Unit tests for canonical goal compilation |
| `tests/test_goal_contracts_cli.py` | CLI tests for render and verify |
| `system/anti-drift-block.md` | Shared slash-command goal lifecycle protocol |
| `system/expectations.md` | Documents the goal layer on top of expectations |
