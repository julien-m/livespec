---
command: specify
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.specify

## 1. Purpose

Create a new feature spec with user stories, Mermaid flowcharts, AC, and FR.

## 2. Preconditions

- `.specs/project.md` exists.
- `Feature description supplied as argument.`

## 3. Observable Signals

**stdout must_contain:**
- "spec.md created"
- "<feature>"

**stdout must_not_contain:**
- "Traceback"
- "TBD"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/features/<feature>/spec.md`
- `.specs/features/<feature>/changelog.md`

**update:**
- `.specs/roadmap.md`
- `.specs/changelog.md`

**optional:**
- `.specs/features/<feature>/seed.md`

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/features/<feature>/`

**forbidden changes:**
- _(none)_

**commit expectations:**
- `spec: add <feature>`

## 6. Produced Artifacts

- path: `.specs/features/<feature>/spec.md`
  must_contain_sections:
  - "User Scenarios"
  - "Acceptance Criteria"
  - "Functional Requirements"

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

- Typical range: 30–300 seconds
- Factors: Scope analysis, story count, mockup generation

## 10. Post-run Checks

- [ ] spec.md has Gherkin + Mermaid per user story
- [ ] FR list maps each AC

## 11. Troubleshooting

- **Symptom:** Spec rejected by reviewer
  **Cause:** Missing story or AC
  **Fix:** Re-run with refined description

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "spec.md created"
    - exists: ".specs/features/<feature>/spec.md"
  may:
    - contains: "Gherkin"
  must_not:
    - contains: "Traceback"
    - contains: "TBD"
```
