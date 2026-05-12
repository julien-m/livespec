---
command: preflight
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.preflight

## 1. Purpose

Verify tooling, auth, and credentials before autonomous work.

## 2. Preconditions

- `.specs/preflight.md` exists with a manifest.

## 3. Observable Signals

**stdout must_contain:**
- "preflight"
- "ok"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/preflight-report.md`

**update:**
- `.specs/preflight.md`

**optional:**
- _(none)_

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/preflight-report.md`

**forbidden changes:**
- _(none)_

**commit expectations:**
- _(none)_

## 6. Produced Artifacts

- path: `.specs/preflight-report.md`
  must_contain_sections:
  - "Tools"
  - "Status"

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

- Typical range: 5–120 seconds
- Factors: Number of items in the manifest

## 10. Post-run Checks

- [ ] Report lists every tool with ok/missing/auto-installable

## 11. Troubleshooting

- **Symptom:** All missing
  **Cause:** Empty PATH or wrong shell
  **Fix:** Source the shell rc and retry

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "preflight"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--fix"
      must:
        - contains: "installed"
```
