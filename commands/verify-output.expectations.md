---
command: verify-output
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.verify-output

## 1. Purpose

Verify a command's latest run artifact against its expectations contract.

## 2. Preconditions

- `commands/<X>.expectations.md` exists (or a project override).
- `.specs/.runs/<X>-*.json` exists.

## 3. Observable Signals

**stdout must_contain:**
- "verify-output"
- "outcome"

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

- Typical range: 1–10 seconds
- Factors: Artifact size (stdout/stderr length)

## 10. Post-run Checks

- [ ] Report mentions outcome=success|drift|blocked|error

## 11. Troubleshooting

- **Symptom:** blocked: no artifact
  **Cause:** Command never ran
  **Fix:** Run the command at least once, then re-verify

## 12. Verify Contract

```yaml
verify:
  must:
    - contains: "outcome"
  may:
    - contains: "PASS"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--json"
      must:
        - contains: '"outcome"'
```
