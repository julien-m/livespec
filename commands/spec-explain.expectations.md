---
command: spec-explain
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec-explain

## 1. Purpose

Living documentation — explain how a feature works (read-only).

## 2. Preconditions

- `.specs/features/<feature>/` exists.

## 3. Observable Signals

**stdout must_contain:**
- "<feature>"
- "Overview"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- _(none)_

**update:**
- _(none)_

**optional:**
- _(none)_

**forbidden:**
- `src/`
- `.specs/`

## 5. Git Effects

**expected dirty paths:**
- _(none)_

**forbidden changes:**
- `any`

**commit expectations:**
- _(none)_

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

- Typical range: 5–60 seconds
- Factors: Feature size, code links

## 10. Post-run Checks

- [ ] Output mentions FR/AC summary

## 11. Troubleshooting

- **Symptom:** Feature unknown
  **Cause:** Wrong slug
  **Fix:** Check `.specs/features/`

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "Overview"
  may:
    - contains: "FR-"
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-explain <feature>
> Loading spec.md, plan.md, implementation.md, changelog.md
> Synthesizing living documentation for <feature>
> Section: Overview · User flows · Architecture · Files · History
exit 0
```

### Files Produced

```
(stdout only — Markdown narrative)
```

### Aligned / Drift / Missing

- **Aligned:** Markdown explanation covers Overview, User flows, Architecture, Files, History sections. Exit 0.
- **Drift:** the feature has partial implementation; explanation marks missing FR/AC explicitly. Exit 0 still (read-only command).
- **Missing:** feature directory not found. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small feature | 15–45s | doc length |
| Medium feature | 45–120s | story count |
| Large feature | 120–300s | implementation breadth |

### Edge Cases

- Implementation lacks @spec anchors: explanation falls back to file inference.
- Multiple changelog entries: explanation summarizes them as a timeline.
- `--json`: emits structured envelope instead of prose.

### Post-run Actions

- **On success:** share the output with reviewers; pipe to a doc site if desired.
- **On drift:** no action.
- **On blocked:** confirm the feature slug; run `/spec-status` to list features.
