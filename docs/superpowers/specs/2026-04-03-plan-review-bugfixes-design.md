# Design: Fix plan-review control-flow bugs

## Context

3 confirmed bugs in the `--plan-review` feature (Codex audit 2026-04-03):

1. **P1 — Silent success on crash**: `_run_single_review()` catches exceptions and appends to `review_result.errors`, but CLI only checks `has_blocking` (findings with `severity == ERROR`). Exit 0 even when all reviews failed.
2. **P2 — PATH scoping ignored**: `run_plan_review()` iterates all features in graph regardless of `path` argument. User expects scoping like `validate_all()`.
3. **P2 — `--warn-only` bypassed**: `raise typer.Exit(1 if has_blocking else 0)` at line 196 exits before reaching the shared `warn_only` guard at line 345.

## Design

### Fix 1: Errors as blocking (cli.py)

After the errors display loop (line 187-188), add:

```python
if review_result.errors:
    has_blocking = True
```

This ensures any review failure causes exit 1. Combined with `warn_only`, errors are also suppressed (advisory mode contract).

### Fix 2: PATH scoping (orchestrator.py + cli.py)

**CLI side** — resolve `path` to a feature `dir_name`:

```python
def _resolve_feature_filter(path: Path | None, specs_root: Path) -> str | None:
    """Resolve a path to a feature dir_name for scoping, or None for all."""
    if path is None:
        return None
    try:
        rel = path.resolve().relative_to((specs_root / "features").resolve())
    except ValueError:
        return None  # path outside features/ — review all
    return rel.parts[0] if rel.parts else None
```

Pass result to orchestrator: `run_plan_review(..., feature_filter=filter_name)`.

**Orchestrator side** — add `feature_filter: str | None = None` param to `run_plan_review()`. In the feature loop:

```python
for feature in graph.features:
    if feature_filter and feature.dir_name != feature_filter:
        continue
    ...
```

If `feature_filter` is set but no matching feature found, append an error to `check_result.errors`.

### Fix 3: warn_only (cli.py)

Replace the exit line:

```python
# Before
raise typer.Exit(1 if has_blocking else 0)

# After
raise typer.Exit(0 if warn_only else (1 if has_blocking else 0))
```

### Testing

| Test case | Expected |
|-----------|----------|
| All reviews crash, `warn_only=False` | exit 1 |
| All reviews crash, `warn_only=True` | exit 0 |
| Blocking finding, `warn_only=True` | exit 0 |
| Blocking finding, `warn_only=False` | exit 1 |
| `path=features/001/spec.md` | only feature 001 reviewed |
| `path=features/nonexistent/` | error, exit 1 |
| `path=None` | all features reviewed |

## Files modified

- `validator/cli.py` — fixes 1, 2, 3
- `validator/orchestrator.py` — fix 2 (feature_filter param)
- `tests/test_plan_review.py` — new test cases
