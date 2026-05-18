---
command: spec-verify-output
contract_version: "1.0"
last_reviewed: 2026-05-18
---

# Expectations — /spec-verify-output

## 1. Purpose

Verify a command's latest run artifact against its expectations contract.

## 2. Preconditions

- `.agent-sync/skills/<X>/expectations.md` exists (or a project override).
- `.specs/.runs/<X>-*.json` exists.

## 3. Observable Signals

**stdout must_contain:**
- "verify-output"
- "outcome"

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
- `src/`
- `.specs/`

## 5. Git Effects

**expected dirty paths:**
- _(none)_

**forbidden changes:**
- `any`

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

- Typical range: 1–10 seconds
- Factors: Artifact size (stdout/stderr length)

## 10. Post-run Checks

- [ ] Report mentions outcome=success|drift|blocked|error

## 11. Troubleshooting

- **Symptom:** blocked: no artifact
  **Cause:** Command never ran
  **Fix:** Run the command at least once, then re-verify

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "outcome"
  may:
    - contains: "PASS"
  must_not:
    - contains: "Traceback"
  when:
    - flag: "--json"
      must:
        - contains: '"outcome"'
```

## 13. Demo Session

### Live Console Output

```
$ livespec verify-output specify
verify-output  command=specify
source         .agent-sync/skills/spec-specify/expectations.md
artifact       .specs/.runs/specify-2026-05-12T10-00-00.json

verb      kind                  status    detail
--------------------------------------------------------------------------------
must      exit_code             PASS      exit_code expected=0 actual=0
must      contains              PASS      substring 'spec.md created'
must_not  contains              PASS      substring 'Traceback'

outcome   success
exit_code 0
```

### Files Produced

```
(no filesystem writes in default mode; --save under --preview writes .specs/.previews/)
.specs/.previews/<name>-<timestamp>.md   # only when --preview --save
```

### Aligned / Drift / Missing

- **Aligned:** all `must` rules PASS, exit 0.
- **Drift:** at least one `must` rule FAILS but the run itself exited 0; outcome `drift`, exit 1.
- **Missing:** no run artifact, missing expectations file, or malformed override; outcome `blocked`, exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small artifact | < 1s | rule count |
| Visual when-branch active | 1–5s | filesystem walks |
| Preview mode | 1–3s | project scan |

### Edge Cases

- `--preview`: skips artifact resolution entirely; produces a Markdown report from Section 13 instantiated with project data.
- `--preview --save`: writes the rendered Markdown to `.specs/.previews/<command>-<ISO>.md`.
- `--json`: emits a JSON envelope (or `{command, project_root, timestamp, markdown}` under `--preview`).

### Post-run Actions

- **On success:** done; CI may archive the report.
- **On drift:** inspect the failing rule's `detail`, fix the command or the expectation.
- **On blocked:** run the command at least once (`livespec run wrap <cmd>` produces the artifact), or fix the override file.
