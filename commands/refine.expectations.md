---
command: refine
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.refine

## 1. Purpose

Refine existing spec artifacts through guided conversation.

## 2. Preconditions

- `.specs/features/<feature>/spec.md` exists.

## 3. Observable Signals

**stdout must_contain:**
- "refine"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- _(none)_

**update:**
- `.specs/features/<feature>/spec.md`
- `.specs/features/<feature>/plan.md`
- `.specs/features/<feature>/changelog.md`

**optional:**
- _(none)_

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/features/<feature>/`

**forbidden changes:**
- _(none)_

**commit expectations:**
- `refine(<feature>): ...`

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

- Typical range: 30–600 seconds
- Factors: Conversation turns, scope of refinement

## 10. Post-run Checks

- [ ] Diff visible on spec.md or plan.md

## 11. Troubleshooting

- **Symptom:** Refine no-op
  **Cause:** Spec already aligned
  **Fix:** Verify intent vs current spec

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "refine"
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output

```
$ /spec.refine <feature>
> Loaded spec.md and plan.md for <feature>
> Conversational refinement: 3 questions
> Wrote refinements to spec.md (+12 lines, -3 lines)
> Updated changelog.md
exit 0
```

### Files Produced

```
.specs/features/<feature>/spec.md       # refined
.specs/features/<feature>/plan.md       # refined if --plan
.specs/features/<feature>/changelog.md  # new entry
```

### Aligned / Drift / Missing

- **Aligned:** spec/plan updated with traceable changelog entry, no schema regression. Exit 0.
- **Drift:** refinement introduces `[NEEDS CLARIFICATION]` markers > previous count. Exit 1.
- **Missing:** target spec/plan absent. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small refine | 30–90s | conversation turns |
| Project-level refine | 60–240s | profile re-evaluation |
| Plan refine with diagrams | 90–300s | re-rendering |

### Edge Cases

- `project` subject: re-evaluates roadmap after profile changes.
- `plan` subject: targets only plan.md.
- Refinement removes an AC: refine confirms the removal interactively and adjusts FR mapping.

### Post-run Actions

- **On success:** run `/spec.check <feature>` to confirm code alignment.
- **On drift:** open spec.md and resolve `[NEEDS CLARIFICATION]`.
- **On blocked:** confirm the feature slug.
