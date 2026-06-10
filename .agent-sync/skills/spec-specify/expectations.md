---
command: spec-specify
contract_version: "1.0"
last_reviewed: 2026-06-10
---

# Expectations — /spec-specify

## 1. Purpose

Create a new feature spec with user stories, Mermaid flowcharts, AC, and FR.

## 2. Preconditions

- `.specs/project.md` exists.
- `Feature description supplied as argument.`

## 3. Observable Signals

**stdout must_contain:**
- "spec.md created"
- "<feature>"
- "Penflow contract:"

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
- `.specs/features/<feature>/spec.md` section `## Penflow Contract`
- `penflow/flow-ui-contract/` for UI features
- `penflow/semantic-ui-tree.json` for UI features
- `penflow/code-ir.json` for UI features

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
- stdout marker: `Penflow Contract Verdict: ABSENT | BLOCKED | PASS`
  - `ABSENT`: non-UI feature without root `penflow/`
  - `BLOCKED`: UI feature forward contract generation failed
  - `PASS`: semantic tree was read and IDs were resolved or explicitly clarified

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
    - contains: "Penflow contract"
    - exists: ".specs/features/<feature>/spec.md"
  may:
    - contains: "Gherkin"
  must_not:
    - contains: "Traceback"
    - contains: "TBD"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-specify "Add filter chips to search results"
> Detected scope: M · Stories: 3 (P1 × 2, P2 × 1)
> Drafting spec.md (9 AC, 11 FR)
> Wrote .specs/features/<feature>/spec.md
> Updated .specs/roadmap.md (checked the matching item)
exit 0
```

### Files Produced

```
.specs/features/<feature>/
├── spec.md                # user stories + AC + FR + Mermaid flowcharts
└── changelog.md           # first entry "spec: add <feature>"
.specs/roadmap.md          # roadmap item checked
.specs/changelog.md        # summary line appended
```

### Aligned / Drift / Missing

- **Aligned:** spec.md exists with Gherkin + Mermaid for every story, ACs numbered, FRs mapped. Exit 0.
- **Drift:** spec contains `[NEEDS CLARIFICATION]` markers > 3, or a story lacks Gherkin. Exit 1 with the gap report.
- **Missing:** `.specs/project.md` not found. Exit 2 with recovery `Run /spec-init first`.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small spec (1 story) | 30–60s | LLM latency |
| Medium spec (3 stories) | 60–180s | story expansion |
| Large spec (5+ stories + ER) | 180–300s | diagram generation |

### Edge Cases

- Description references a feature that overlaps an existing one: spec-specify proposes a split and writes a `seed.md` for each sub-feature.
- LLM emits Mermaid syntax errors: spec-specify retries once, then fails with the malformed block highlighted.
- Roadmap already has a matching item: it gets checked and linked to the new feature folder.

### Post-run Actions

- **On success:** run `/spec-plan <feature>` next.
- **On drift:** open spec.md, resolve `[NEEDS CLARIFICATION]`, re-run with `--refine`.
- **On blocked:** run `/spec-init`, then retry.
