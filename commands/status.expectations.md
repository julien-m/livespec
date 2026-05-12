---
command: status
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.status

## 1. Purpose

Display a factual status overview of the roadmap and features (read-only).

## 2. Preconditions

- `.specs/project.md` exists.

## 3. Observable Signals

**stdout must_contain:**
- "LiveSpec"
- "features"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- _(none)_

**update:**
- _(none)_

**optional:**
- _(none)_

**forbidden:**
- `src/`
- `.specs/`

## 5. Git Effects

**expected dirty paths:**
- _(none)_

**forbidden changes:**
- `any`

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

- Typical range: 1–30 seconds
- Factors: Feature count, roadmap size

## 10. Post-run Checks

- [ ] Output mentions roadmap tiers and feature statuses

## 11. Troubleshooting

- **Symptom:** Empty output
  **Cause:** No features
  **Fix:** Run /spec.specify first

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "features"
  may:
    - contains: "MVP"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--json"
      must:
        - contains: '"features"'
```
