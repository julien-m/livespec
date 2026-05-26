---
command: spec-refresh-conventions
contract_version: "1.0"
last_reviewed: 2026-05-26
---

# Expectations — /spec-refresh-conventions

## 1. Purpose

Manually initialize or refresh project conventions from the LiveSpec stack.

## 2. Preconditions

- `.specs/stacks/_default.md` exists.

## 3. Observable Signals

**stdout must_contain:**
- "conventions"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.conventions/`

**update:**
- `.conventions/index.md`
- `.conventions/manifest.yaml`

**optional:**
- _(none)_

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.conventions/`

**forbidden changes:**
- _(none)_

**commit expectations:**
- `chore(conventions): refresh`

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

- Typical range: 5–60 seconds
- Factors: Stack size, ai-ressources availability

## 10. Post-run Checks

- [ ] .conventions/index.md is present and non-empty

## 11. Troubleshooting

- **Symptom:** ai-ressources missing
  **Cause:** Wrong path
  **Fix:** Set $AIRESOURCES and retry

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "conventions"
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-refresh-conventions
> Reading .specs/stacks/_default.md (<stack>)
> Generating .conventions/manifest.yaml + index.md
> 4 sub-domains detected: code, design-tokens, design-components, design-views
exit 0
```

### Files Produced

```
.conventions/manifest.yaml    # machine-readable
.conventions/index.md         # routing table
```

### Aligned / Drift / Missing

- **Aligned:** manifest.yaml and index.md exist with matching sub-domains. Exit 0.
- **Drift:** manifest declares sub-domains the source files no longer define. Exit 1.
- **Missing:** ai-ressources path unresolved or stack file absent. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Minimal stack | 1–5s | sub-domain count |
| Full stack | 5–20s | source file count |
| With `--full` re-detect | 20–60s | exclusion analysis |

### Edge Cases

- `--full`: re-detects sub-domains from scratch (used after stack identity change).
- ai-ressources repo not cloned locally: refresh emits a clear error with the expected `$AIRESOURCES` path.
- Old compiled-format `.conventions/` detected: refresh prompts migration.

### Post-run Actions

- **On success:** subsequent commands auto-load the new conventions.
- **On drift:** run `--full` to rebuild from scratch.
- **On blocked:** set `AIRESOURCES` env var, or run `/spec-init` first.
