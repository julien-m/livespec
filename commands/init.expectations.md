---
command: init
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.init

## 1. Purpose

Initialize LiveSpec in a project through a 3-phase conversational brainstorm.

## 2. Preconditions

- `Project directory exists (any structure).`
- `No existing `.specs/` directory (else use /spec.migrate).`

## 3. Observable Signals

**stdout must_contain:**
- "LiveSpec initialized"
- "`.specs/`"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/`
- `.specs/spec-system.md`
- `.specs/project.md`
- `.specs/constitution.md`
- `.specs/roadmap.md`

**update:**
- `.gitignore`

**optional:**
- `.specs/stacks/_default.md`

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/`
- `.gitignore`

**forbidden changes:**
- `any source files`

**commit expectations:**
- `feat(spec): initialize LiveSpec`

## 6. Produced Artifacts

- path: `.specs/project.md`
  must_contain_sections:
  - "Vision"
  - "Users"
  - "Constraints"

## 7. Exit Codes

| Code | Meaning | Operator action |
|------|---------|-----------------|
| 0    | success | nothing |
| 1    | drift   | inspect report, fix divergence |
| 2    | blocked | restore precondition, retry |

## 8. Outcome Matrix

- **success:** every `must` rule passes, exit_code == 0
- **drift:** at least one `must` rule fails, command exited 0
- **blocked:** precondition missing or artifact missing
- **error:** command itself crashed (exit_code != 0)

## 9. Runtime Profile

- Typical range: 60–600 seconds
- Factors: Brainstorm interactivity, number of clarifying turns, design tool detection

## 10. Post-run Checks

- [ ] `.specs/` directory present at repo root
- [ ] spec-system.md is the canonical version

## 11. Troubleshooting

- **Symptom:** `.specs/` already exists
  **Cause:** previous init
  **Fix:** run /spec.migrate instead

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "LiveSpec initialized"
    - exists: ".specs/spec-system.md"
    - exists: ".specs/project.md"
  may:
    - contains: "stack"
  must_not:
    - contains: "Traceback"
```
