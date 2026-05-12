---
command: migrate
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.migrate

## 1. Purpose

Upgrade a LiveSpec project to the latest version by running pending migrations.

## 2. Preconditions

- `.specs/` directory exists with a previous LiveSpec version.

## 3. Observable Signals

**stdout must_contain:**
- "migration"
- "complete"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- _(none)_

**update:**
- `.specs/spec-system.md`

**optional:**
- `.specs/migrations.log`

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/`

**forbidden changes:**
- `unrelated paths`

**commit expectations:**
- `chore(spec): migrate to <version>`

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

- Typical range: 5–120 seconds
- Factors: Number of pending migrations and project size

## 10. Post-run Checks

- [ ] spec-system.md version matches LiveSpec checkout
- [ ] No legacy file shape remains

## 11. Troubleshooting

- **Symptom:** Conflicting custom edits
  **Cause:** User changed templated files
  **Fix:** Resolve manually then re-run

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "migration"
  must_not:
    - contains: "Traceback"
```
