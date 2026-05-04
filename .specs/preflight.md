---
created_at: '2026-04-13'
current_state: Done
feature_slug: '-'
owner_command: spec.preflight
schema_version: 1
updated_at: '2026-04-13'
---

# Preflight Manifest

> Auto-generated from stack by `spec.init --from-code` on 2026-04-13. Editable — changes are preserved on regeneration.

## Tooling

### Python 3.11+

```yaml
check: python --version | grep "3\.(1[1-9]|[2-9][0-9])"
source: pyproject.toml requires-python ≥3.11
auto_resolve: false
```

**Status:** Verify manually — `python3 --version` or `python --version`

### pip (package manager)

```yaml
check: pip --version
source: CI workflow uses pip install -e
auto_resolve: false
```

**Status:** Standard with Python installation

### Virtual environment

```yaml
check: ls .venv/bin/python
source: .venv/ directory present in project root
auto_resolve: pip install -e ".[dev]"
```

**Status:** Present (`.venv/` detected)

### livespec CLI (editable install)

```yaml
check: livespec --help
source: pyproject.toml [project.scripts]
auto_resolve: pip install -e ".[dev]"
```

**Status:** Verify with `livespec --help` in active virtualenv

### ruff (linter/formatter)

```yaml
check: ruff --version
source: pyproject.toml [tool.ruff], .ruff_cache/ present
auto_resolve: pip install -e ".[dev]"
```

**Status:** Installed via dev dependencies

### pyright (type checker)

```yaml
check: pyright --version
source: pyproject.toml [tool.pyright]
auto_resolve: pip install pyright
```

**Status:** May need separate install — `pip install pyright`

### pytest

```yaml
check: pytest --version
source: pyproject.toml [project.optional-dependencies.dev]
auto_resolve: pip install -e ".[dev]"
```

**Status:** Installed via dev dependencies

## Authentication

> No authentication required. LiveSpec is a local CLI tool with no hosted services.

## Tokens

### LLM Provider (optional — Layer 4 only)

```yaml
check: ls ~/.config/livespec/provider.py
source: validator/llm_provider.py provider discovery
required: false
note: Only needed for --plan-review, --semantic, --contradiction-only flags
```

**Status:** Optional — Layer 4 features degrade gracefully without it. See `examples/provider-cchub.py` for a template.

## Custom

<!-- preflight:custom:start -->
<!-- Add manual checks here. Use the same ### format as above. Set source: manual -->
<!-- preflight:custom:end -->
