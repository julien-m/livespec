---
command: spec-propose
contract_version: "1.0"
last_reviewed: 2026-05-26
---

# Expectations — /spec-propose

## 1. Purpose

Analyze project context and propose the next feature(s) to build.

## 2. Preconditions

- `.specs/project.md` exists.
- `.specs/roadmap.md` exists (may be empty).

## 3. Observable Signals

**stdout must_contain:**
- "Proposal"
- "next feature"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- _(none)_

**update:**
- `.specs/roadmap.md`

**optional:**
- _(none)_

**forbidden:**
- `.specs/features/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/roadmap.md`

**forbidden changes:**
- _(none)_

**commit expectations:**
- `docs(spec): propose <feature>`

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

- Typical range: 10–120 seconds
- Factors: Project size, number of existing features

## 10. Post-run Checks

- [ ] roadmap.md has a fresh entry under MVP/Post-MVP/Future

## 11. Troubleshooting

- **Symptom:** No proposal returned
  **Cause:** Project lacks signals
  **Fix:** Add detail to project.md and retry

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "Proposal"
  may:
    - contains: "MVP"
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-propose
> Reading project.md, roadmap.md, recent changelog
> Top 3 suggestions:
>   1. Add CSV export · Scope: M · Roles: backend
>   2. Search by date range · Scope: S · Roles: frontend
>   3. Audit log viewer · Scope: M · Roles: full-stack
exit 0
```

### Files Produced

```
(read-only — prints suggestions; nothing written unless --append-roadmap)
```

### Aligned / Drift / Missing

- **Aligned:** ≥ 1 suggestion printed with name, scope, roles, deps. Exit 0.
- **Drift:** roadmap already exhausts the obvious features; suggestions become speculative. Exit 0 (informational).
- **Missing:** project.md absent. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| Small project | 10–30s | LLM call |
| Medium project | 30–90s | history scan |
| Large project | 60–180s | doc depth |

### Edge Cases

- `--append-roadmap`: writes the top-N suggestions to roadmap.md MVP tier.
- Roadmap already has a similar item: propose dedups and links to the existing line.
- LLM rate-limited: propose retries once, then exits 1 with the rate-limit hint.

### Post-run Actions

- **On success:** run `/spec-specify "<chosen suggestion>"`.
- **On drift:** ignore; propose is advisory.
- **On blocked:** run `/spec-init`.
