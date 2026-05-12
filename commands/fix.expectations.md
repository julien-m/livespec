---
command: fix
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.fix

## 1. Purpose

Fix implementation gaps from /spec.check — functional and visual corrections.

## 2. Preconditions

- `A recent `checks/<date>-check.md` exists with non-empty findings.`

## 3. Observable Signals

**stdout must_contain:**
- "fix"
- "applied"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- _(none)_

**update:**
- `src/`
- `.specs/features/<feature>/implementation.md`

**optional:**
- _(none)_

**forbidden:**
- `.specs/features/<feature>/spec.md`

## 5. Git Effects

**expected dirty paths:**
- `src/`

**forbidden changes:**
- `.specs/features/<feature>/spec.md`

**commit expectations:**
- `fix(<feature>): close gap`

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

- Typical range: 30–900 seconds
- Factors: Number of findings, fix complexity

## 10. Post-run Checks

- [ ] Re-running /spec.check shows the gap closed

## 11. Troubleshooting

- **Symptom:** No findings to act on
  **Cause:** Stale check
  **Fix:** Re-run /spec.check first

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "applied"
  must_not:
    - contains: "Traceback"
```
