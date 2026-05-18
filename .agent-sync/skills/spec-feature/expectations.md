---
command: spec-feature
contract_version: "1.0"
last_reviewed: 2026-05-18
---

# Expectations — /spec-feature

## 1. Purpose

Run the full feature pipeline: specify → plan → review → implement → test → commit.

## 2. Preconditions

- `.specs/project.md` exists.
- `Feature description supplied.`

## 3. Observable Signals

**stdout must_contain:**
- "PHASE_RESULT"
- "feature"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/features/<feature>/spec.md`
- `.specs/features/<feature>/plan.md`
- `.specs/features/<feature>/progress.md`

**update:**
- `.specs/roadmap.md`
- `.specs/changelog.md`

**optional:**
- _(none)_

**forbidden:**
- _(none)_

## 5. Git Effects

**expected dirty paths:**
- `.specs/features/<feature>/`
- `src/`

**forbidden changes:**
- _(none)_

**commit expectations:**
- `feat(<feature>): full pipeline`

## 6. Produced Artifacts

- path: `.specs/features/<feature>/implementation.md`
  must_contain_sections:
  - "FR mapping"

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

- Typical range: 300–3600 seconds
- Factors: Whole pipeline (specify+plan+implement+test)

## 10. Post-run Checks

- [ ] progress.md exists and is complete
- [ ] implementation.md maps every FR

## 11. Troubleshooting

- **Symptom:** Stops at plan-review
  **Cause:** Plan invalid
  **Fix:** Address findings and resume

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "PHASE_RESULT"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--auto"
      must:
        - contains: "auto"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-feature -a "Add CSV export"
> Phase 1 (Specify): spawning agent — 1 spec.md drafted (12 FR, 9 AC)
> Gate 1: review PASS — proceeding
> Phase 2 (Plan): spawning agent — 1 plan.md drafted (8 steps)
> Gate 2: review PASS — proceeding
> Phase 2.7 (Preflight): READY
> Phase 3 (Implement): 8/8 steps done — 14 files changed, 27 tests pass
> Phase 3.5 (Test): AC coverage 9/9 — visual: skipped
> Auto-commit: 1 commit pushed on feature/<feature>
exit 0
```

### Files Produced

```
.specs/features/<feature>/
├── spec.md                    # 12 FR, 9 AC, 4 user stories
├── plan.md                    # technical plan, sequence diagrams
├── pipeline.md                # phase tracker (Done × 7)
├── progress.md                # step-by-step checkpoint
├── implementation.md          # FR → file map
└── changelog.md               # first entry
```

### Aligned / Drift / Missing

- **Aligned:** all 5 phases Done, AC coverage 100%, no review findings remain, one commit on the feature branch. Exit 0.
- **Drift:** Phase 1.5 or 2.5 returns BLOCKING findings; in `--auto` mode pipeline retries up to 2× then aborts. Exit 1.
- **Missing:** Preflight failed critical check (no git, no Python, no LLM creds). Exit 2 with the failing check name.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small feature (S, no UI) | 5–10 min | story count |
| Medium feature (M, 1 surface) | 10–25 min | tests + AC count |
| Large feature (L, multi-surface) | 25–60 min | implementation surface |

### Edge Cases

- `--resume`: reads `pipeline.md` and re-spawns the first non-Done phase agent; never re-runs Done phases.
- `--mono`: implement phase runs single-agent (no Superpowers dispatch); feature-level supervisor still spawns Specify/Plan/Implement/Test separately.
- `--economy`: disables ALL sub-agent dispatch; all phases run inline. Lossless, just slower.

### Post-run Actions

- **On success:** open the commit, push, request review.
- **On drift:** read `FINDINGS_DETAIL` in `pipeline.md`, fix the spec/plan, re-run with `--resume`.
- **On blocked:** run `/spec-preflight` standalone to identify the missing prerequisite.
