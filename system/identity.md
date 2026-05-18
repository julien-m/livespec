# Identity Resolution

> Single source of truth for `feature_slug` derivation.
> Implementation: [`validator/identity.py`](../validator/identity.py).
>
> **@spec FR-001:** Single `resolve_feature_slug(description)` helper — [`.specs/features/013-state-model-identity-resolution/spec.md#fr-001`](../.specs/features/013-state-model-identity-resolution/spec.md#fr-001)

---

## Why this exists

Before Chantier 4, `commands/spec-feature.md` propagated the literal placeholder string `NNN-feature-name` into runtime CLI calls (`livespec pipeline init --feature NNN-feature-name`) and into the Universal Agent Context dispatched to subagents. The placeholder was never resolved before side-effects, leading to:

- Pipeline state files initialised with literal `NNN-feature-name`
- Subagent payloads carrying an unresolved identifier
- Files written to a literal `.specs/features/NNN-feature-name/` directory

This document defines the canonical rules; the Python module enforces them.

---

## The `feature_slug` regex

```
^\d{3}(\.\d+)?-[a-z0-9]+(-[a-z0-9]+)*$
```

- 3-digit zero-padded NNN (`001`–`999`)
- Optional `.M` sub-feature suffix (e.g. `005.1`, `005.2`) — used when a feature is split into derivative work tracked under the same parent number
- A hyphen separator
- Kebab-case name (lowercase letters and digits, hyphen-separated, no leading/trailing hyphen)

Examples:
- `013-state-model-identity-resolution` (top-level feature)
- `005.1-behavioral-tdd-audit` (sub-feature of 005)

The literal string `NNN-feature-name` MUST never match this regex (the `NNN` part is alphabetic, not digits) and is additionally rejected explicitly by `parse_slug` and `resolve_feature_slug`.

## Resolution rules

| Input                                   | Resolution                                                                                  |
|-----------------------------------------|---------------------------------------------------------------------------------------------|
| Already a valid slug (`013-foo-bar`)    | Return as-is, no NNN allocation                                                             |
| Free-text description (`"Add search"`) | Allocate next NNN by scanning `.specs/features/`, slugify the description, join             |
| Empty / whitespace-only                 | `IdentityResolutionError`                                                                   |
| Literal `NNN-feature-name`              | `IdentityResolutionError`                                                                   |
| Description that slugifies to empty     | `IdentityResolutionError`                                                                   |

NNN allocation is **not atomic** — concurrent runs can collide. Atomicity is the responsibility of [Chantier 3 / Feature 015](../.specs/features/015-global-write-locks/spec.md), which wraps `resolve_feature_slug` with a `mkdir`-based reservation.

## Failure protocol

When a caller receives an unresolvable input, it MUST emit the canonical anti-drift line:

```
BLOCKED at step <N> - state_invalid - feature_slug not resolved (got: "<value>")
```

See [`system/anti-drift-block.md`](anti-drift-block.md) §2 for the full BLOCKED format.

## Public API

```python
from validator.identity import resolve_feature_slug, parse_slug, assert_resolved, FeatureSlug

# Resolve a description or slug
slug: FeatureSlug = resolve_feature_slug("Add user search")

# Parse and validate an existing slug string
slug = parse_slug("013-state-model-identity-resolution")

# Guard: raise if value is not a fully resolved slug
assert_resolved(maybe_slug)
```

## Where this is used

- `commands/spec-feature.md` — Identity Resolution section (calls `resolve_feature_slug` before any side-effect)
- `commands/spec-specify.md` Step 2 (NNN allocation) — uses the same regex
- `agents/livespec-supervisor.md` Activation Contract — calls `assert_resolved` on every payload field
- `agents/livespec-documenter.md` Step 5 (log path) — uses the resolved slug in the log directory name
- `commands/spec-implement.md` Phase 4 (execution log path) — mirrors the documenter convention
- `validator/state_files.py` — `feature_slug` frontmatter field is validated against the same regex

## Migration of legacy artefacts

When migrating an existing project that has files written with the literal placeholder, run:

```bash
grep -r "NNN-feature-name" .specs/features/ commands/ agents/
```

Move/rename any matched files to the resolved slug. The CI regression check defined by [FR-009](#fr-009) prevents the literal from being reintroduced.
