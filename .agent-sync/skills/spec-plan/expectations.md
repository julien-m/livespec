---
command: spec-plan
contract_version: "1.0"
last_reviewed: 2026-05-26
---

# Expectations — /spec-plan

## 1. Purpose

Generate a technical plan with sequence, state, and ER diagrams.

## 2. Preconditions

- `.specs/features/<feature>/spec.md` exists.

## 3. Observable Signals

**stdout must_contain:**
- "plan.md"
- "<feature>"
- "Penflow contract:"

**stdout must_not_contain:**
- "Traceback"
- "[DECISION NEEDED]"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/features/<feature>/plan.md`

**update:**
- `.specs/features/<feature>/changelog.md`

**optional:**
- `## Penflow Contract Inputs` in plan.md for UI features
- `penflow/code-ir.json` generated or verified before UI plan output

**forbidden:**
- `.specs/features/<feature>/spec.md`

## 5. Git Effects

**expected dirty paths:**
- `.specs/features/<feature>/plan.md`

**forbidden changes:**
- _(none)_

**commit expectations:**
- `plan(<feature>): add plan`

## 6. Produced Artifacts

- path: `.specs/features/<feature>/plan.md`
  must_contain_sections:
  - "Summary"
  - "Technical Context"
  - "Constitution Check"
  - "Implementation Plan"
- stdout marker: `Penflow Contract Verdict: ABSENT | BLOCKED | PASS`
  - `ABSENT`: non-UI feature without root `penflow/`
  - `BLOCKED`: UI plan needs `code-ir.json` or other root artifacts but forward generation failed
  - `PASS`: required Penflow planning inputs are present

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
- Factors: Feature complexity, diagram count

## 10. Post-run Checks

- [ ] plan.md contains a sequence + state + ER diagram
- [ ] No [DECISION NEEDED] markers

## 11. Troubleshooting

- **Symptom:** Constitution Check fails
  **Cause:** Spec contradicts constitution
  **Fix:** Revise spec or update constitution

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - exists: ".specs/features/<feature>/plan.md"
    - contains: "plan.md"
    - contains: "Penflow contract"
  may:
    - contains: "mermaid"
  must_not:
    - contains: "Traceback"
    - contains: "[DECISION NEEDED]"
  when:
    - flag: "--review"
      must:
        - contains: "Plan Review"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-plan <feature>
> Loaded spec.md (9 AC, 11 FR)
> Drafting plan.md — 8 steps, 1 sequence diagram, 1 state diagram
> Constitution check: PASS
> Wrote .specs/features/<feature>/plan.md
exit 0
```

### Files Produced

```
.specs/features/<feature>/
├── plan.md                # file-by-file plan, diagrams, testing strategy
└── changelog.md           # entry "plan: draft <feature>"
```

### Aligned / Drift / Missing

- **Aligned:** plan.md has Technical Context, Constitution Check, sequence/state/ER diagrams as appropriate, and one step per FR. Exit 0.
- **Drift:** Constitution Check missing or an FR is uncovered in the plan. Exit 1.
- **Missing:** spec.md not found for the feature. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small plan (3 steps) | 30–60s | LLM call count |
| Medium plan (8 steps) | 60–180s | diagram drafting |
| Plan with ER + state diagrams | 120–300s | entity count |

### Edge Cases

- Plan references libraries not in the stack: spec-plan warns and suggests adding an ADR.
- `--no-contracts`: skips OpenAPI/GraphQL emission; useful when the feature exposes no API.
- Plan exceeds 800 lines: spec-plan suggests splitting the feature.

### Post-run Actions

- **On success:** review plan.md, then run `/spec-implement <feature>`.
- **On drift:** open the gap report, refine plan.md, re-run `--refine`.
- **On blocked:** run `/spec-specify` first.
