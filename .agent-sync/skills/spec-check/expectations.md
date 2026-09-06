---
command: spec-check
contract_version: "1.0"
last_reviewed: 2026-09-05
---

# Expectations — /spec-check

## 1. Purpose

Verify spec vs code alignment and produce a gap report.

## 2. Preconditions

- `.specs/features/<feature>/spec.md` and implementation.md exist.

## 3. Observable Signals

**stdout must_contain:**
- "gap report"
- "checks"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/features/<feature>/checks/<date>-check.md`

**update:**
- _(none)_

**optional:**
- `penflow/compare-report.json`
- `penflow/review-report.md`
- `penflow/fix-report.md`

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

- path: `.specs/features/<feature>/checks/<date>-check.md`
  must_contain_sections:
  - "Gap Report"
  - "Findings"
- stdout marker (`--pre-impl` only): `## Specification Analysis Report` — read-only mode; creates no `checks/`, no changelog, no `src/`; exit 1 iff any CRITICAL or HIGH finding
- stdout marker: `Penflow Contract Verdict: ABSENT | READY | PASS | FAIL | BLOCKED`
  - `ABSENT` / `READY`: unrequired non-UI or preparation inspection only, `certified: false`.
  - `PASS`: installed Penflow revalidated the cumulative report for the caller-required profile and current report/scope/build bindings; `certified: true`.
  - `FAIL` / `BLOCKED`: rejected, missing, stale or incompatible required evidence; raw compare PASS never substitutes for certification.

### C51 stage evidence

- Read-only --pre-impl/tree-only/preparation checks report readiness without runtime proof. UI implementation closure audits revalidate existing implementation evidence with the independently supplied runner manifest; they do not generate reports or captures. Missing proof blocks certification.

## 7. Exit Codes

| Code | Meaning | Operator action |
|------|---------|-----------------|
| 0    | success | nothing |
| 1    | drift   | inspect report, fix divergence |
| 2    | blocked | restore precondition, retry |
| 6    | visual gate FAIL (link copy, runtime under design/screens, alignment FAIL) | run `livespec visual-gate cleanup --feature <slug> --dry-run` then `/spec-fix` |
| 7    | visual gate BLOCKED (missing mockup/baseline/compare report, weak signals only) | restore prereqs, no auto-PASS |

## 7b. Visual Gate (required for VISUAL features)

`/spec-check` MUST call `livespec visual-gate certify --feature <slug> --command spec-check --target <t> --run-id <run-id> --json`, then `livespec visual-gate validate --feature <slug> --command spec-check --target <t> --receipt <receipt-path> --json`, and surface the verdict literally. Exit 0/6/7 propagate.

Nested invocation: when `--fix` is requested, `/spec-fix` is called through an independent sub-agent (Task tool) with its own goal scope; the parent `/spec-check` goal is preserved. After the sub-agent returns, the gate is re-run; the parent step only proves `complete` when the second gate exit is 0.

A step listed in the goal MUST NOT be marked done while the gate exit is non-zero; "skipped due to missing prerequisites" is BLOCKED, not PASS.

## 8. Outcome Matrix

- **success:** every `must` rule passes, exit_code == 0
- **drift:** at least one `must` rule fails, command exited 0
- **blocked:** precondition missing or artifact missing
- **error:** command itself crashed (exit_code != 0)

## 9. Runtime Profile

- Typical range: 15–300 seconds
- Factors: Code size, spec depth

## 10. Post-run Checks

- [ ] checks/<date>-check.md exists and is readable

## 11. Troubleshooting

- **Symptom:** Gap report empty
  **Cause:** No anchors found
  **Fix:** Ensure @spec comments are in the code

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "gap report"
    - contains: "Penflow Contract Verdict"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--pre-impl"
      replace_base: true
      must:
        - contains: "Specification Analysis Report"
```

> **`--pre-impl` mode (read-only):** `replace_base: true` makes this branch the **sole** verify contract in `--pre-impl` — the base rules (`exit_code: 0`, `gap report`, `Penflow Contract Verdict`) are **machine-dropped**, not merely documented as inapplicable, and a non-zero exit no longer classifies as `error` (verify-output engine, C14). So a legitimate blocking analysis (exit 1 = any CRITICAL or HIGH) yields a non-error outcome.
>
> **Read-only enforcement (C15):** the guarantee that `--pre-impl` writes no `checks/`, no changelog, and no `src/` is enforced **structurally** by the CLI early-exit branch (`validator/cli.py` — `--pre-impl` resolves, renders, and `raise typer.Exit(...)` before any writing branch) and proven by the CLI zero-write test (`tests/test_pre_impl_analysis_cli.py`). It is intentionally **not** expressed as `must_not: produces_artifact <dir>` here: those paths (`checks/`, `.specs/changelog.md`, `src/`) routinely **preexist** from normal runs, so an existence-based `must_not` would false-FAIL a clean read-only run.

## 13. Demo Session

### Live Console Output

```
$ /spec-check <feature>
> Scanning code for @spec anchors → 27 matches
> Cross-referencing with spec.md FR/AC → 2 unmapped FRs
> Visual fidelity: 12/13 screens match (1 drift: <screen>)
> Wrote .specs/features/<feature>/checks/<date>.md
exit 1
```

### Files Produced

```
.specs/features/<feature>/checks/<date>.md   # gap report
```

### Aligned / Drift / Missing

- **Aligned:** every FR/AC has at least one `@spec` anchor in code; visual diff < threshold for every screen. Exit 0.
- **Drift:** unmapped FR/AC, missing test, or visual drift > threshold. Exit 1, gap report names each issue.
- **Missing:** spec.md absent or `@spec` anchor convention not configured. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Code-only check | 10–30s | ripgrep span |
| Code + visual | 30–120s | screenshot count |
| Code + visual + surfaces | 60–300s | surface count |

### Edge Cases

- Code has a `@spec` anchor pointing to a deleted FR: check reports `orphan anchor`.
- Visual driver disabled: only structural check runs.
- `--surfaces` flag: detects drift between `.specs/surfaces.yaml` and the actual filesystem.

### Post-run Actions

- **On success:** done.
- **On drift:** run `/spec-fix <feature>` for visual drift, or edit code/spec for structural drift.
- **On blocked:** run `/spec-specify` first.
