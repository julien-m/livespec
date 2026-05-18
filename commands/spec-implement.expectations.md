---
command: spec-implement
contract_version: "1.0"
last_reviewed: 2026-05-17
---

# Expectations — /spec-implement

## 1. Purpose

Auto-implement a feature from its plan, write tests, run the visual gate for UI features, and map FR/AC to @spec anchors.

## 2. Preconditions

- `.specs/features/<feature>/plan.md` exists.
- `Branch `feature/<feature>` is checked out.`

## 3. Observable Signals

**stdout must_contain:**
- "PHASE_RESULT"
- "implement"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/features/<feature>/progress.md`
- `.specs/features/<feature>/implementation.md`

**update:**
- `.specs/features/<feature>/changelog.md`
- `.specs/changelog.md`

**optional:**
- `.specs/features/<feature>/baselines/`
- `.specs/features/<feature>/checks/<date>-test.md`

**forbidden:**
- `.specs/features/<feature>/spec.md`

## 5. Git Effects

**expected dirty paths:**
- `src/`
- `.specs/features/<feature>/`

**forbidden changes:**
- _(none)_

**commit expectations:**
- `feat(<feature>): ...`

## 6. Produced Artifacts

- path: `.specs/features/<feature>/implementation.md`
  must_contain_sections:
  - "FR mapping"
  - "AC mapping"
- path: `.specs/features/<feature>/checks/<date>-test.md`
  must_contain_sections:
  - "Visual Gate Verdict"

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

- Typical range: 60–1800 seconds
- Factors: Step count, file count, test suite size

## 10. Post-run Checks

- [ ] progress.md fully checked off
- [ ] implementation.md maps every FR/AC

## 11. Troubleshooting

- **Symptom:** Blocked step
  **Cause:** Missing tool
  **Fix:** Run /spec-preflight

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "PHASE_RESULT"
    - exists: ".specs/features/<feature>/progress.md"
  may:
    - contains: "tests passed"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--visual"
      must:
        - contains: "Visual Gate Verdict"
        - contains: "/spec-test <feature> --auto --visual"
    - flag: "--resume"
      must:
        - contains: "Resuming"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-implement <feature>
> Loaded plan.md — 8 steps queued
> Step 1/8: src/api/csv-export.ts (create) — 42 lines
> Step 2/8: tests/api/csv-export.test.ts — 6 tests PASS
> ... (steps 3-7 elided)
> Step 8/8: docs/exports.md (update) — 12 lines
> Visual Gate Verdict: PASS — visual gate passed before final status
> All steps Done · 27 tests pass · implementation.md generated
exit 0
```

### Files Produced

```
.specs/features/<feature>/
├── progress.md            # step-by-step checkpoint (MANDATORY)
├── implementation.md      # FR/AC → file map with @spec anchors
├── logs/<date>.md         # execution log (unless --no-save)
└── changelog.md           # entry "impl: <feature>"
src/<...> + tests/<...>    # code under each step
```

### Aligned / Drift / Missing

- **Aligned:** every step in progress.md is Done, implementation.md maps all FR/AC to anchors, all tests pass. Exit 0.
- **Drift:** one step failed and was rolled back; progress.md shows it `Blocked` with reason. Exit 1.
- **Missing:** plan.md not found, or preflight check failed. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small (3 steps) | 2–5 min | step latency |
| Medium (8 steps) | 5–20 min | test compile time |
| Large (15+ steps) | 20–60 min | step orchestration |

### Edge Cases

- `--resume`: reads progress.md and continues at the first non-Done step.
- `--step`: pauses between steps for manual validation.
- Visual feature: runs `/spec-test <feature> --auto --visual`; `Implemented` requires Visual Gate Verdict PASS.
- `--no-visual` on a visual feature: leaves status `In Progress`.
- A step's tests fail twice: implement stops, marks the step Blocked, surfaces the failing output.

### Post-run Actions

- **On success:** visual gate passed before final status; review generated checks and baseline artifacts.
- **On drift:** inspect progress.md, fix the failing step, re-run with `--resume`.
- **On blocked:** run `/spec-plan` first, or unblock the preflight check.
