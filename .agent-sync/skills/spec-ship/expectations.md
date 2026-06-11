---
command: spec-ship
contract_version: "1.0"
last_reviewed: 2026-06-11
---

# Expectations — /spec-ship

## 1. Purpose

Batch autopilot — ship multiple features from the roadmap end-to-end.

## 2. Preconditions

- `.specs/roadmap.md` has at least one unchecked feature.

## 3. Observable Signals

**stdout must_contain:**
- "ship"
- "PHASE_RESULT"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/features/`

**update:**
- `.specs/roadmap.md`
- `.specs/changelog.md`

**optional:**
- _(none)_

**forbidden:**
- _(none)_

## 5. Git Effects

**expected dirty paths:**
- `.specs/`
- `src/`

**forbidden changes:**
- _(none)_

**commit expectations:**
- `feat(ship): multi-feature batch`

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

- Typical range: 600–7200 seconds
- Factors: Number of features, per-feature complexity

## 10. Post-run Checks

- [ ] Every shipped feature has implementation.md
- [ ] Roadmap entries are checked

## 11. Troubleshooting

- **Symptom:** Stops mid-batch
  **Cause:** One feature failed
  **Fix:** Inspect last feature's progress.md

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "PHASE_RESULT"
  may:
    - contains: "shipped"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--auto"
      must:
        - contains: "batch"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-ship
> Scanning roadmap.md — 3 unchecked items in MVP tier
> Picking next: <feature>
> Spawning /spec-feature -a "<feature>" --branch
> Pipeline complete → SHIP_RESULT: OK on feature/<feature>
> Continuing batch: 2 remaining
exit 0
```

### Files Produced

```
.specs/features/<feature>/             # one folder per shipped feature
git branches:                          # feature/<feature> × N
```

### Aligned / Drift / Missing

- **Aligned:** every targeted roadmap item is shipped (commit + PR), SHIP_RESULT: OK for each. Exit 0.
- **Drift:** one feature returned SHIP_RESULT: BLOCKED; batch halts. Exit 1 with the failing feature name.
- **Missing:** roadmap.md absent or empty. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Single feature | 5–25 min | feature size |
| Batch of 3 small features | 15–60 min | sum of per-feature time |
| Full MVP tier | 60–240 min | feature count × scope |

### Edge Cases

- `--limit N`: ships at most N features then stops.
- `--dry-run`: prints the batch plan without spawning any pipeline.
- A feature fails mid-batch: ship logs the failure and offers `--resume` to skip past.

### Post-run Actions

- **On success:** review the resulting PRs.
- **On drift:** open the failing feature's pipeline.md, fix the blocker, re-run with `--resume`.
- **On blocked:** populate roadmap.md via `/spec-propose`.
