---
command: implement
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.implement

## 1. Purpose

Auto-implement a feature from its plan, write tests, and map FR/AC to @spec anchors.

## 2. Preconditions

- `.specs/features/<feature>/plan.md` exists.
- `Branch `feature/<feature>` is checked out.`

## 3. Observable Signals

**stdout must_contain:**
- "PHASE_RESULT"
- "implement"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/features/<feature>/progress.md`
- `.specs/features/<feature>/implementation.md`

**update:**
- `.specs/features/<feature>/changelog.md`
- `.specs/changelog.md`

**optional:**
- _(none)_

**forbidden:**
- `.specs/features/<feature>/spec.md`

## 5. Git Effects

**expected dirty paths:**
- `src/`
- `.specs/features/<feature>/`

**forbidden changes:**
- _(none)_

**commit expectations:**
- `feat(<feature>): ...`

## 6. Produced Artifacts

- path: `.specs/features/<feature>/implementation.md`
  must_contain_sections:
  - "FR mapping"
  - "AC mapping"

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

- Typical range: 60–1800 seconds
- Factors: Step count, file count, test suite size

## 10. Post-run Checks

- [ ] progress.md fully checked off
- [ ] implementation.md maps every FR/AC

## 11. Troubleshooting

- **Symptom:** Blocked step
  **Cause:** Missing tool
  **Fix:** Run /spec.preflight

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "PHASE_RESULT"
    - exists: ".specs/features/<feature>/progress.md"
  may:
    - contains: "tests passed"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--resume"
      must:
        - contains: "Resuming"
```
