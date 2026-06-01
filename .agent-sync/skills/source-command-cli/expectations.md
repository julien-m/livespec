---
command: source-command-cli
contract_version: "1.0"
last_reviewed: 2026-06-01
---

# Expectations — /cli

## 1. Purpose

Interactive picker for the unified `livespec` CLI surface — routes the user to the right subcommand (test / coverage / drivers / mutation / preflight) and runs it with the right flags.

## 2. Preconditions

- `cwd` is inside a project whose first ancestor contains `.specs/`.
- `docs/cli-reference.md` is readable (canonical flag/exit-code reference).
- `livespec` is resolvable on `PATH`.

## 3. Observable Signals

**stdout must_contain:**
- "LIVESPEC"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- "_(none — the picker delegates to `livespec`; effects depend on the chosen subcommand)_"

**update:**
- "_(subcommand-dependent: coverage/mutation may write `--report-path`)_"

**optional:**
- "_(report artifacts under the path passed to the subcommand)_"

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- "_(none — read-only unless the chosen subcommand writes a report)_"

**forbidden changes:**
- `src/`

**commit expectations:**
- "_(none — the picker never commits)_"

## 6. Produced Artifacts

- Structured `LIVESPEC <subcommand> · ...` summary line printed to stdout.
- Any report file produced by the delegated subcommand (`--report-path`).

## 7. Exit Codes

| Code | Meaning | Operator action |
|------|---------|-----------------|
| 0    | success | review the summary line |
| 1    | failure / threshold not met | inspect the subcommand output |
| 2    | usage or precondition error | fix arguments and retry |
| 3    | coverage/threshold gate failed | raise coverage or adjust threshold |
| 4    | mutation gate failed | inspect surviving mutants |
| 5    | preflight manifest invalid | run `livespec preflight --fix` |

## 8. Outcome Matrix

- **success:** the chosen subcommand runs and exits 0 with a summary line.
- **drift:** the summary line is missing after a nominal run.
- **blocked:** no `.specs/` ancestor, `livespec` missing, or reference unreadable.
- **error:** the subcommand crashes or emits a traceback.

## 9. Runtime Profile

- Typical range: 1–120 seconds.
- Factors: chosen subcommand (drivers is instant, mutation is slow), project size.

## 10. Post-run Checks

- [ ] The structured `LIVESPEC <subcommand>` summary line is surfaced.
- [ ] The exit code is reported to the user.
- [ ] Non-zero exits include a proposed next step from `docs/cli-reference.md`.

## 11. Troubleshooting

- **Symptom:** exit 5
  **Cause:** preflight manifest is invalid or out of date
  **Fix:** run `livespec preflight --fix`

- **Symptom:** no project root found
  **Cause:** `cwd` has no `.specs/` ancestor
  **Fix:** run from the repository root containing `.specs/`

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "LIVESPEC"
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output

```
$ /cli drivers --json
LIVESPEC drivers · 3 drivers · primary=pytest
```

### Files Produced

```
_(none for drivers; coverage/mutation write to --report-path when given)_
```

### Aligned / Drift / Missing

- **Aligned:** summary line printed, exit code reported.
- **Drift:** subcommand ran but no summary line surfaced.
- **Missing:** `.specs/` ancestor, `livespec` binary, or `docs/cli-reference.md` absent.

### Runtime Profile

| Scenario | Duration | Driver |
|----------|----------|--------|
| drivers | 1–3s | registry scan |
| coverage | 5–30s | diff vs base branch |
| mutation | 30–120s | mutant generation |

### Edge Cases

- `/cli` with no args asks one question, then runs with defaults.
- Forwarded args (`/cli test --mutation`) run verbatim.
- Exit 5 always maps to `livespec preflight --fix`.

### Post-run Actions

- Surface the summary line so CI logs share the same shape.
- On non-zero exit, propose the next step from the reference.
- Use `/spec.test` for deeper coverage workflows.
