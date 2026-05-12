---
command: play-coverage
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.play-coverage

## 1. Purpose

Open the spec coverage playground with live grep data.

## 2. Preconditions

- `.specs/` exists.
- `A browser available (or `--no-open`).`

## 3. Observable Signals

**stdout must_contain:**
- "playground"
- "coverage"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `playground/coverage/`

**update:**
- `playground/coverage/data.json`

**optional:**
- _(none)_

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `playground/coverage/`

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

- Typical range: 5–60 seconds
- Factors: Repo size, anchor count

## 10. Post-run Checks

- [ ] data.json contains at least one feature entry

## 11. Troubleshooting

- **Symptom:** Browser not opened
  **Cause:** Headless env
  **Fix:** Pass --no-open and inspect manually

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "playground"
  must_not:
    - contains: "Traceback"
```
