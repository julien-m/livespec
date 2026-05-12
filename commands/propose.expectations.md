---
command: propose
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.propose

## 1. Purpose

Analyze project context and propose the next feature(s) to build.

## 2. Preconditions

- `.specs/project.md` exists.
- `.specs/roadmap.md` exists (may be empty).

## 3. Observable Signals

**stdout must_contain:**
- "Proposal"
- "next feature"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- _(none)_

**update:**
- `.specs/roadmap.md`

**optional:**
- _(none)_

**forbidden:**
- `.specs/features/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/roadmap.md`

**forbidden changes:**
- _(none)_

**commit expectations:**
- `docs(spec): propose <feature>`

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

- Typical range: 10–120 seconds
- Factors: Project size, number of existing features

## 10. Post-run Checks

- [ ] roadmap.md has a fresh entry under MVP/Post-MVP/Future

## 11. Troubleshooting

- **Symptom:** No proposal returned
  **Cause:** Project lacks signals
  **Fix:** Add detail to project.md and retry

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "Proposal"
  may:
    - contains: "MVP"
  must_not:
    - contains: "Traceback"
```
