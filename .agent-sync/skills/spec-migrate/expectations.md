---
command: spec-migrate
contract_version: "1.0"
last_reviewed: 2026-06-07
---

# Expectations — /spec-migrate

## 1. Purpose

Upgrade a LiveSpec project to the latest version by running pending migrations.

## 2. Preconditions

- `.specs/` directory exists with a previous LiveSpec version.

## 3. Observable Signals

**stdout must_contain:**
- "migration"
- "complete"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- _(none)_

**update:**
- `.specs/spec-system.md`

**optional:**
- `.specs/migrations.log`

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/`

**forbidden changes:**
- `unrelated paths`

**commit expectations:**
- `chore(spec): migrate to <version>`

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

- Typical range: 5–120 seconds
- Factors: Number of pending migrations and project size

## 10. Post-run Checks

- [ ] spec-system.md version matches LiveSpec checkout
- [ ] No legacy file shape remains

## 11. Troubleshooting

- **Symptom:** Conflicting custom edits
  **Cause:** User changed templated files
  **Fix:** Resolve manually then re-run

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "migration"
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output

```
$ /spec-migrate
> Current project version: v2 · LiveSpec repo version: v9
> Migrations to apply: 7 (v3 → v9)
> Applying v3: rename .specs/specs/ → .specs/features/
> ... (steps 2-6 elided)
> Applying v9: write .specs/surfaces.yaml
> All migrations applied successfully
exit 0
```

### Files Produced

```
.specs/livespec-version       # bumped to the latest version
.specs/<various artifacts>    # per migration
```

### Aligned / Drift / Missing

- **Aligned:** every migration applied, livespec-version matches repo VERSION, no manual fixups required. Exit 0.
- **Drift:** a migration encountered conflicting custom edits and skipped the file; report names it. Exit 1.
- **Missing:** `.specs/` not initialized. Exit 2.

### Runtime Profile (scenarios)

| Scenario | Duration | Driver |
|----------|----------|--------|
| One migration | 1–5s | file count |
| Multiple structural | 5–30s | rename volume |
| Full v1 → v9 catch-up | 30–120s | feature count |

### Edge Cases

- `--dry-run`: print the migration plan without writing.
- A migration fails mid-way: spec-migrate rolls back the partial step, leaves a clean state.
- Custom hooks reference paths that the migration renamed: migrate updates the references.

### Post-run Actions

- **On success:** review the changelog entry, commit.
- **On drift:** open the skipped file, apply the migration manually.
- **On blocked:** run `/spec-init`.
