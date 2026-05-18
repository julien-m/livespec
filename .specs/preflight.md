---
created_at: '2026-04-13'
current_state: Done
feature_slug: '-'
owner_command: spec-preflight
schema_version: 1
updated_at: '2026-04-13'
---

# Preflight Manifest

> Auto-generated from stack by `spec-init --from-code` on 2026-04-13. Editable — changes are preserved on regeneration.

## Tooling

### Python 3.11+

```yaml
check: python3 --version | grep -E "3\.(1[1-9]|[2-9][0-9])"
source: pyproject.toml requires-python ≥3.11
auto_resolve: false
```

**Status:** Verify manually — `python3 --version`

### pip (package manager)

```yaml
check: python3 -m pip --version
source: CI workflow uses pip install -e
auto_resolve: false
```

**Status:** Verify manually — `python3 -m pip --version`

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

## LiveSpec-Managed (auto-generated)

<!-- preflight:livespec:start -->
### node (driver)
- **binary:** `node`
- **verify:** `node --version`
- **install:** `brew install node`
- **severity:** critical
- **source:** stack (driver: node)

### python (driver)
- **binary:** `python3`
- **verify:** `python3 --version`
- **install:** `brew install python`
- **severity:** critical
- **source:** stack (driver: python)
<!-- preflight:livespec:end -->

## User Integrations (optional)

### user-level integrations report

```yaml
check: ls ~/.config/livespec/*.md 2>/dev/null | grep -v provider.py || true
source: validator/integrations.py
status: optional
```

**Status:** Informational only — surfaces which Level 0 markdown integrations
are currently active for the local user. Absence is normal — LiveSpec runs
unchanged without any integration. See `system/integrations.md`.
