---
command: spec-test
contract_version: "1.0"
last_reviewed: 2026-09-07
---

<!-- @spec(FR-004) -->

# Expectations — /spec-test

## 1. Purpose

Audit test coverage, generate missing tests, execute the suite, and verify visual fidelity.

## 2. Preconditions

- `.specs/features/<feature>/spec.md` exists.
- `A test driver is configured (`.specs/testing/`).`

Before generating or repairing AC/visual tests, the existing progression CLI must establish current Clarify and Analyze readiness separately for every affected feature with the actual model/budget. Preserve each feature's real command, exit code and raw output; stop before the failing feature's writes. Audit-only, no-generate, dry-run and regeneration without confirm do not request generation readiness or generate tests; confirmed regeneration remains generation-only. This deterministic gate consumes current semantic receipts and does not demand future runtime evidence.

## 3. Observable Signals

**stdout must_contain:**
- "test"
- "test"

**stdout must_not_contain:**
- A real Python traceback header: `Traceback (most recent call last):` followed by an actual newline. Quoted or JSON-escaped diagnostics that describe the rule are permitted; section 12 defines the exact machine signature.

**stderr:**
- "_(none expected on happy path)_"

Collection and test failures are established by runner-owned execution receipts and exit status, not by quoted diagnostic words. Policy 2 rejects failed, missing, empty or entirely skipped results even when a wrapper returns exit 0; documentary mentions cannot establish execution outcomes.

## 4. Filesystem Effects

`test-report` excludes --dry-run and every --regenerate-missing mode: render output in memory, without checks/implementation/changelog/strategy writes. Confirmed regeneration creates missing test sources only. Audit-only preserves its existing report and metadata updates but never claims suite execution. Normal execution retains the effects below; --no-update still excludes implementation.md. Runtime goal/receipt bookkeeping remains the existing protocol, separate from business artifacts.

Visual capture, publication, baseline/registry updates and visual closure requirements apply only when the existing `visual` execution branch is active: a selected UI feature, no `--no-visual`, and no audit, dry-run or regeneration-only mode. `--no-generate` still executes existing visual tests; apply this scope separately to each selected feature in `--all`.

**create:**
- `.specs/features/<feature>/checks/<date>-test.md`

**update:**
- _(none)_

**optional:**
- `test-results/`
- `.specs/features/<feature>/baselines/`
- `.specs/features/<feature>/design-alignment/`
- `penflow/review-report.md`
- `penflow/fix-report.md`

**create for UI runs with root `penflow/`:**
- `penflow/actual-ui-tree.json`
- `penflow/compare-report.json`
- `penflow/compare-report.md`
- browser screenshot evidence under `.specs/features/<feature>/run/<run-id>/<target>/`; feature baselines contain only approved, promoted copies
- `.specs/design/baselines/<feature_slug>/` synced runtime screenshots in the Global LiveSpec Design Registry

**require for UI runs with root `penflow/`:**
- `.specs/design/screens/<feature_slug>/`
- `.specs/design/screens/index.md`
- `.specs/design/changelog.md`
- `.mockup-validation/audit-report.md`
- `.mockup-validation/<feature_slug>/checklist.md`
- `.mockup-validation/visual-evidence/manifest.json` with status `PASS`
- `.mockup-validation/visual-evidence/visual-report.md`

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/features/<feature>/checks/`

**forbidden changes:**
- _(none)_

**commit expectations:**
- _(none)_

## 6. Produced Artifacts

- stdout marker: `Visual Gate Verdict: PASS | FAIL | BLOCKED` for `--visual` runs
<!-- @spec FR-004: Proof docs — .specs/features/067-visual-preview-proof-publishing/spec.md#fr-004 -->
- stdout marker: `![visual proof](/absolute/path/to/image.png)` for every validation PNG
- stdout marker: `visual-preview url /absolute/path/to/image.png`
- stdout marker: `Open for annotation: http://127.0.0.1:<port>/i/<id>`
- fallback marker: `Visual preview: unavailable - visual-preview CLI missing`
- proof boundary: `visual_evidence_receipt_path` remains required for pixel fidelity; preview URLs are human-visible annotation proof only
- proof boundary: native QE Analysis from `system/qe-analysis.md` verifies AC/FR test-evidence sufficiency, required gates, expected evidence, missing proof, and review/audit/test boundaries; user hooks are extension-only
- stdout marker: `Design Alignment Verdict: PASS | FAIL | BLOCKED` for `--visual` runs when `ui.pen` is present or changed
- stdout marker: `Penflow Contract Verdict: ABSENT | READY | PASS | FAIL | BLOCKED`
  - `ABSENT` / `READY`: unrequired non-UI or preparation inspection only, `certified: false`.
  - `PASS`: installed Penflow revalidated the cumulative report for the caller-required profile and current report/scope/build bindings; `certified: true`.
  - `FAIL` / `BLOCKED`: rejected, missing, stale or incompatible required evidence; raw compare PASS never substitutes for certification.

