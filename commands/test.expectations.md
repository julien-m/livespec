---
command: test
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.test

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

- Typical range: 30–1200 seconds
- Factors: Suite size, parallel workers, visual diff cost

## 10. Post-run Checks

- [ ] Coverage report present in checks/
- [ ] Suite exits 0

## 11. Troubleshooting

- **Symptom:** No tests collected
  **Cause:** Missing driver
  **Fix:** Run /spec.preflight or /spec.driver list

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
```

## 13. Demo Session

### Live Console Output

```
$ /spec.test <feature> --visual
> Auditing AC coverage: <feature> has 12 ACs, 9 covered, 3 missing
> Generating 3 missing scaffolds in apps/web/tests/e2e/<feature>/
> Running 38 specs across 1 surface (web)
> Visual: 13 baselines · 0 diff · 1 missing (<screen>)
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

### Post-run Actions

- **On success:** commit baselines + checks file, push.
- **On drift:** open the gap report, fix code or update spec; re-run with `--update` when ready to re-baseline.
- **On blocked:** create the surface entry in `.specs/surfaces.yaml`, then re-run.
