---
created: 2026-10-12
feature: 084-bugfix-lane
title: 'Implementation Map: Bugfix Lane'
type: implementation
updated: 2026-10-12
---

# Implementation — Bugfix Lane

> Read [spec](spec.md) and [plan](plan.md). Non-UI feature (CLI + files); no visual baselines.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Bugfix command group](spec.md#fr-001) | `validator/cli_commands/bugfix_cmd.py`, `validator/cli_commands/__init__.py` | `@spec FR-001: Bugfix command group — .specs/features/084-bugfix-lane/spec.md#fr-001` | ✅ Implemented | 2026-10-12 |
| [FR-002: Runner-owned capture](spec.md#fr-002) | `validator/cli_commands/bugfix_cmd.py`, `validator/bugfix/receipts.py` | `@spec FR-002: Runner-owned RED/GREEN capture — .specs/features/084-bugfix-lane/spec.md#fr-002` | ✅ Implemented | 2026-10-12 |
| [FR-003: Owner identification](spec.md#fr-003) | `validator/bugfix/gate.py` | `@spec FR-003: Owner feature identification — .specs/features/084-bugfix-lane/spec.md#fr-003` | ✅ Implemented | 2026-10-12 |
| [FR-004: Protected spec text](spec.md#fr-004) | `validator/bugfix/requirements.py`, `validator/bugfix/gate.py`, `validator/bugfix/diff.py` | `@spec FR-004: Requirement definition extraction, Requirement text unchanged — .specs/features/084-bugfix-lane/spec.md#fr-004` | ✅ Implemented | 2026-10-12 |
| [FR-005: RED/GREEN regression proof](spec.md#fr-005) | `validator/bugfix/receipts.py`, `validator/execution_evidence.py` | `@spec FR-005: Historical RED observation, Regression, identity, order and changed inputs — .specs/features/084-bugfix-lane/spec.md#fr-005` | ✅ Implemented | 2026-10-12 |
| [FR-006: Diff and limits](spec.md#fr-006) | `validator/bugfix/diff.py`, `validator/bugfix/config.py`, `validator/bugfix/gate.py` | `@spec FR-006: Bugfix diff collection, Configurable diff thresholds, Diff confinement — .specs/features/084-bugfix-lane/spec.md#fr-006` | ✅ Implemented | 2026-10-12 |
| [FR-007: Scoped gate](spec.md#fr-007) | `validator/bugfix/gate.py`, `validator/bugfix/models.py` | `@spec FR-007: Scoped gate without whole-feature readiness — .specs/features/084-bugfix-lane/spec.md#fr-007` | ✅ Implemented | 2026-10-12 |
| [FR-008: Cited requirement scope](spec.md#fr-008) | `validator/bugfix/requirements.py` | `@spec FR-008: Cited requirement scope — .specs/features/084-bugfix-lane/spec.md#fr-008` | ✅ Implemented | 2026-10-12 |
| [FR-009: Explicit fallback](spec.md#fr-009) | `validator/bugfix/models.py`, `validator/cli_commands/bugfix_cmd.py` | `@spec FR-009: Explicit fallback output — .specs/features/084-bugfix-lane/spec.md#fr-009` | ✅ Implemented | 2026-10-12 |
| [FR-010: Idempotent record](spec.md#fr-010) | `validator/bugfix/record.py`, `validator/cli_commands/bugfix_cmd.py` | `@spec FR-010: Idempotent bugfix trace — .specs/features/084-bugfix-lane/spec.md#fr-010` | ✅ Implemented | 2026-10-12 |
| [FR-011: Goal integration](spec.md#fr-011) | `validator/goal_inventory.py`, `validator/goal_contract_model.py`, `validator/evidence_policy.py`, `validator/run_requirement_receipts.py`, `.agent-sync/skills/spec-fix/SKILL.md` | `@spec FR-011: Bugfix lane replaces readiness, gap report and feature acceptance — .specs/features/084-bugfix-lane/spec.md#fr-011` | ✅ Implemented | 2026-10-12 |
| [FR-012: Skill and documents](spec.md#fr-012) | `.agent-sync/skills/spec-fix/SKILL.md`, `.agent-sync/skills/spec-fix/expectations.md`, `system/spec-system.md`, `.specs/spec-system.md`, `README.md` | `@spec FR-012: Bugfix lane in spec-fix, in the universal rules, commands — .specs/features/084-bugfix-lane/spec.md#fr-012` | ✅ Implemented | 2026-10-12 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_bugfix_capture.py` | ✅ Pass 2026-10-12 |
| AC-002 | `tests/test_bugfix_capture.py` | ✅ Pass 2026-10-12 |
| AC-003 | `tests/test_bugfix_gate.py` (`test_pre_edit_gate_is_ready_without_any_review`) | ✅ Pass 2026-10-12 |
| AC-004 | `tests/test_bugfix_gate.py` (`test_closing_gate_is_eligible_with_measured_diff`) | ✅ Pass 2026-10-12 |
| AC-005 | `tests/test_bugfix_gate.py` (requirement text, heading bodies, Gherkin) | ✅ Pass 2026-10-12 |
| AC-006 | `tests/test_bugfix_gate.py` (invalid/foreign RED, historical RED) | ✅ Pass 2026-10-12 |
| AC-007 | `tests/test_bugfix_gate.py` (stale GREEN, changed test, test support, order, command, fix outside diff, no regression) | ✅ Pass 2026-10-12 |
| AC-008 | `tests/test_bugfix_gate.py` (limits at base, too large, binary, config exit 3, diff unavailable) | ✅ Pass 2026-10-12 |
| AC-009 | `tests/test_bugfix_gate.py` (`test_owner_not_identified`) | ✅ Pass 2026-10-12 |
| AC-010 | `tests/test_bugfix_gate.py` (cited alone, unknown, ambiguous, unreadable receipt) | ✅ Pass 2026-10-12 |
| AC-011 | `tests/test_bugfix_gate.py` (text output and JSON schema) | ✅ Pass 2026-10-12 |
| AC-012 | `tests/test_bugfix_record.py` | ✅ Pass 2026-10-12 |
| AC-013 | `tests/test_bugfix_goal.py` | ✅ Pass 2026-10-12 |
| AC-014 | `tests/test_bugfix_docs.py` | ✅ Pass 2026-10-12 |

## Files Created/Modified

- `validator/bugfix/` (new): `models.py`, `config.py`, `diff.py`, `requirements.py`, `receipts.py`, `gate.py`, `record.py`.
- `validator/cli_commands/bugfix_cmd.py` (new), `validator/cli_commands/__init__.py` (registration).
- `validator/execution_evidence.py`: `_inspect(..., require_current=True)` keyword for historical RED.
- `validator/goal_inventory.py`, `validator/goal_contract_model.py`: `fix-bugfix` and `fix-readiness` branches.
- `validator/evidence_policy.py`, `validator/run_requirement_receipts.py`: `outcome:passed` proven by a current GREEN observation.
- `.agent-sync/skills/spec-fix/SKILL.md`, `expectations.md`, `system/spec-system.md`, `.specs/spec-system.md`, `README.md`.
- Tests: `tests/bugfix_support.py`, `tests/test_bugfix_{capture,gate,record,goal,docs}.py`.