### C51 stage evidence

- UI closure requires implementation certification after actual captures and cumulative report production: exit 0, verdict PASS, certified true, required_profile implementation. Preserve validation JSON and the independent runner manifest path; forward the manifest to UI terminal finalize/pipeline calls. Non-UI omits the argument.
- Existing Global LiveSpec Design Registry, MockupFactory and visual-gate receipts remain required for visual closure; C51 does not replace pixel fidelity evidence.

## 7. Exit Codes

| Code | Meaning | Operator action |
|------|---------|-----------------|
| 0    | success | nothing |
| 1    | drift   | inspect report, fix divergence |
| 2    | blocked | restore precondition, retry |
| 6    | visual gate FAIL (runtime under design/screens, physical copy, alignment FAIL) | run cleanup + re-test |
| 7    | visual gate BLOCKED (prereqs / weak signals only) | generate baselines, do not auto-PASS |

## 7b. Visual Gate (required for VISUAL features)

`/spec-test` MUST call `livespec visual-gate validate --feature <slug> --command spec-test [--target <t>]` BEFORE returning. Phase 0 (prereqs) blocks on exit 7; phase visuel runs the runner (web/Playwright, iOS/XCUITest, Android/Maestro, Tauri) with `output_path` outside `.specs/design/screens/`; phase finale re-runs the gate.

Runners write captures to `.specs/features/<slug>/run/<ts>/<target>/<screen>.png`. Promotion into the registry uses `livespec visual-gate promote`. The skill MUST NOT mark a visual test step done when the gate exit is 6 or 7.

## 8. Outcome Matrix

- **success:** every `must` rule passes, exit_code == 0
- **drift:** at least one `must` rule fails, command exited 0
- **blocked:** precondition missing or artifact missing
- **error:** command itself crashed (exit_code != 0)

## 9. Runtime Profile

- Typical range: 30–1200 seconds
- Factors: Suite size, parallel workers, visual diff cost

## 10. Post-run Checks

- [ ] Coverage report present in checks/ only for test-report modes; otherwise rendered in memory
- [ ] Functional suite exits 0 only for test-suite modes; real execution receipts required, never the word passed
- [ ] Native QE Analysis applied: AC/FR evidence sufficiency, gates, expected evidence, gaps, and boundary note are recorded
- [ ] Penflow UI runs have Global LiveSpec Design Registry artifacts: `.specs/design/screens/<feature_slug>/`, `.specs/design/baselines/<feature_slug>/`, `.specs/design/screens/index.md`, and `.specs/design/changelog.md`
- [ ] Penflow UI runs have Mockup Factory PASS proof: `.mockup-validation/audit-report.md`, `.mockup-validation/<feature_slug>/checklist.md`, `.mockup-validation/<feature_slug>/manifest.json`, `.mockup-validation/<feature_slug>/drift-report.json`, `.mockup-validation/visual-evidence/manifest.json`, `.mockup-validation/visual-evidence/visual-report.md`, and visual evidence PNGs

## 11. Troubleshooting

- **Symptom:** No tests collected
  **Cause:** Missing driver
  **Fix:** Run /spec-preflight or /spec.driver list

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "test"
    - receipt_verdict: {"kind": "conventions", "verdict": "PASS", "required_if_exists": true}
  may:
    - contains: "coverage"
  must_not:
    - contains: "Traceback (most recent call last):\n"
  when:
    - flag: "--visual"
      may:
        - contains: "Visual baselines"
        - contains: "Design Alignment Verdict"
        - contains: "Visual Gate Verdict"
        - contains: "Penflow Contract Verdict"
        - contains: "PASS | FAIL | BLOCKED"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-test <feature> --visual
