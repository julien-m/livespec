---
command: test
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.test

## 1. Purpose

Audit test coverage, generate missing tests, execute the suite, and verify visual fidelity.

## 2. Preconditions

- `.specs/features/<feature>/spec.md` exists.
- `A test driver is configured (`.specs/testing/`).`

## 3. Observable Signals

**stdout must_contain:**
- "passed"
- "test"

**stdout must_not_contain:**
- "Traceback"
- "ERROR collecting"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/features/<feature>/checks/<date>-test.md`

**update:**
- _(none)_

**optional:**
- `test-results/`

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/features/<feature>/checks/`

**forbidden changes:**
- _(none)_

**commit expectations:**
- _(none)_

## 6. Produced Artifacts

- _(none)_

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

- Typical range: 30–1200 seconds
- Factors: Suite size, parallel workers, visual diff cost

## 10. Post-run Checks

- [ ] Coverage report present in checks/
- [ ] Suite exits 0

## 11. Troubleshooting

- **Symptom:** No tests collected
  **Cause:** Missing driver
  **Fix:** Run /spec.preflight or /spec.driver list

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "passed"
  may:
    - contains: "coverage"
  must_not:
    - contains: "Traceback"
    - contains: "ERROR collecting"
  when:
    - flag: "--visual"
      must:
        - contains: "Visual baselines"
```
