# Implementation: Goal Tasks Replay Required Conventions Per Step

- **Feature:** 053-goal-tasks-replay-required-conventions-per-step
- **Status:** Implemented
- **Last Verified:** 2026-06-01

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `validator/goal_contracts.py` | `@spec FR-001: Per-task convention payload` | ✅ Implemented | 2026-06-01 |
| FR-002 | `validator/goal_contracts.py` | `@spec FR-002: Convention proof fields` | ✅ Implemented | 2026-06-01 |
| FR-003 | `validator/goal_contracts.py` | `@spec FR-003: Validate convention evidence` | ✅ Implemented | 2026-06-01 |
| FR-004 | `validator/goal_contracts.py` | `@spec FR-004: Convention repair actions` | ✅ Implemented | 2026-06-01 |
| FR-005 | `validator/goal_contracts.py` | `@spec FR-005: Render task-level convention replay` | ✅ Implemented | 2026-06-01 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_goal_contracts.py::test_rendered_goal_tasks_replay_required_conventions` | ✅ Implemented |
| AC-002 | `tests/test_goal_contracts.py::test_rendered_goal_tasks_replay_required_conventions` | ✅ Implemented |
| AC-003 | `tests/test_goal_contracts.py::test_goal_prove_rejects_missing_convention_evidence` | ✅ Implemented |
| AC-004 | `tests/test_goal_contracts.py::test_goal_prove_rejects_missing_convention_evidence` | ✅ Implemented |
| AC-005 | `tests/test_goal_contracts.py::test_goal_prove_rejects_missing_convention_evidence` | ✅ Implemented |
| AC-006 | `tests/test_goal_contracts.py::test_goal_prove_accepts_matching_convention_evidence` | ✅ Implemented |
| AC-007 | `tests/test_goal_contracts.py::test_rendered_goal_tasks_replay_required_conventions` | ✅ Implemented |
| AC-008 | `tests/test_goal_contracts.py::test_rendered_goal_tasks_replay_required_conventions` | ✅ Implemented |

## Files Created/Modified

- `validator/goal_contracts.py` — goal contract task construction and proof validation.
- `tests/test_goal_contracts.py` — convention replay and evidence gate tests.
- `tests/test_agent_sync_layout.py` — registry command-count drift fixed for the current 21-command surface.
- `tests/test_command_registry.py` — builtin command discovery expectations fixed for `spec-refresh-from-brainstorm`.
