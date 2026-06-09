---
title: "Integrate Penflow Primary UI Contract Implementation"
feature: "051-integrate-penflow-primary-ui-contract"
---

# Implementation — 051-integrate-penflow-primary-ui-contract

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `validator/penflow_contract.py` | Module-level helper doc | ✅ Implemented | 2026-05-21 |
| FR-002 | `validator/cli_commands/penflow_contract_cmd.py`, `validator/cli_commands/__init__.py` | CLI module doc | ✅ Implemented | 2026-05-26 |
| FR-003 | `.agent-sync/skills/spec-init/SKILL.md` | Step 3.5.5 | ✅ Implemented | 2026-05-26 |
| FR-004 | `.agent-sync/skills/spec-specify/SKILL.md` | Step 1.8 | ✅ Implemented | 2026-05-21 |
| FR-005 | `.agent-sync/skills/spec-plan/SKILL.md`, `.agent-sync/skills/spec-implement/SKILL.md` | Step 2.6 / Phase 1 | ✅ Implemented | 2026-05-21 |
| FR-006 | `.agent-sync/skills/spec-test/SKILL.md`, `.agent-sync/skills/spec-check/SKILL.md`, `system/testing/penflow-contract.md` | Phase 4.5.P / Step 8.P | ✅ Implemented | 2026-05-21 |
| FR-007 | `.agent-sync/skills/spec-test/SKILL.md`, `.agent-sync/skills/spec-check/SKILL.md`, README | Visual gate language | ✅ Implemented | 2026-05-21 |
| FR-008 | `docs/superpowers/specs/2026-04-18-legacy-test-merge-design.md` | Audit table | ✅ Implemented | 2026-05-21 |
| FR-009 | `validator/penflow_contract.py`, `validator/cli_commands/penflow_contract_cmd.py` | Runtime comparison status | ✅ Implemented | 2026-05-21 |
| FR-010 | `validator/penflow_contract.py`, `validator/cli_commands/penflow_contract_cmd.py` | Explicit source bootstrap | ✅ Implemented | 2026-05-26 |
| FR-011 | `validator/penflow_contract.py` | Duplicate Penflow source scan | ✅ Implemented | 2026-05-26 |
| FR-012 | `system/testing/penflow-contract.md`, `.agent-sync/skills/spec-feature/SKILL.md`, `.agent-sync/skills/spec-test/SKILL.md`, `.agent-sync/skills/spec-init/SKILL.md` | Single canonical Penflow source contract | ✅ Implemented | 2026-05-26 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_penflow_contract_command_contract.py` | ✅ Implemented |
| AC-002 | `tests/test_penflow_contract.py`, `tests/test_penflow_contract_command_contract.py` | ✅ Implemented |
| AC-003 | `tests/test_penflow_contract_command_contract.py` | ✅ Implemented |
| AC-004 | `tests/test_penflow_contract_command_contract.py` | ✅ Implemented |
| AC-005 | `tests/test_penflow_contract_command_contract.py` | ✅ Implemented |
| AC-006 | `tests/test_penflow_contract_command_contract.py` | ✅ Implemented |
| AC-007 | `tests/test_penflow_contract_command_contract.py` | ✅ Implemented |
| AC-008 | `tests/test_penflow_contract_command_contract.py` | ✅ Implemented |
| AC-009 | `docs/superpowers/specs/2026-04-18-legacy-test-merge-design.md` | ✅ Implemented |
| AC-010 | `tests/test_penflow_contract.py`, `tests/test_penflow_contract_command_contract.py` | ✅ Implemented |
| AC-011 | `tests/test_penflow_contract.py`, `tests/test_penflow_contract_command_contract.py` | ✅ Implemented |
| AC-012 | `tests/test_penflow_contract.py`, `tests/test_penflow_contract_command_contract.py` | ✅ Implemented |
| AC-013 | `tests/test_penflow_contract.py`, `tests/test_penflow_contract_command_contract.py` | ✅ Implemented |

## Files Created/Modified

| File | Purpose |
|---|---|
| `validator/penflow_contract.py` | Root Penflow workspace status and bootstrap helpers |
| `validator/cli_commands/penflow_contract_cmd.py` | `livespec penflow-contract status/bootstrap` CLI |
| `validator/cli_commands/__init__.py` | Registers the CLI group |
| `system/testing/penflow-contract.md` | Canonical Penflow contract gate workflow |
| `.agent-sync/skills/spec-init/SKILL.md` | Documents `.brainstorm/penflow/` bootstrap |
| `.agent-sync/skills/spec-specify/SKILL.md` | Documents semantic tree ID resolution |
| `.agent-sync/skills/spec-plan/SKILL.md` | Documents `code-ir.json` planning input |
| `.agent-sync/skills/spec-implement/SKILL.md` | Documents Penflow ID/context preservation |
| `.agent-sync/skills/spec-test/SKILL.md` | Documents blocking Penflow compare gate |
| `.agent-sync/skills/spec-check/SKILL.md` | Documents Penflow contract status reporting |
| `tests/test_penflow_contract.py` | Helper and CLI tests |
| `tests/test_penflow_contract_command_contract.py` | Command documentation contract tests |
| `README.md` | Public project structure and workflow update |
| `.specs/spec-system.md`, `system/spec-system.md` | Document root `penflow/ui.pen` as the only `.pen` source |
