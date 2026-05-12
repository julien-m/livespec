---
command: stack
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.stack

## 1. Purpose

View the current stack, analyze change impact, or create an ADR.

## 2. Preconditions

- `.specs/stacks/_default.md` exists.

## 3. Observable Signals

**stdout must_contain:**
- "stack"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- _(none)_

**update:**
- `.specs/stacks/_default.md`
- `.specs/stacks/decisions/`

**optional:**
- `.specs/stacks/decisions/ADR-<N>-<slug>.md`

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/stacks/`

**forbidden changes:**
- _(none)_

**commit expectations:**
- `docs(stack): ADR <N>`

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
- Factors: Impact analysis depth

## 10. Post-run Checks

- [ ] ADR file present if --adr was requested

## 11. Troubleshooting

- **Symptom:** Stack missing
  **Cause:** /spec.init not run
  **Fix:** Run /spec.init

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "stack"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--adr"
      must:
        - contains: "ADR-"
```
