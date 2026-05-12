---
command: status
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.status

## 1. Purpose

Display a factual status overview of the roadmap and features (read-only).

## 2. Preconditions

- `.specs/project.md` exists.

## 3. Observable Signals

**stdout must_contain:**
- "LiveSpec"
- "features"

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

- Typical range: 1–30 seconds
- Factors: Feature count, roadmap size

## 10. Post-run Checks

- [ ] Output mentions roadmap tiers and feature statuses

## 11. Troubleshooting

- **Symptom:** Empty output
  **Cause:** No features
  **Fix:** Run /spec.specify first

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "features"
  may:
    - contains: "MVP"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--json"
      must:
        - contains: '"features"'
```

## 13. Demo Session

### Live Console Output

```
$ /spec.status
> Roadmap: 3 MVP · 5 Post-MVP · 2 Future · 1 Deferred
> Features in progress: 2 (<feature>, <feature>)
> Last activity: 2026-05-12 14:22 — impl: 040
exit 0
```

### Files Produced

```
(read-only — prints summary to stdout)
```

### Aligned / Drift / Missing

- **Aligned:** summary lists tier counts, in-progress features, recent changelog. Exit 0.
- **Drift:** spec.status detects a feature without a pipeline.md and flags it as orphan. Exit 0 (informational).
- **Missing:** `.specs/` not initialized. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small project | < 2s | file count |
| Large project | 2–10s | feature folder count |
| Project with logs | 5–20s | log aggregation |

### Edge Cases

- `--json`: emits a structured envelope for machine consumption.
- Multiple features with overlapping branches: status lists them all with branch markers.
- Roadmap has Deferred items: they appear in their own line, distinct from Future.

### Post-run Actions

- **On success:** decide which feature to advance next.
- **On drift:** investigate the flagged orphan feature.
- **On blocked:** run `/spec.init`.
