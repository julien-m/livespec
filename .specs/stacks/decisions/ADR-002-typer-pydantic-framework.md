# ADR-002: Typer + Pydantic as CLI and Validation Frameworks

- **Date:** 2026-04-13
- **Status:** Observed (from existing codebase)
- **Context:** The validator needs (1) a CLI framework to expose subcommands with typed arguments, auto-generated help, and clean exit codes, and (2) a schema validation library to enforce structure on parsed spec files.
- **Decision:** Typer ≥0.12 for CLI, Pydantic ≥2.7 for schema validation.
- **Evidence:** `pyproject.toml` dependencies; `validator/cli.py` uses `typer.Typer()`, `typer.Argument()`, `typer.Option()`; `validator/schemas/` contains Pydantic BaseModel subclasses for all spec file types.
- **Alternatives in ecosystem:**
  - **Click** (CLI) — lower-level predecessor to Typer; Typer wraps Click with type annotations, reducing boilerplate. No reason to drop to Click.
  - **argparse** (CLI) — stdlib, no dependencies, but verbose; Typer is strictly better for this use case.
  - **Marshmallow** (validation) — older Python validation library; Pydantic v2 is faster, has better typing support, and is now standard for Python APIs.
  - **attrs + cattrs** (validation) — lighter alternative; Pydantic v2 has better ecosystem integration and JSON schema generation.
- **Consequences:**
  - Typer auto-generates `--help` docs from type annotations and docstrings — documentation is always up-to-date
  - Pydantic v2 enforces strict types at runtime, catching malformed spec files early
  - Both libraries add to the dependency footprint (pip install size), but this is acceptable for a developer tool
- **Note:** This ADR documents an observed choice, not a deliberate decision made during `spec-init`. Rationale reconstructed from codebase signals.
