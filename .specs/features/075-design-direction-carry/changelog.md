# Changelog: Design Direction Carry (075)

## 2026-07-04 — [Feature]: Design direction carry

- **Type:** Feature
- **Spec modified:** Yes (new feature spec, plan, progress, implementation map)
- **Code modified:** system/templates/spec-template.md, .agent-sync/skills/spec-specify/SKILL.md, .agent-sync/skills/spec-init/SKILL.md, .specs/spec-system.md, tests/test_design_direction_carry.py
- **AC impacted:** AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-007
- **Author:** tool-worker

### Highlights

- Future UI specs can carry an optional `**Design direction:**` line from Penflow, project theme, or user default.
- `/spec-specify` documents clean omission when no source exists and prohibits placeholders.
- LiveSpec judgement commands remain isolated from the direction line; it is implementation context only.
