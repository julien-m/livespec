---
created: 2026-06-27
feature: 071-qe-analysis-native-module
title: "Implementation Map: QE Analysis Native Module"
type: implementation
updated: 2026-06-27
---

# Implementation Map: QE Analysis Native Module (071)

**Status:** Implemented.
**Mode:** Retroactive mapping after runtime implementation. The feature artifacts were created after the code change to repair the missing `/spec-feature` materialization.

## Requirement Mapping

| Req | Behavior | Source File | @spec Anchor | Test |
|---|---|---|---|---|
| FR-001, AC-001 | Native QE system module | `system/qe-analysis.md` | @spec(FR-001) | `tests/test_goal_contracts.py` |
| FR-002, AC-002, AC-003, AC-004 | Embed native QE for affected commands | `validator/goal_contracts.py` | @spec(FR-002) | `test_spec_plan_goal_embeds_native_qe_without_user_config`, parameterized injection test |
| FR-003, AC-005 | Inject `qe.analysis` before archive completion | `validator/goal_contracts.py` | @spec(FR-003) | `test_native_qe_analysis_task_is_injected_for_quality_commands` |
| FR-004, FR-005, AC-006, AC-007 | Validate structured QE evidence and reject generic claims | `validator/goal_contracts.py` | @spec(FR-004), @spec(FR-005) | generic rejection and structured acceptance tests |
| FR-006, AC-009, AC-010 | Reject skill/config substitutes | `validator/goal_contracts.py` | @spec(FR-006) | `test_goal_prove_rejects_qe_analysis_substitutes` and content assertions |
| FR-007, AC-008 | Keep user hooks additive | `validator/goal_contracts.py`, `validator/hook_resolver.py` | @spec(FR-007) | `test_native_qe_is_primary_and_user_hooks_are_additive` |
| FR-008, FR-009, FR-010, AC-011 | Per-command QE mapping in command docs | `.agent-sync/skills/spec-specify/`, `.agent-sync/skills/spec-plan/`, `.agent-sync/skills/spec-test/` | @spec(FR-008), @spec(FR-009), @spec(FR-010) | command audit |
| FR-011, AC-012 | System docs and README describe native QE | `system/spec-system.md`, `system/integrations.md`, `README.md` | @spec(FR-011) | command audit and docs inspection |

## AC Coverage

| AC | Covered by | Status |
|---|---|---|
| AC-001 | `system/qe-analysis.md` | Implemented |
| AC-002 | `spec-specify` goal render injection path | Implemented |
| AC-003 | clean-HOME `spec-plan` render proof | Implemented |
| AC-004 | `spec-test` goal render injection path | Implemented |
| AC-005 | `QE_ANALYSIS_REQUIRED_EVIDENCE` | Implemented |
| AC-006 | generic QE proof rejection | Implemented |
| AC-007 | structured QE proof acceptance | Implemented |
| AC-008 | additive hook test | Implemented |
| AC-009 | no global QE skill dependency | Implemented |
| AC-010 | no user config dependency | Implemented |
| AC-011 | command skills and expectations updates | Implemented |
| AC-012 | system docs and README updates | Implemented |

## Success Criteria Verification

| SC | Verification |
|---|---|
| SC-001 | clean-HOME `livespec goal render spec-plan --flags "" --save` contains native QE and `qe.analysis` |
| SC-002 | parameterized test covers `spec-specify`, `spec-plan`, `spec-test` |
| SC-003 | `goal prove` generic rejection and structured acceptance verified |
| SC-004 | hook-additive test verifies hooks are optional extensions |
| SC-005 | pytest, ruff, targeted type check, `.specs` validation, command audit all pass |

## Files Created / Modified

- `system/qe-analysis.md` - native QE module.
- `validator/goal_contracts.py` - native QE payload, task injection, and proof validation.
- `tests/test_goal_contracts.py` - render/prove regression coverage.
- `.agent-sync/skills/spec-specify/SKILL.md` and `expectations.md` - specify mapping.
- `.agent-sync/skills/spec-plan/SKILL.md` and `expectations.md` - plan mapping.
- `.agent-sync/skills/spec-test/SKILL.md` and `expectations.md` - test mapping.
- `system/spec-system.md`, `system/integrations.md`, `README.md` - documentation.
- `.specs/features/071-qe-analysis-native-module/` - repaired feature artifact set.

## Verification

- `python3 -m pytest tests/test_goal_contracts.py -q` - 105 passed.
- `ruff check validator/goal_contracts.py tests/test_goal_contracts.py` - pass.
- `ruff format --check validator/goal_contracts.py tests/test_goal_contracts.py` - pass.
- `pyright validator/goal_contracts.py tests/test_goal_contracts.py` - 0 errors.
- `mypy .` - attempted; blocked by pre-existing missing third-party stubs/imports for `yaml`, `frontmatter`, and `claude_agent_sdk`, outside this feature diff.
- `livespec validate .specs --format json` - 394 files, 0 errors, 0 warnings after feature folder repair.
- `livespec command-audit --json` - 23 commands / 0 failed.
- clean-HOME render/prove runtime proof - generic QE proof rejected, structured QE proof accepted.
