# Implementation — Conventions Blocking Pipeline

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | [`validator/run_receipts.py`](../../../validator/run_receipts.py) | module receipt key map | Implemented | 2026-06-13 |
| FR-002 | [`validator/run_receipts.py`](../../../validator/run_receipts.py), [`validator/goal_contracts.py`](../../../validator/goal_contracts.py) | conventions receipt verifier calls | Implemented | 2026-06-13 |
| FR-003 | [`validator/verify_output.py`](../../../validator/verify_output.py), [`validator/run_artifacts.py`](../../../validator/run_artifacts.py) | receipt_verdict outcome path | Implemented | 2026-06-13 |
| FR-004 | [`validator/verify_output.py`](../../../validator/verify_output.py), [`validator/expectations.py`](../../../validator/expectations.py) | receipt_verdict parser/evaluator | Implemented | 2026-06-13 |
| FR-005 | [`validator/verify_output.py`](../../../validator/verify_output.py) | gates-absent skip branch | Implemented | 2026-06-13 |
| FR-006 | [`validator/goal_contracts.py`](../../../validator/goal_contracts.py) | conventions_receipt_path proof | Implemented | 2026-06-13 |
| FR-007 | [`.agent-sync/skills/spec-implement/SKILL.md`](../../../.agent-sync/skills/spec-implement/SKILL.md), [`.agent-sync/skills/spec-test/SKILL.md`](../../../.agent-sync/skills/spec-test/SKILL.md), [`.agent-sync/skills/spec-fix/SKILL.md`](../../../.agent-sync/skills/spec-fix/SKILL.md), [`.agent-sync/skills/spec-*/expectations.md`](../../../.agent-sync/skills/spec-implement/expectations.md) | command docs contract | Implemented | 2026-06-13 |
| FR-008 | [`.agent-sync/agents/livespec-verifier/prompt.md`](../../../.agent-sync/agents/livespec-verifier/prompt.md), [`.agent-sync/agents/livespec-supervisor/prompt.md`](../../../.agent-sync/agents/livespec-supervisor/prompt.md) | prompt hard gate text | Implemented | 2026-06-13 |
| FR-009 | [`validator/coherence/rules/r7_conventions_gates.py`](../../../validator/coherence/rules/r7_conventions_gates.py), [`validator/coherence/rules/__init__.py`](../../../validator/coherence/rules/__init__.py) | R7 registration | Implemented | 2026-06-13 |
| FR-010 | [`validator/conventions_diffguard.py`](../../../validator/conventions_diffguard.py) | supervisor lock helpers | Implemented | 2026-06-13 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | [`tests/test_run_receipts.py`](../../../tests/test_run_receipts.py) | Implemented |
| AC-002 | [`tests/test_run_artifact.py`](../../../tests/test_run_artifact.py) | Implemented |
| AC-003 | [`tests/test_verify_output.py`](../../../tests/test_verify_output.py) | Implemented |
| AC-004 | [`tests/test_goal_contracts.py`](../../../tests/test_goal_contracts.py) | Implemented |
| AC-005 | [`tests/test_goal_contracts.py`](../../../tests/test_goal_contracts.py) | Implemented |
| AC-006 | [`tests/test_conventions_pipeline_docs.py`](../../../tests/test_conventions_pipeline_docs.py) | Implemented |
| AC-007 | [`tests/test_conventions_pipeline_docs.py`](../../../tests/test_conventions_pipeline_docs.py) | Implemented |
| AC-008 | [`tests/test_conventions_pipeline_docs.py`](../../../tests/test_conventions_pipeline_docs.py) | Implemented |
| AC-009 | [`tests/test_conventions_pipeline_docs.py`](../../../tests/test_conventions_pipeline_docs.py) | Implemented |
| AC-010 | [`tests/test_coherence_rules.py`](../../../tests/test_coherence_rules.py) | Implemented |
| AC-011 | [`tests/test_coherence_rules.py`](../../../tests/test_coherence_rules.py) | Implemented |
| AC-012 | [`tests/test_coherence_rules.py`](../../../tests/test_coherence_rules.py) | Implemented |
| AC-013 | [`tests/test_conventions_diffguard.py`](../../../tests/test_conventions_diffguard.py) | Implemented |
| AC-014 | [`tests/test_conventions_diffguard.py`](../../../tests/test_conventions_diffguard.py) | Implemented |
| AC-015 | [`tests/test_conventions_diffguard.py`](../../../tests/test_conventions_diffguard.py) | Implemented |

## Files Created/Modified

- Created [`validator/coherence/rules/r7_conventions_gates.py`](../../../validator/coherence/rules/r7_conventions_gates.py) for R7 coherence checks.
- Created [`validator/conventions_diffguard.py`](../../../validator/conventions_diffguard.py) for supervisor locks.
- Created [`tests/test_run_receipts.py`](../../../tests/test_run_receipts.py), [`tests/test_conventions_diffguard.py`](../../../tests/test_conventions_diffguard.py), and [`tests/test_conventions_pipeline_docs.py`](../../../tests/test_conventions_pipeline_docs.py).
- Updated receipt, verify-output, expectations, goal contract, command skill, agent prompt, and coherence registry files.

## Verification

- Targeted tests: 22 passed.
- Full tests: `2079 passed, 40 skipped, 194 warnings`.
- Ruff: `ruff check .` passed.
- Format: `ruff format --check .` passed.
- Pyright: `0 errors, 0 warnings, 0 informations`.
