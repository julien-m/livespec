---
title: "Deterministic Command Goal Contracts Implementation"
feature: "052-deterministic-command-goal-contracts"
---

# Implementation — 052-deterministic-command-goal-contracts

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `validator/goal_contracts.py` | Module-level `@spec FR-001` | ✅ Implemented | 2026-05-23 |
| FR-002 | `validator/goal_contracts.py` | Module-level `@spec FR-002` | ✅ Implemented | 2026-05-21 |
| FR-003 | `validator/goal_contracts.py` | Module-level `@spec FR-003` | ✅ Implemented | 2026-05-21 |
| FR-004 | `validator/goal_contracts.py` | Module-level `@spec FR-004` | ✅ Implemented | 2026-05-21 |
| FR-005 | `validator/goal_contracts.py` | Module-level `@spec FR-005` | ✅ Implemented | 2026-05-21 |
| FR-006 | `validator/goal_contracts.py` | Module-level `@spec FR-006` | ✅ Implemented | 2026-05-21 |
| FR-007 | `validator/goal_contracts.py` | Module-level `@spec FR-007` | ✅ Implemented | 2026-05-21 |
| FR-008 | `validator/cli_commands/goal_cmd.py`, `validator/cli.py` | CLI module `@spec FR-008` | ✅ Implemented | 2026-05-23 |
| FR-009 | `validator/cli_commands/goal_cmd.py`, `validator/goal_contracts.py` | CLI module `@spec FR-009` | ✅ Implemented | 2026-05-23 |
| FR-010 | `validator/cli_commands/goal_cmd.py`, `validator/goal_contracts.py` | CLI module `@spec FR-010` | ✅ Implemented | 2026-05-23 |
| FR-011 | `system/anti-drift-block.md`, `system/expectations.md`, all `.agent-sync/skills/spec-*/SKILL.md` | `@spec FR-011` in system docs + explicit **Read** directive in every SKILL.md | ✅ Implemented | 2026-05-23 |
| FR-012 | `validator/goal_contracts.py` | Module-level `@spec FR-012` | ✅ Implemented | 2026-05-21 |
| FR-013 | `validator/goal_contracts.py` | Module-level `@spec FR-013` | ✅ Implemented | 2026-05-21 |
| FR-014 | `validator/goal_contracts.py` | `@spec FR-014` on `_build_convention_signal_text()` (l.524) | ✅ Implemented | 2026-05-21 |
| FR-015 | `validator/goal_contracts.py` | `@spec FR-015` on `_render_convention_domain()` (l.561) | ✅ Implemented | 2026-05-21 |
| FR-016 | `validator/goal_contracts.py`, `validator/cli_commands/goal_cmd.py` | `render_goal_contract_file()`, `render_goal_state_file()`, `render_cmd()` | ✅ Implemented | 2026-05-23 |
| FR-017 | `validator/goal_contracts.py` | `_build_goal_tasks()` proof metadata + `render_goal_contract_file()` top-level worker guard | ✅ Implemented | 2026-05-23 |
| FR-018 | `validator/goal_contracts.py`, `validator/visual_evidence.py`, `validator/visual_gate.py`, `validator/cli_commands/visual_gate_cmd.py`, `.agent-sync/skills/spec-{check,fix,test,implement,feature}/SKILL.md` | `_validate_visual_receipt_evidence()`, `verify_visual_receipt()`, `certify_visual_evidence()`, receipt-bound `visual-gate validate --feature --command --target --receipt` | ✅ Implemented | 2026-05-23 |
| FR-019 | `validator/goal_contracts.py`, `validator/command_audit.py`, `.agent-sync/skills/spec-{check,fix,feature,implement,ship,refine,stack}/SKILL.md`, `system/anti-drift-block.md`, `system/integrations.md` | `_validate_internal_subagent_context_guard()` + `internal_subagent_workdir` audit check | ✅ Implemented | 2026-05-23 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_goal_contracts.py::test_compile_command_goal_is_reproducible_for_same_inputs` | ✅ Implemented |
| AC-002 | `tests/test_goal_contracts.py::test_compile_command_goal_is_reproducible_for_same_inputs` | ✅ Implemented |
| AC-003 | `tests/test_goal_contracts.py::test_compile_command_goal_is_reproducible_for_same_inputs` | ✅ Implemented |
| AC-004 | `tests/test_goal_contracts.py::test_normalize_goal_flags_is_order_independent_and_preserves_values` | ✅ Implemented |
| AC-005 | `tests/test_goal_contracts.py::{test_render_goal_contract_and_state_replace_markdown_task_file,test_goal_render_save_writes_contract_and_state_files}` | ✅ Implemented |
| AC-006 | `tests/test_goal_contracts.py::{test_goal_prove_rejects_missing_visual_design_fidelity_evidence,test_goal_prove_accepts_visual_design_fidelity_receipt}` | ✅ Implemented |
| AC-007 | `tests/test_goal_contracts.py::test_anti_drift_block_documents_shared_goal_protocol` | ✅ Implemented |
| AC-008 | `tests/test_goal_contracts_cli.py::test_goal_render_json_outputs_hash_and_canonical_payload` | ✅ Implemented |
| AC-009 | `tests/test_goal_contracts.py`, `tests/test_goal_contracts_cli.py` | ✅ Implemented |
| AC-010 | `system/expectations.md` | ✅ Implemented |
| AC-011 | `tests/test_goal_contracts.py::test_compile_command_goal_embeds_code_convention_domains` | ✅ Implemented |
| AC-012 | `tests/test_goal_contracts.py::test_compile_command_goal_embeds_code_convention_domains` | ✅ Implemented |
| AC-013 | `tests/test_goal_contracts.py::test_compile_command_goal_adds_design_domain_for_ui_feature` | ✅ Implemented |
| AC-014 | `tests/test_goal_contracts.py::test_render_goal_contract_and_state_replace_markdown_task_file` | ✅ Implemented |
| AC-015 | `tests/test_goal_contracts.py::{test_render_goal_contract_and_state_replace_markdown_task_file,test_goal_prove_rejects_missing_visual_design_fidelity_evidence}` | ✅ Implemented |
| AC-016 | `tests/test_goal_contracts.py::{test_spec_check_design_fidelity_contract_rejects_normalized_json_substitute,test_goal_prove_rejects_legacy_visual_design_fidelity_payload,test_goal_prove_accepts_visual_design_fidelity_receipt}`, `tests/test_visual_evidence.py`, `tests/test_visual_gate_receipts.py`, `tests/test_visual_implementation_gate.py::test_visual_command_skills_require_oracle_receipts` | ✅ Implemented |
| AC-017 | `tests/test_goal_contracts.py::test_compile_command_goal_rejects_subagent_without_project_root_cwd_guard`, `tests/test_command_audit_cli.py::test_command_audit_fails_subagent_internal_command_without_workdir_guard` | ✅ Implemented |

## Files Created/Modified

| File | Purpose |
|---|---|
| `validator/goal_contracts.py` | Deterministic command goal compiler, contract/state renderer, and task proof validator |
| `validator/visual_evidence.py` | Deterministic PNG diff oracle and tamper-checked visual receipt verifier |
| `validator/visual_gate.py` | Visual gate receipt certification and receipt-required validation for VISUAL features |
| `validator/cli_commands/visual_gate_cmd.py` | `livespec visual-gate certify` and receipt-bound `validate --feature --command --target --receipt` CLI |
| `validator/cli_commands/goal_cmd.py` | `livespec goal render/prove/status` CLI |
| `validator/cli.py` | Registers the `goal` subcommand |
| `tests/test_goal_contracts.py` | Unit tests for canonical goal compilation |
| `tests/test_visual_evidence.py` | Unit tests for visual receipts, PNG hash/diff verification, and tamper rejection |
| `tests/test_visual_gate_receipts.py` | CLI and gate tests for `certify`, receipt-bound `validate --receipt`, and missing-receipt blocking |
| `tests/test_command_audit_cli.py` | Command audit regression for missing internal subagent workdir guard |
| `system/anti-drift-block.md` | Shared slash-command goal lifecycle protocol |
| `system/integrations.md` | Chained subagent docs updated with project root/cwd propagation |
| `system/expectations.md` | Documents the goal layer on top of expectations |
| `.agent-sync/skills/spec-*/SKILL.md` | Command startup protocol updated to contract/state/prove |
| `.agent-sync/skills/spec-{check,fix,feature,implement,ship,refine,stack}/SKILL.md` | Internal Command Invocation subagent rows now require project_root/cwd propagation |
| `.agent-sync/skills/spec-status/SKILL.md`, `.agent-sync/skills/spec-explain/SKILL.md` | Machine-readable Goal Lock execution tasks added |
