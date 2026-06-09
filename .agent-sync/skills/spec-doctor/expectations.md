---
command: spec-doctor
contract_version: "1.0"
last_reviewed: 2026-06-09
---
<!-- LiveSpec traceability anchors -->
<!-- @spec(FR-011) -->


# Expectations — /spec-doctor

## 1. Purpose

Run a project-level health audit that orchestrates coherence validation and detects stale mappings, missing tests, missing `@spec(...)` traceability anchors, unenforced hooks, runner drift, lifecycle ambiguity, visual orphans, and cleanup safety.

## 2. Preconditions

- `.specs/` exists.

## 3. Observable Signals

**stdout must_contain:**
- "LiveSpec doctor"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- _(none)_

**update:**
- _(none)_

**optional:**
- _(none)_

**forbidden:**
- `.specs/features/`
- `.specs/design/`
- `tests/`

## 5. Git Effects

**expected dirty paths:**
- _(none)_

**forbidden changes:**
- `any`

**commit expectations:**
- _(none)_

## 6. Produced Artifacts

- JSON report on `--format json`
- Text report on compact/full output

## 7. Exit Codes

| Code | Meaning | Operator action |
|------|---------|-----------------|
| 0 | OK | nothing |
| 1 | FAIL or any drift finding; strict promotes warnings to errors | inspect findings, fix drift |
| 2 | usage/precondition error | fix invocation or initialize LiveSpec |

## 8. Outcome Matrix

- **success:** no findings, exit_code == 0
- **drift:** findings present, report rendered, exit_code == 1
- **blocked:** `.specs/` missing or invalid invocation
- **error:** command crashed or emitted traceback

## 9. Runtime Profile

- Typical range: 1–10 seconds
- Factors: feature count, implementation map size, coherence rule count

## 10. Post-run Checks

- [ ] JSON output has `status`, `summary`, `findings`, and `cleanup_actions`.
- [ ] `--fix-plan` leaves the working tree unchanged.
- [ ] `--apply-cleanup` refuses destructive active spec/test/evidence deletion.

## 11. Troubleshooting

- **Symptom:** `hook_unenforced`
  **Cause:** No LiveSpec validation hook found.
  **Fix:** Install or update git hooks.

## 12. Verify Contract

```yaml
verify:
  must:
    - contains: "LiveSpec doctor"
  may:
    - exit_code: 1
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--format json"
      must:
        - contains: '"status"'
        - contains: '"findings"'
```

## 13. Demo Session

### Live Console Output

```
$ /spec-doctor
> LiveSpec doctor: FAIL
> summary: errors=1 warnings=2 infos=0 findings=3
exit 1
```

### Files Produced

```
(read-only by default)
```

### Aligned / Drift / Missing

- **Aligned:** no stale mappings, missing traceability anchors, runner gaps, hook gaps, lifecycle gaps, or visual orphans. Exit 0.
- **Drift:** findings are reported with category, severity, evidence, and suggested action. Exit 1.
- **Missing:** `.specs/` not initialized. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|---|---:|---|
| Small project | < 2s | file scan |
| Large project | 2–10s | feature count |

### Edge Cases

- `--strict`: promotes warnings to errors for CI.
- `--fix-plan`: proposes cleanup without file changes.
- `--apply-cleanup`: refuses destructive cleanup until a future archive contract exists.

### Post-run Actions

- **On success:** continue normal development.
- **On drift:** run `/spec-fix <feature>` or update runner/hooks/lifecycle metadata.
- **On blocked:** run `/spec-init` first.
