---
command: spec-refresh-from-brainstorm
contract_version: "1.0"
last_reviewed: 2026-06-26
---

<!-- @spec(FR-004) -->

# Expectations — /spec-refresh-from-brainstorm

## 1. Purpose

Sync brainstorm lifecycle deltas into LiveSpec specs through an interactive Impact Report.

## 2. Preconditions

- `brainstorm/` is a symlink in the project root.
- `brainstorm/handoff/livespec/lifecycle/log.ndjson` is readable, or legacy `brainstorm/lifecycle/log.ndjson` is readable.
- `.specs/` exists.

## 3. Observable Signals

**stdout must_contain:**
- "Impact Report"
- "spec-refresh-from-brainstorm"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/features/`

**update:**
- `.specs/features/`
- `brainstorm/handoff/livespec/lifecycle/.refresh-cursor` or legacy `brainstorm/lifecycle/.refresh-cursor`

**optional:**
- `brainstorm/handoff/livespec/lifecycle/.refresh-deferred.yaml` or legacy `brainstorm/lifecycle/.refresh-deferred.yaml`

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/`
- the resolved lifecycle `.refresh-cursor`

**forbidden changes:**
- `src/`

**commit expectations:**
- `chore: refresh brainstorm sync cursor (<event_id>)`

## 6. Produced Artifacts

- Impact Report printed to stdout.
- Optional new or status-updated feature specs under `.specs/features/`.

## 7. Exit Codes

| Code | Meaning | Operator action |
|------|---------|-----------------|
| 0    | success | review applied actions |
| 1    | drift   | inspect report and rejected expectations |
| 2    | blocked | restore symlink/log preconditions and retry |

## 8. Outcome Matrix

- **success:** deltas are read, chain validation passes, and confirmed actions are applied.
- **drift:** expected files or output are missing after a nominal run.
- **blocked:** symlink is missing, log is unreadable, or `prev_hash` chain validation fails.
- **error:** command crashes or emits a traceback.

## 9. Runtime Profile

- Typical range: 5–45 seconds.
- Factors: lifecycle log size, number of deltas, number of interactive actions.

## 10. Post-run Checks

- [ ] Impact Report lists actions, signalements, and no-op events.
- [ ] Cursor advances to the last validated event.
- [ ] No `.specs/` mutation occurs without explicit `o` confirmation.

## 11. Troubleshooting

- **Symptom:** symlink missing
  **Cause:** project is not linked to a brainstorm project
  **Fix:** run `ln -s ~/projects/project-brainstorm/projects/<slug> brainstorm`

- **Symptom:** log corrupted
  **Cause:** an event `prev_hash` does not match the previous canonical event
  **Fix:** repair the brainstorm lifecycle log before retrying

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "Impact Report"
    - contains: "spec-refresh-from-brainstorm"
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-refresh-from-brainstorm
# Impact Report — spec-refresh-from-brainstorm
Events lus: 2
Action [1/1]: Créer — onboarding-reminder
```

### Files Produced

```
.specs/features/NNN-onboarding-reminder/spec.md
brainstorm/handoff/livespec/lifecycle/.refresh-cursor
```

The cursor records the last validated event.
Deferred actions may create `.refresh-deferred.yaml`.

### Aligned / Drift / Missing

- **Aligned:** report printed, confirmed action applied, cursor advanced.
- **Drift:** cursor or expected `.specs/` update missing after confirmation.
- **Missing:** symlink, lifecycle log, or `.specs/` directory absent.

### Runtime Profile

| Scenario | Duration | Driver |
|----------|----------|--------|
| No deltas | 1–5s | log scan |
| Few actions | 5–20s | interactive confirmations |
| Long history | 20–45s | hash verification |

### Edge Cases

- First run has no cursor and reads all events.
- Corrupted `prev_hash` blocks before any `.specs/` write.
- Mutation events read `impacts.yaml`, not the quick event index.

### Post-run Actions

- Review the Impact Report before confirming actions.
- Commit `.specs/` and cursor changes only after human approval.
- Re-run when new brainstorm lifecycle events appear.
