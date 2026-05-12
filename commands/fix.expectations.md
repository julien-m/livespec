---
command: fix
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.fix

## 1. Purpose

Fix implementation gaps from /spec.check — functional and visual corrections.

## 2. Preconditions

- `A recent `checks/<date>-check.md` exists with non-empty findings.`

## 3. Observable Signals

**stdout must_contain:**
- "fix"
- "applied"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- _(none)_

**update:**
- `src/`
- `.specs/features/<feature>/implementation.md`

**optional:**
- _(none)_

**forbidden:**
- `.specs/features/<feature>/spec.md`

## 5. Git Effects

**expected dirty paths:**
- `src/`

**forbidden changes:**
- `.specs/features/<feature>/spec.md`

**commit expectations:**
- `fix(<feature>): close gap`

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

- Typical range: 30–900 seconds
- Factors: Number of findings, fix complexity

## 10. Post-run Checks

- [ ] Re-running /spec.check shows the gap closed

## 11. Troubleshooting

- **Symptom:** No findings to act on
  **Cause:** Stale check
  **Fix:** Re-run /spec.check first

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "applied"
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output

```
$ /spec.fix <feature>
> Reading checks/<date>.md → 3 issues
> Issue 1/3: visual drift on <screen> → re-rendering component
> Issue 2/3: missing @spec anchor on src/api/foo.ts:45
> Issue 3/3: unmapped FR-008 → added stub test
> All issues addressed — re-run /spec.check to verify
exit 0
```

### Files Produced

```
src/<modified files>
tests/<new or modified tests>
.specs/features/<feature>/implementation.md   # anchors refreshed
```

### Aligned / Drift / Missing

- **Aligned:** every issue from the gap report has a corresponding patch; re-running /spec.check returns 0. Exit 0.
- **Drift:** some issues could not be auto-fixed; the report lists them as `manual`. Exit 1.
- **Missing:** no gap report under `.specs/features/<feature>/checks/`. Exit 2 with recovery `/spec.check first`.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Few small issues | 30–90s | LLM call count |
| Visual drift (multi-screen) | 60–300s | re-render cost |
| Many structural issues | 120–600s | per-issue patch loop |

### Edge Cases

- `--dry-run`: shows the patch plan without writing files.
- Visual fix needs a design mockup change: fix flags it as `manual — update design source`.
- Auto-fix produces a regression in another test: fix rolls back and surfaces the conflict.

### Post-run Actions

- **On success:** re-run `/spec.check <feature>` to confirm zero gaps.
- **On drift:** address the `manual` issues by hand, re-run `/spec.fix`.
- **On blocked:** run `/spec.check <feature>` to generate the gap report.
