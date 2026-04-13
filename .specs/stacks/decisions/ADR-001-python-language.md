# ADR-001: Python 3.11+ as Primary Language

- **Date:** 2026-04-13
- **Status:** Observed (from existing codebase)
- **Context:** LiveSpec validator needs to parse Markdown files, extract YAML frontmatter, validate schemas, run git operations, and optionally call LLMs. The language choice determines the ecosystem available for all of these tasks.
- **Decision:** Python 3.11+ with modern type hints, Pydantic v2, and Typer.
- **Evidence:** `pyproject.toml` requires-python ≥3.11; `.venv/` runs Python 3.14; all source files in `validator/` use `from __future__ import annotations` and modern typing.
- **Alternatives in ecosystem:**
  - **Go** — faster runtime, but weaker text processing/Markdown ecosystem; would require custom parsers for YAML frontmatter and Markdown
  - **TypeScript/Node.js** — user's general preference for web projects, but Python has stronger scientific/text processing libraries and is the dominant language for LLM tooling
  - **Rust** — maximum performance, but high development friction for text-manipulation and LLM integration tasks
- **Consequences:**
  - Requires virtualenv management per-project (`.venv/`)
  - No lock file currently (pip install -e .) — could add `uv` or `pip-tools` for reproducibility
  - CI uses pip directly; no lock file means dependency resolution on every CI run
- **Note:** This ADR documents an observed choice, not a deliberate decision made during `spec.init`. Rationale reconstructed from codebase signals.
