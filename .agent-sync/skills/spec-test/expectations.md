---
command: spec-test
contract_version: "1.0"
last_reviewed: 2026-05-22
---

# Expectations — /spec-test

## 1. Purpose

Audit test coverage, generate missing tests, execute the suite, and verify visual fidelity.

## 2. Preconditions

- `.specs/features/<feature>/spec.md` exists.
- `A test driver is configured (`.specs/testing/`).`

## 3. Observable Signals

**stdout must_contain:**
- "passed"
- "test"

**stdout must_not_contain:**
- "Traceback"
- "ERROR collecting"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

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
- browser screenshot evidence under `.specs/features/<feature>/baselines/` or `penflow/screens/`
- `.specs/design/baselines/<feature_slug>/` synced runtime screenshots in the Global LiveSpec Design Registry

**require for UI runs with root `penflow/`:**
- `.specs/design/ui.pen`
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
- stdout marker: `Design Alignment Verdict: PASS | FAIL | BLOCKED` for `--visual` runs when `ui.pen` is present or changed
- stdout marker: `Penflow Contract Verdict: ABSENT | PASS | FAIL | BLOCKED` for UI runs
  - `ABSENT`: no root `penflow/`
  - `PASS`: `actual-ui-tree.json` validates and matches `expected-ui-tree.json`
  - `FAIL`: compare report contains structural drift
  - `BLOCKED`: required artifacts, `actual-ui-tree.json`, or Penflow CLI are missing
  - `BLOCKED`: also required when the Global LiveSpec Design Registry has no matching mockup PNGs under `.specs/design/screens/<feature_slug>/`
  - `BLOCKED`: also required when `--require-mockup-validation` reports missing Mockup Factory proof or visual-evidence status other than `PASS`
  - note: non-UI runs without runtime comparison can report `runtime_comparison: ABSENT` while final verdict remains `PASS` when root Penflow planning artifacts are ready

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

- Typical range: 30–1200 seconds
- Factors: Suite size, parallel workers, visual diff cost

## 10. Post-run Checks

- [ ] Coverage report present in checks/
- [ ] Suite exits 0
- [ ] Penflow UI runs have Global LiveSpec Design Registry artifacts: `.specs/design/ui.pen`, `.specs/design/screens/<feature_slug>/`, `.specs/design/baselines/<feature_slug>/`, `.specs/design/screens/index.md`, and `.specs/design/changelog.md`
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
    - contains: "passed"
  may:
    - contains: "coverage"
  must_not:
    - contains: "Traceback"
    - contains: "ERROR collecting"
  when:
    - flag: "--visual"
      must:
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
- `--regenerate-missing` invoked: only baselines absent on disk are captured; pre-existing baselines are NEVER overwritten without `--update`.
- Visual gate result is always one of `PASS | FAIL | BLOCKED`; `/spec-implement` consumes this line during Phase 6.5.

### Post-run Actions

- **On success:** commit baselines + checks file, push.
- **On drift:** open the gap report, fix code or update spec; re-run with `--update` when ready to re-baseline.
- **On blocked:** create the surface entry in `.specs/surfaces.yaml`, then re-run.
