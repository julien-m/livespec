---
command: spec-feature
contract_version: "1.0"
last_reviewed: 2026-06-07
---

# Expectations — /spec-feature

## 1. Purpose

Run the full feature pipeline: specify → plan → review → implement → test. Commit only when explicitly authorized.

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
- `penflow/flow-ui-contract/` for UI features
- `penflow/ui.pen` for UI features
- `penflow/semantic-ui-tree.json` for UI features
- `penflow/expected-ui-tree.json` for UI features
- `penflow/code-ir.json` for UI features
- `.specs/design/screens/<feature_slug>/` for UI feature mockup PNG exports
- `.specs/design/baselines/<feature_slug>/` for UI feature runtime baseline sync
- `.mockup-validation/audit-report.md` for UI feature Mockup Factory validation
- `.mockup-validation/<feature_slug>/checklist.md` for UI feature Mockup Factory validation
- `.mockup-validation/visual-evidence/manifest.json` for UI feature visual evidence PASS
- `.mockup-validation/visual-evidence/visual-report.md` for UI feature visual evidence PASS

**update:**
- `.specs/roadmap.md`
- `.specs/changelog.md`
- `.specs/design/screens/index.md` for UI features
- `.specs/design/changelog.md` for UI features

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
- none unless explicitly authorized

## 6. Produced Artifacts

- path: `.specs/features/<feature>/implementation.md`
  must_contain_sections:
  - "FR mapping"
- path: `.specs/design/screens/<feature_slug>/`
  note: "Global LiveSpec Design Registry mockup PNG exports; missing mockups block Penflow UI features"
- path: `.specs/design/baselines/<feature_slug>/`
  note: "Global LiveSpec Design Registry runtime screenshot destination"
- path: `.mockup-validation/visual-evidence/manifest.json`
  note: "Mockup Factory visual evidence; status must be PASS before any UI implementation code"
- stdout marker: `Penflow Contract Verdict: ABSENT | BLOCKED | FAIL | PASS`
  - `ABSENT`: feature is non-UI
  - `BLOCKED`: UI forward contract generation failed
  - `FAIL`: runtime raw compare report is `FAIL` or has issues
  - `PASS`: UI forward/runtime artifacts were generated or verified, and runtime compare is `PASS` with zero issues when required
  - `BLOCKED`: also required when `BLOCKED at step 0.5 - design_registry_sync_failed` reports `Mockups missing for Penflow UI feature`
  - `BLOCKED`: also required when `--require-mockup-validation` reports missing Mockup Factory proof or visual-evidence status other than `PASS`

## 7. Exit Codes

| Code | Meaning | Operator action |
|------|---------|-----------------|
| 0    | success | nothing |
| 1    | drift   | inspect report, fix divergence |
| 2    | blocked | restore precondition, retry |
| 6    | visual gate FAIL after pipeline | iterate via `/spec-fix`; do not commit |
| 7    | visual gate BLOCKED (missing baselines/mockups/compare reports) | generate prereqs or surface gap, no auto-PASS |

## 7b. Visual Gate (required before feature completion)

`/spec-feature` MUST call `livespec visual-gate validate --feature <slug> --command spec-feature [--target <t>]` AFTER implementation and tests, BEFORE commit. The skill MUST refuse to commit (and MUST refuse `--auto` continuation) when the gate exit is 6 or 7.

Nested skill calls (`/spec-specify`, `/spec-plan`, `/spec-implement`, `/spec-test`, `/spec-fix`) inside the pipeline run as independent sub-agents (Task tool) so each can hold its own goal without colliding with the `/spec-feature` parent goal. The parent only re-aggregates verdicts after each sub-agent returns.

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
- [ ] UI features have `penflow/code-ir.json` before implementation
- [ ] Global LiveSpec Design Registry has `.specs/design/screens/<feature_slug>/`, `.specs/design/baselines/<feature_slug>/`, `.specs/design/screens/index.md`, and `.specs/design/changelog.md`
- [ ] UI features have Mockup Factory PASS proof before implementation: `.mockup-validation/audit-report.md`, `.mockup-validation/<feature_slug>/checklist.md`, `.mockup-validation/<feature_slug>/manifest.json`, `.mockup-validation/<feature_slug>/drift-report.json`, `.mockup-validation/visual-evidence/manifest.json`, `.mockup-validation/visual-evidence/visual-report.md`, and visual evidence PNGs
- [ ] If a phase agent omits `PHASE_RESULT`, artifact recovery either advances safely or emits `BLOCKED - phase_agent_timeout`

## 11. Troubleshooting

- **Symptom:** Stops at plan-review
  **Cause:** Plan invalid
  **Fix:** Address findings and resume
- **Symptom:** `plan.md` exists but pipeline remains `Plan | In Progress`
  **Cause:** Phase agent omitted `PHASE_RESULT` after writing the artifact
  **Fix:** Supervisor applies Phase Agent Timeout and Artifact Recovery; if required sections are missing, retry `/spec-feature --resume <feature>`

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
> Commit: skipped - no explicit user authorization
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

- **Aligned:** all 5 phases Done, AC coverage 100%, no review findings remain, no commit unless explicitly authorized. Exit 0.
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

- **On success:** report changed files and verification evidence. Do not create commits, tags, pushes, or branches unless the current user request explicitly asks for that exact repository-history action.
- **On drift:** read `FINDINGS_DETAIL` in `pipeline.md`, fix the spec/plan, re-run with `--resume`.
- **On blocked:** run `/spec-preflight` standalone to identify the missing prerequisite.
