---
command: spec-preflight
contract_version: "1.0"
last_reviewed: 2026-05-26
---

# Expectations — /spec-preflight

## 1. Purpose

Verify tooling, auth, and credentials before autonomous work.

## 2. Preconditions

- `.specs/preflight.md` exists with a manifest.

## 3. Observable Signals

**stdout must_contain:**
- "preflight"
- "ok"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/preflight-report.md`

**update:**
- `.specs/preflight.md`

**optional:**
- _(none)_

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/preflight-report.md`

**forbidden changes:**
- _(none)_

**commit expectations:**
- _(none)_

## 6. Produced Artifacts

- path: `.specs/preflight-report.md`
  must_contain_sections:
  - "Tools"
  - "Status"

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

- Typical range: 5–120 seconds
- Factors: Number of items in the manifest

## 10. Post-run Checks

- [ ] Report lists every tool with ok/missing/auto-installable

## 11. Troubleshooting

- **Symptom:** All missing
  **Cause:** Empty PATH or wrong shell
  **Fix:** Source the shell rc and retry

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "preflight"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--fix"
      must:
        - contains: "installed"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-preflight
> Running 7 checks from .specs/preflight.md
> ✓ git ≥ 2.30
> ✓ python3 ≥ 3.11
> ✓ playwright installed (1.45)
> ⚠ ANTHROPIC_API_KEY missing (warning, not critical)
> Wrote .specs/preflight-report.md — verdict: WARNINGS
exit 0
```

### Files Produced

```
.specs/preflight-report.md     # verdict (READY | WARNINGS | BLOCKED), per-check status
```

### Aligned / Drift / Missing

- **Aligned:** every critical check passes, report verdict READY. Exit 0.
- **Drift:** only warnings; verdict WARNINGS. Exit 0 (non-blocking by design).
- **Missing:** a critical check fails. Exit 2 with the failing check and recovery command.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Pure tooling check | 2–10s | binary lookup |
| Tooling + LLM creds | 5–20s | network |
| Full stack + autofix | 10–60s | autofix loop |

### Edge Cases

- `--light`: runs only critical checks (used by /spec-feature 2.7).
- `--autofix`: attempts to install missing deps when safe.
- Check command crashes: preflight reports `error` for that line, continues.

### Post-run Actions

- **On success:** proceed with `/spec-feature` or the targeted command.
- **On drift:** address the warnings if relevant; no blocker.
- **On blocked:** run the recovery command from the report, re-run preflight.
