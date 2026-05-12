---
command: plan
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.plan

## 1. Purpose

Generate a technical plan with sequence, state, and ER diagrams.

## 2. Preconditions

- `.specs/features/<feature>/spec.md` exists.

## 3. Observable Signals

**stdout must_contain:**
- "plan.md"
- "<feature>"

**stdout must_not_contain:**
- "Traceback"
- "[DECISION NEEDED]"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/features/<feature>/plan.md`

**update:**
- `.specs/features/<feature>/changelog.md`

**optional:**
- _(none)_

**forbidden:**
- `.specs/features/<feature>/spec.md`

## 5. Git Effects

**expected dirty paths:**
- `.specs/features/<feature>/plan.md`

**forbidden changes:**
- _(none)_

**commit expectations:**
- `plan(<feature>): add plan`

## 6. Produced Artifacts

- path: `.specs/features/<feature>/plan.md`
  must_contain_sections:
  - "Summary"
  - "Technical Context"
  - "Constitution Check"
  - "Implementation Plan"

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

- Typical range: 30–300 seconds
- Factors: Feature complexity, diagram count

## 10. Post-run Checks

- [ ] plan.md contains a sequence + state + ER diagram
- [ ] No [DECISION NEEDED] markers

## 11. Troubleshooting

- **Symptom:** Constitution Check fails
  **Cause:** Spec contradicts constitution
  **Fix:** Revise spec or update constitution

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - exists: ".specs/features/<feature>/plan.md"
    - contains: "plan.md"
  may:
    - contains: "mermaid"
  must_not:
    - contains: "Traceback"
    - contains: "[DECISION NEEDED]"
  when:
    - flag: "--review"
      must:
        - contains: "Plan Review"
```
