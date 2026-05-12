---
command: check
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.check

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
- _(none)_

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
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output

```
$ /spec.check <feature>
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
- **On drift:** run `/spec.fix <feature>` for visual drift, or edit code/spec for structural drift.
- **On blocked:** run `/spec.specify` first.
