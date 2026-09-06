---
command: spec-feature
contract_version: "1.0"
last_reviewed: 2026-09-05
---

<!-- @spec(FR-004) -->

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
- A real Python traceback header: `Traceback (most recent call last):` followed by an actual newline. Quoted or JSON-escaped diagnostics that describe the rule are permitted; section 12 defines the exact machine signature.

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
- `.specs/features/<feature>/spec.md` section `## Clarifications` (Phase 1.6 Clarify gate, when ambiguities were resolved)

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
<!-- @spec FR-004: Proof docs — .specs/features/067-visual-preview-proof-publishing/spec.md#fr-004 -->
- stdout marker: `![visual proof](/absolute/path/to/image.png)` for every validation PNG published by child visual workflows
- stdout marker: `visual-preview url /absolute/path/to/image.png`
- stdout marker: `Open for annotation: http://127.0.0.1:<port>/i/<id>`
- fallback marker: `Visual preview: unavailable - visual-preview CLI missing`
- proof boundary: `visual_evidence_receipt_path` remains required for pixel fidelity; preview URLs are human-visible annotation proof only
- stdout marker: `Clarify gate` — Phase 1.6 runs after spec review and before plan; in `--auto`, an unresolved question emits `BLOCKED at step 1.6 - decision_needed - clarify question requires human answer`
- stdout marker: `Specification Analysis Report` — Phase 2.6 Analyze gate (read-only `/spec-check --pre-impl`) runs after plan review and before preflight; CRITICAL or HIGH findings block implementation (`pipeline update --phase analyze --status blocked`); creates no `checks/`, no changelog, no `src/`
- proof boundary: when `## Clarifications` is written it carries `### Session YYYY-MM-DD` with at most 5 accepted `- Q: ... -> A: ...` bullets per session and no duplicate session bullets
- stdout marker: `Penflow Contract Verdict: ABSENT | READY | PASS | FAIL | BLOCKED`
  - `ABSENT` / `READY`: unrequired non-UI or preparation inspection only, `certified: false`.
  - `PASS`: installed Penflow revalidated the cumulative report for the caller-required profile and current report/scope/build bindings; `certified: true`.
  - `FAIL` / `BLOCKED`: rejected, missing, stale or incompatible required evidence; raw compare PASS never substitutes for certification.

### C51 stage evidence

- UI closure requires implementation certification after actual captures and cumulative report production: exit 0, verdict PASS, certified true, required_profile implementation. The Test child returns actual paths in JSON extra.runner_build_manifest and extra.penflow_validation_path; absent fields cannot be synthesized. Preserve validation JSON and the independent runner manifest path; forward the manifest to UI terminal finalize/pipeline calls. Non-UI omits the argument.
- Existing Global LiveSpec Design Registry, MockupFactory and visual-gate receipts remain required for visual closure; C51 does not replace pixel fidelity evidence.

## 7. Exit Codes

| Code | Meaning | Operator action |
|------|---------|-----------------|
| 0    | success | nothing |
| 1    | drift   | inspect report, fix divergence |
| 2    | blocked | restore precondition, retry |
| 6    | visual gate FAIL after pipeline | iterate via `/spec-fix`; do not commit |
| 7    | visual gate BLOCKED (missing baselines/mockups/compare reports) | generate prereqs or surface gap, no auto-PASS |

## 7b. Visual Gate (required before visual feature completion)

For VISUAL features, `/spec-feature` MUST call `livespec visual-gate validate --feature <slug> --command spec-feature [--target <t>]` AFTER implementation and tests, BEFORE commit. The skill MUST refuse to commit (and MUST refuse `--auto` continuation) when the gate exit is 6 or 7. Non-UI features do not require visual evidence; their applicable nonvisual checks remain mandatory.

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

- [ ] Clarify gate ran after spec review and before plan; if `## Clarifications` was written it has ≤ 5 accepted Q/A for the session and no duplicate session bullets
- [ ] Analyze gate (Phase 2.6) ran after plan review and before preflight; blocked implementation on any CRITICAL or HIGH finding; wrote no `checks/`, no changelog, no `src/`
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

## Audit and phase completion

- Audit remains read-only; the authorized implementing agent fixes findings, reruns affected checks and reruns audit. No unsupported fix flag.
- Only actually executed successful phases become Done; preserve Pending, Skipped and BLOCKED otherwise. Applicable mandatory phases still require proof before closure.

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "PHASE_RESULT"
    - receipt_verdict: {"kind": "conventions", "verdict": "PASS", "required_if_exists": true}
  must_not:
    - contains: "Traceback (most recent call last):\n"
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

## Bound Plan Review source authority

UI or accepted Penflow history requires Plan extra.review_result_path from the actual pre-dispatch snapshot review. Plan Review Done consumes --review-result and publishes the approved baseline before recording completion. Interactive overrides and stdout PASS do not substitute for this bound result. Source selection and disposition active/retired remain reviewed, including prior/new deltas.
