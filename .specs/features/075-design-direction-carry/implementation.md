---
created: 2026-07-04
feature: 075-design-direction-carry
title: "Implementation Map: Design Direction Carry"
type: implementation
updated: 2026-07-04
---

# Implementation Map: Design Direction Carry (075)

**Status:** Implemented pending final gates.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | [spec-template.md](../../../system/templates/spec-template.md) | @spec FR-001 | ✅ Implemented | 2026-07-04 |
| FR-002 | [SKILL.md](../../../.agent-sync/skills/spec-specify/SKILL.md) | @spec FR-002 | ✅ Implemented | 2026-07-04 |
| FR-003 | [SKILL.md](../../../.agent-sync/skills/spec-init/SKILL.md) | @spec FR-003 | ✅ Implemented | 2026-07-04 |
| FR-004 | [SKILL.md](../../../.agent-sync/skills/spec-init/SKILL.md) | @spec FR-004 | ✅ Implemented | 2026-07-04 |
| FR-005 | [spec-system.md](../../spec-system.md) | @spec FR-005 | ✅ Implemented | 2026-07-04 |
| FR-006 | [test_design_direction_carry.py](../../../tests/test_design_direction_carry.py) | @spec FR-006 | ✅ Implemented | 2026-07-04 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | [test_design_direction_carry.py](../../../tests/test_design_direction_carry.py) | Implemented |
| AC-002 | [test_design_direction_carry.py](../../../tests/test_design_direction_carry.py) | Implemented |
| AC-003 | [test_design_direction_carry.py](../../../tests/test_design_direction_carry.py) | Implemented |
| AC-004 | [test_design_direction_carry.py](../../../tests/test_design_direction_carry.py) | Implemented |
| AC-005 | [test_design_direction_carry.py](../../../tests/test_design_direction_carry.py) | Implemented |
| AC-006 | [test_design_direction_carry.py](../../../tests/test_design_direction_carry.py) | Implemented |
| AC-007 | [test_design_direction_carry.py](../../../tests/test_design_direction_carry.py) | Implemented |

## Manual Verification Transcripts

| Check | Evidence | Status |
|---|---|---|
| V11 no source degradation | [2026-07-04-design-direction-transcripts.md](checks/2026-07-04-design-direction-transcripts.md) | ✅ Verified |
| V12 default direction carry | [2026-07-04-design-direction-transcripts.md](checks/2026-07-04-design-direction-transcripts.md) | ✅ Verified |

## Files Created/Modified

**Created:** `.specs/features/075-design-direction-carry/*`, `.specs/features/075-design-direction-carry/checks/2026-07-04-design-direction-transcripts.md`, `tests/test_design_direction_carry.py`.

**Modified:** `system/templates/spec-template.md`, `.agent-sync/skills/spec-specify/SKILL.md`, `.agent-sync/skills/spec-specify/expectations.md`, `.agent-sync/skills/spec-init/SKILL.md`, `.agent-sync/skills/spec-init/expectations.md`, `.specs/spec-system.md`, `.specs/README.md`, `.specs/roadmap.md`, `.specs/changelog.md`.

**Numbering note:** The upstream plan targeted 074 conditionally. This worktree already contained `074-agent-device-proof-adapter`, so the feature was created as 075.
