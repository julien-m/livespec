---
title: Default Stack
updated: 2026-04-13
---

# Stack — LiveSpec

> Detected from codebase by `spec-init --from-code` on 2026-04-13.
> All choices are Observed from existing code. See `decisions/` for rationale ADRs.

---

## Core Stack

| Layer | Choice | Version | Evidence | Notes |
|---|---|---|---|---|
| Language | Python | ≥3.11 (3.14 in .venv) | `pyproject.toml` | Primary and only language |
| CLI Framework | Typer | ≥0.12 | `pyproject.toml`, `validator/cli.py` | Auto-generated help, type-safe subcommands |
| Schema Validation | Pydantic | ≥2.7 | `pyproject.toml`, `validator/schemas/` | v2 API with strict typing |
| Markdown Parsing | mistune | ≥3.0 | `pyproject.toml` | Parses spec file content |
| Frontmatter Parsing | python-frontmatter | ≥1.1 | `pyproject.toml` | YAML frontmatter in spec files |
| CLI Output | rich | ≥13.0 | `pyproject.toml` | Colored terminal output, tables |
| YAML | pyyaml | ≥6.0 | `pyproject.toml` | YAML parsing (config, frontmatter) |
| LLM Integration | claude-agent-sdk | ≥0.1.0 (optional) | `pyproject.toml` [integration] | Layer 3/4 — pluggable provider interface |
| Testing | pytest + pytest-asyncio + pytest-xdist | ≥8.0 | `pyproject.toml`, test files | Unit + integration + parallel execution |
| Linter/Formatter | ruff | via `.ruff_cache`, target py311 | `pyproject.toml [tool.ruff]` | Replaces black/isort/flake8 |
| Type Checker | pyright | strict mode | `pyproject.toml [tool.pyright]` | Strict — all types explicit |
| Package Manager | pip + venv | (no lock file) | CI: `pip install -e ".[dev]"` | Standard Python tooling |
| CI | GitHub Actions | — | `.github/workflows/livespec-tests.yml` | Python 3.11, pip |
| Deploy | None — local CLI + pre-commit hook | — | No Dockerfile/vercel.json/fly.toml | Developer tool, no hosted service |

<!-- Dev Tooling -->

| Layer | Choice | Notes |
|---|---|---|
| Build System | setuptools ≥68.0 | `pyproject.toml [build-system]` |
| Package format | editable install (`pip install -e .`) | Development workflow |

## Design

| Layer | Choice | Notes |
|---|---|---|
| Design | Pencil (MCP enabled) | Anthropic-inspired design system (warm beige #FAFAF9, amber #D97706, charcoal #1A1A1A); PNG/PDF export; Lucide icons |

> Note: LiveSpec is a CLI tool with no UI screens. The design tool is configured at the global level for use when designing spec mockups for LiveSpec's own feature specs.

---

## pytest Markers

| Marker | Description | LLM Required |
|---|---|---|
| `level_3a` | Static invariants — no LLM, fixture-based | No |
| `level_3b` | SDK isolated commands — controlled inputs | Yes (claude-agent-sdk) |
| `level_3c` | Full pipeline end-to-end | Yes |
| `chaos` | Broken/malformed fixtures — validator must not crash | No |
| `slow` | Tests > 30s | Depends |

---

## LLM Provider

The LLM provider is NOT part of the stack — it is user-configured via `~/.config/livespec/provider.py`. This pluggable interface allows any LLM backend (Anthropic API, cc-hub, local model) to be used for Layer 4 features.

---

*Updated by `spec-init --from-code` on 2026-04-13. Bump `updated` date on every stack change via `/spec-stack`.*

## Rationale

- Keep the stack explicit so LiveSpec commands can derive conventions and validation behavior deterministically.
