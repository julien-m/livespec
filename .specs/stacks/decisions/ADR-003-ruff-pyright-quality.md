# ADR-003: Ruff + Pyright for Code Quality

- **Date:** 2026-04-13
- **Status:** Observed (from existing codebase)
- **Context:** Python projects need linting, formatting, and type checking. The choice of tools affects developer experience, CI speed, and the quality of the type guarantees.
- **Decision:** Ruff for linting and formatting; Pyright in strict mode for type checking.
- **Evidence:** `pyproject.toml [tool.ruff]` with rules E, F, I, UP, RUF, B, SIM; `pyproject.toml [tool.pyright]` with `typeCheckingMode = "strict"`; `.ruff_cache/` in project root.
- **Alternatives in ecosystem:**
  - **Black + isort + flake8** — the classic Python trio; Ruff replaces all three with a single Rust-based tool that is 10-100x faster
  - **mypy** — the dominant Python type checker; Pyright is faster, has better IDE integration (VS Code Pylance), and stricter inference
  - **pylint** — broad linter but slow; Ruff covers the most important rules much faster
- **Consequences:**
  - Ruff is configured with a strict rule set (B = bugbear, SIM = simplify, RUF = ruff-specific) — some rules require explicit ignores for intentional patterns (e.g., `noqa: B904` for intentional `raise typer.Exit` without `from`)
  - Pyright strict mode requires all function signatures to be typed — no `Any` escape hatches
  - CI runs ruff + pyright on every push; failures block merge
- **Note:** This ADR documents an observed choice, not a deliberate decision made during `spec.init`. Rationale reconstructed from codebase signals.
