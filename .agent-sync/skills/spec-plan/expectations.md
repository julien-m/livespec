---
command: spec-plan
contract_version: "1.0"
last_reviewed: 2026-09-05
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
- proof boundary: native QE Analysis from `system/qe-analysis.md` translates risks into gates, test levels, proof artifacts, evidence gaps, and review/audit/test boundaries; user hooks are extension-only
- stdout marker: `Penflow Contract Verdict: ABSENT | READY | FAIL | BLOCKED`
  - `ABSENT`: unrequired non-UI inspection has no workspace.
  - `READY`: required planning artifacts and ID mappings are available; `certified: false`.
  - `FAIL` / `BLOCKED`: invalid or missing required preparation input; no certification is implied.

### C51 stage evidence

- This command prepares inputs; no runtime report/build manifest or final certificate is required before its producing/test stage.

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
- [ ] Native QE Analysis applied: risks map to gates, test levels, proof artifacts, gaps, and boundary note

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

## Approved visual source boundary

Standard planning declares closed verification policy in every actual active plan; review-snapshot automatically generates the union, preserving required procedures from earlier active plans and authenticated inheritance. Missing or duplicate metadata blocks; candidate C20 never supplies policy.

Visual planning records a complete cumulative pre-dispatch review snapshot and packages the actual raw reviewer output through the internal review-result command. Missing review fields are rejected, never synthesized; transport packaging remains uncertified. Plan Review Done requires `--review-result`; missing or stale input, review findings or mismatched selection block the transition. Preparation reports READY with certified false. Subsequent design certification requires the approved baseline and a current Penflow PASS with certified true. No stdout PASS or registry finalization receipt substitutes for bound review approval.

The C20 producer prepares missing test identifiers before first review through Penflow authority prepare; existing explicit identifiers remain unchanged. The machine snapshot gate delegates validate-flow-contract --require-test-ids and cannot publish active invalid or unidentified C20. Review never repairs approved identities.