> Auditing AC coverage: <feature> has 12 ACs, 9 covered, 3 missing
> Generating 3 missing scaffolds in apps/web/tests/e2e/<feature>/
> Design Alignment Verdict: PASS
> Running 38 specs across 1 surface (web)
> Visual: 13 baselines · 0 diff · 1 missing (<screen>)
> Visual Gate Verdict: FAIL
> AC coverage: 12/12 ✓  Visual: 12/13 ✗ (1 missing)
exit 1
```

### Files Produced

```
apps/web/tests/e2e/<feature>/
├── happy-path.spec.ts          # generated from AC-001..AC-003
├── edge-cases.spec.ts          # generated from EC-001..EC-005
└── visual.spec.ts              # screenshot grid
.specs/features/<feature>/
├── baselines/
│   └── <screen>.png             # captured (if --update)
└── checks/<date>-test.md        # AC coverage report
```

### Aligned / Drift / Missing

- **Aligned:** All AC scaffolded, all tests pass, visual diff 0 across all screens. Exit 0 with `Visual: N baselines · 0 diff`.
- **Drift:** Some AC have no test (gap), or pixel diff exceeds threshold on a screen. Exit 1 with a per-AC and per-screen report.
- **Missing:** No `<surface>` testDir configured, or no Playwright config detected. Exit 2 naming the surface and the recovery command.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Single surface, cached browsers | 20–60s | spec count |
| Visual + screenshot capture | 60–180s | screen count |
| Multi-surface (web + native) | 120–600s | converge cost |

### Edge Cases

- New screen mentioned in `spec.md` but missing PNG mockup: report flags `[no mockup]` and falls back to a layout-only baseline.
- Driver in `--migrate` mode: tests are regenerated under the new naming convention; old `.skip` versions are kept until `--commit`.
- `--regenerate-missing` without `--confirm` is a read-only preview; with `--confirm`, generate missing test sources only. `--dry-run` overrides confirmation. Neither mode captures, approves, deletes or synchronizes visual baselines.
- Visual gate result is always one of `PASS | FAIL | BLOCKED`; `/spec-implement` consumes this line during Phase 6.5.

### Post-run Actions

- **After an executed run only:** baselines/checks may be committed through the separate Git workflow; preview and regeneration-only runs do not acquire publication obligations.
- **On drift:** open the gap report, fix code or update spec; re-run with `--update` when ready to re-baseline.
- **On blocked:** create the surface entry in `.specs/surfaces.yaml`, then re-run.

## C51 child transport

- UI success returns actual existing paths in canonical PHASE_RESULT JSON `extra.runner_build_manifest` and `extra.penflow_validation_path`; they come from the completed runner and current validation, with no synthesized values. Missing, stale or malformed transport keeps UI closure blocked. Non-UI omits these inputs.

## Typed acceptance evidence (078 policy2)

- Review explicit documentary ACs through existing native acceptance preparation/ingestion; retain actual input manifests and raw independent output. Default ACs require execution proof.
- Require the complete immutable AC conjunction at prove/archive/verify-output: documentary `acceptance_review_receipt_path` plus mapped `execution_receipt_path` where each kind applies. Missing, stale or substituted proof cannot complete the feature; policy1 archives retain their original interpretation.
- **Read** [Goal review identity](../../../system/review-protocol.md#goal-review-identity) before emitting a model-bound acceptance goal, including when no semantic-review task exists.

- Full functional suite DoD uses typed execution evidence and is inactive for audit/dry-run/regeneration/visual-only. An active functional suite must pass before visual capture; its failure skips Phase 4.5. Visual-only records the functional suite as `not_run`, proceeds with visual runners/gates and retains its applicable visual receipts; it never claims full-suite PASS. No collection goal without a selected feature invents global AC coverage; final acceptance remains scoped to the actual feature and immutable inventory. Historical immutable contracts are not reclassified.

- Generated-file validation is documentary syntax evidence only: use the skill’s verified non-executing parsers; no test collection, imports/hooks, app execution, baseline or runtime-report writes. Actual runtime outcomes are deferred to the applicable Phase 4/4.5 execution/visual receipts.
- Penflow web screenshots are captured under `.specs/features/<feature>/run/<run-id>/<target>/`, certified and validated for that exact run, then approved/promoted through the existing flow; no direct capture into feature/design baselines.
