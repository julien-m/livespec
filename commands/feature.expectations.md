---
command: feature
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.feature

## 1. Purpose

Run the full feature pipeline: specify → plan → review → implement → test → commit.

## 2. Preconditions

- `.specs/project.md` exists.
- `Feature description supplied.`

## 3. Observable Signals

**stdout must_contain:**
- "PHASE_RESULT"
- "feature"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/features/<feature>/spec.md`
- `.specs/features/<feature>/plan.md`
- `.specs/features/<feature>/progress.md`

**update:**
- `.specs/roadmap.md`
- `.specs/changelog.md`

**optional:**
- _(none)_

**forbidden:**
- _(none)_

## 5. Git Effects

**expected dirty paths:**
- `.specs/features/<feature>/`
- `src/`

**forbidden changes:**
- _(none)_

**commit expectations:**
- `feat(<feature>): full pipeline`

## 6. Produced Artifacts

- path: `.specs/features/<feature>/implementation.md`
  must_contain_sections:
  - "FR mapping"

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

- Typical range: 300–3600 seconds
- Factors: Whole pipeline (specify+plan+implement+test)

## 10. Post-run Checks

- [ ] progress.md exists and is complete
- [ ] implementation.md maps every FR

## 11. Troubleshooting

- **Symptom:** Stops at plan-review
  **Cause:** Plan invalid
  **Fix:** Address findings and resume

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "PHASE_RESULT"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--auto"
      must:
        - contains: "auto"
```
