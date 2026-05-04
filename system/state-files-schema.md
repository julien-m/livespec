# State Files Frontmatter Schema

> Canonical YAML frontmatter required for `pipeline.md`, `progress.md`, `ship.md`, `preflight.md`.
> Validated by `livespec validate --state-files`.
>
> **@spec FR-005:** State-files schema reference — [`.specs/features/013-state-model-identity-resolution/spec.md#fr-005`](../.specs/features/013-state-model-identity-resolution/spec.md#fr-005)
> **@spec FR-006:** Validator subcommand — [`spec.md#fr-006`](../.specs/features/013-state-model-identity-resolution/spec.md#fr-006)

---

## Required keys

| Key             | Type    | Description                                                                          |
|-----------------|---------|--------------------------------------------------------------------------------------|
| `schema_version`| `int`   | Currently `1`. Bumped on incompatible schema changes; older values trigger a halt.   |
| `owner_command` | `str`   | Slash command that owns this file (`spec.feature`, `spec.implement`, `spec.ship`, `spec.preflight`). |
| `feature_slug`  | `str`   | The resolved `NNN-name` slug, or the literal `"-"` for project-global files (see below). |
| `created_at`    | `str`   | ISO date `YYYY-MM-DD` when the file was first written.                               |
| `updated_at`    | `str`   | ISO date `YYYY-MM-DD` when the file was last modified.                               |
| `current_state` | `enum`  | One of `Pending` / `InProgress` / `Done` / `Blocked` (see [state-machine.md](state-machine.md)). |

When `current_state: Blocked`, an additional non-empty `reason: str` field is required.

## Feature-scoped vs project-global files

| File path                                          | `feature_slug` value                  |
|----------------------------------------------------|---------------------------------------|
| `.specs/features/<slug>/pipeline.md`              | The same `<slug>` (e.g., `013-state-model-identity-resolution`) |
| `.specs/features/<slug>/progress.md`              | The same `<slug>`                     |
| `.specs/ship.md`                                   | Literal `"-"` (project-global)        |
| `.specs/preflight.md`                              | Literal `"-"` (project-global)        |

Project-global files (`ship.md`, `preflight.md` directly under `.specs/`) carry the sentinel `"-"` because they apply across all features in the project. Feature-scoped files carry their owning slug, validated against the canonical regex from [`identity.md`](identity.md).

## Example — `pipeline.md`

```yaml
---
schema_version: 1
owner_command: spec.feature
feature_slug: 013-state-model-identity-resolution
created_at: 2026-05-04
updated_at: 2026-05-04
current_state: InProgress
---
```

## Example — `pipeline.md` in `Blocked` state

```yaml
---
schema_version: 1
owner_command: spec.feature
feature_slug: 013-state-model-identity-resolution
created_at: 2026-05-04
updated_at: 2026-05-04
current_state: Blocked
reason: livespec validate --state-files reports schema violation in progress.md
---
```

## Example — project-global `ship.md`

```yaml
---
schema_version: 1
owner_command: spec.ship
feature_slug: "-"
created_at: 2026-05-04
updated_at: 2026-05-04
current_state: InProgress
---
```

## Validator behaviour

`livespec validate --state-files` walks `.specs/` and validates every file whose basename is in:
```
{pipeline.md, progress.md, ship.md, preflight.md}
```

It reports per-file violations of the form:
```
<path>: [<rule>] <message>
```

Where `<rule>` is one of:
- `missing_key` — required key absent
- `wrong_type` — key present but wrong type
- `wrong_value` — value out of allowed range (e.g., `current_state` not in the enum)
- `wrong_format` — value present but malformed (e.g., date not ISO)
- `placeholder_leak` — `feature_slug` is the literal `NNN-feature-name`
- `missing_reason` — `current_state: Blocked` without `reason`
- `parse_error` — frontmatter parse failed

Exit code: `0` on no violations, `1` otherwise. Add `--warn-only` to always exit `0`.

## Migration of legacy state files

Existing state files created before Chantier 4 generally lack the canonical frontmatter. The validator ships with `--migrate` to add the missing fields in place:

```bash
livespec validate --state-files --migrate
```

**Inference rules:**

| Field | Inferred from |
|-------|---------------|
| `schema_version` | Constant `1` |
| `owner_command` | File basename: `pipeline.md` → `spec.feature`, `progress.md` → `spec.implement`, `ship.md` → `spec.ship`, `preflight.md` → `spec.preflight` |
| `feature_slug` | Path: `.specs/features/<slug>/` → `<slug>`; `.specs/<file>` (project-global) → `"-"` |
| `created_at` | First commit date from `git log --diff-filter=A`; filesystem mtime as fallback |
| `updated_at` | Last commit date from `git log -1`; filesystem mtime as fallback |
| `current_state` | Body markers (`Blocked`/`In Progress`/`Done`); defaults to `Done` for historical files |

**Merge strategy:**

- Missing keys are added.
- Existing keys whose value passes the schema are preserved verbatim.
- Existing keys whose value fails the schema are replaced with the inferred default.
- Body content (after the frontmatter block) is preserved byte-for-byte.

**Output:**

```
Migrated 23 state file(s): 0 added, 4 completed, 19 already compliant.
  /path/to/pipeline.md: completed [feature_slug] (fixed: feature_slug)
  ...
OK: post-migration re-validation confirms 23 file(s) compliant.
```

After migration, the body of each file is intact and the frontmatter is canonical. The migration is idempotent: re-running `--migrate` on an already-compliant tree is a no-op.

Manual editing remains supported and is preferred when you want to set specific values (e.g., a `current_state` other than the inferred default).
