---
command: spec-hooks
contract_version: "1.0"
last_reviewed: 2026-05-26
---

# Expectations — /spec-hooks

## 1. Purpose

Show, create, or edit lifecycle hooks for a command.

## 2. Preconditions

- `.specs/` exists.

## 3. Observable Signals

**stdout must_contain:**
- "hooks"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/hooks/`

**update:**
- `.specs/hooks/`

**optional:**
- `.specs/hooks/before-<cmd>.md`
- `.specs/hooks/after-<cmd>.md`

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/hooks/`

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

- Typical range: 1–30 seconds
- Factors: Interactive editing time

## 10. Post-run Checks

- [ ] Hook file present at the requested path

## 11. Troubleshooting

- **Symptom:** Hook not picked up
  **Cause:** Wrong level
  **Fix:** Hooks resolve global -> project -> local

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "hooks"
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-hooks plan
> Resolved hooks for "plan":
> [global] ~/.claude/livespec/hooks/before-plan.md
> [project] .specs/hooks/before-plan.md
> Mode: extend (chain executes both)
exit 0
```

### Files Produced

```
(read-only — prints hook chain to stdout)
```

### Aligned / Drift / Missing

- **Aligned:** hook chain is printed with file paths and mode. Exit 0.
- **Drift:** local hook declares `mode: override` but the same level lacks content. Exit 1 (validation).
- **Missing:** the command name doesn't exist. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Single command resolution | 1–3s | filesystem only |
| `--create` | 3–10s | template scaffold |
| `--edit` | depends on editor | user time |

### Edge Cases

- `--create` on a level that already exists: hooks prompts before overwriting.
- `mode: override` at local level: chain shortens to one entry; spec-hooks marks the chain explicitly.
- Hook file is invalid YAML frontmatter: spec-hooks reports the parse error.

### Post-run Actions

- **On success:** review the chain; if customization is needed, run `--create local`.
- **On drift:** fix the offending hook's frontmatter.
- **On blocked:** verify the command spelling.
