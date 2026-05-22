---
command: spec-stack
contract_version: "1.0"
last_reviewed: 2026-05-22
---

# Expectations — /spec-stack

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
  **Cause:** /spec-init not run
  **Fix:** Run /spec-init

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

## 13. Demo Session

### Live Console Output

```
$ /spec-stack
> Current stack: <stack>
> Impact analysis: 3 files affected by your draft change
> Drafting ADR-012-replace-pg-with-sqlite.md
> Wrote .specs/stacks/decisions/ADR-012-*.md
exit 0
```

### Files Produced

```
.specs/stacks/decisions/ADR-NNN-*.md      # new ADR
.specs/stacks/_default.md                  # updated if stack identity changed
.specs/changelog.md                        # stack: ADR-NNN entry
```

### Aligned / Drift / Missing

- **Aligned:** ADR exists with Context, Decision, Consequences sections, stack rationale updated. Exit 0.
- **Drift:** ADR missing one of the canonical sections. Exit 1.
- **Missing:** `.specs/stacks/` directory not initialized. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Single ADR | 20–60s | LLM call |
| ADR + impact analysis | 60–180s | repo scan |
| ADR + propagation to features | 180–600s | feature touch count |

### Edge Cases

- Stack change affects existing features: spec-stack lists them and proposes `/spec-refine` to update each.
- `--view`: read-only mode lists the current stack and ADRs without prompting changes.
- ADR conflicts with a previous one: spec-stack surfaces the conflict for manual resolution.

### Post-run Actions

- **On success:** run `/spec-refresh-conventions` if the stack identity changed.
- **On drift:** edit the ADR to add missing sections.
- **On blocked:** run `/spec-init` first.
