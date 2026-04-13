# Constitution — LiveSpec

> This constitution defines the architectural principles and conventions for this project.
> All implementation decisions are validated against these principles.
> AI tools must check this file before making architectural choices.

---

## Project Identity

- **Name:** LiveSpec
- **Description:** A universal, tool-agnostic specification framework for AI-driven development. LiveSpec combines a Markdown-based command system (Claude Code slash commands + agents) with a Python CLI validator (`livespec-validator`) that enforces structural integrity on `.specs/` directories through 4 validation layers.
- **Vision:** LiveSpec becomes the default spec framework for Claude Code projects. The Python validator runs in CI on thousands of projects. A single `/spec.feature` invocation ships a fully-specified, tested, and traced feature end-to-end.
- **Repository:** https://github.com/julien-m/livespec
- **Stack Reference:** See `.specs/stacks/_default.md`

---

## Architecture Principles

### 1. Layered Validation
- Validation is organized in explicit layers: structural (Layer 1) → coherence (Layer 2) → SDK-isolated (Layer 3) → semantic/LLM (Layer 4)
- Each layer builds on the previous; a file that fails Layer 1 is not passed to Layer 2
- Layers are independently invocable via CLI flags (`--coherence`, `--semantic`, `--plan-review`)
- No layer is skipped silently — failures are surfaced with file, line, and rule references

### 2. Provider-Agnostic LLM Integration
- LLM calls are never hardcoded to a specific provider or model
- The pluggable `call_llm()` interface (`~/.config/livespec/provider.py`) is the only LLM entry point
- LLM-dependent features (Layer 4) degrade gracefully when no provider is configured — they fail fast with a clear error, never silently
- Provider setup details live in `.specs/stacks/_default.md` and `validator/llm_provider.py`

### 3. File-System as Source of Truth
- The `.specs/` directory is the sole source of truth for project state — no database, no remote service
- All validator reads are from the file system; all writes are scoped to `.specs/` or the target project
- Git is used for versioning and staged-file detection, never for state storage

### 4. Fail Fast, Exit Clearly
- Validate inputs at the earliest possible point (CLI argument parsing → file existence → YAML parsing → schema validation)
- Return specific exit codes: 0 (success), 1 (general error), 2 (invalid args), 3 (config error), 130 (Ctrl+C)
- Error messages always identify: file path, rule ID, and actionable fix
- No silent swallowing of exceptions; all errors are surfaced to the user

### 5. Minimal Surface, Maximum Composability
- The CLI exposes a small number of well-defined subcommands: `validate`, `install-hook`, `pipeline`, `git`, `commit-context`
- Features are composed via flags, not separate commands (e.g., `--coherence`, `--fix`, `--staged`)
- No global state between invocations — the CLI is stateless except for what it reads from the file system
- Every subcommand can be used independently or chained in CI pipelines

### 6. No Hosted Infrastructure
- LiveSpec is a local developer tool and open-source library — no server, no SaaS, no telemetry
- All LLM token costs are borne by the developer's own API key
- Installation is via `pip install -e .` or globally via the bootstrap script

---

## Testing Standards

### What to Test
- **Unit tests:** All pure functions in `validator/` modules (parsing, schema validation, coherence rules, scoring)
- **Integration tests:** Full CLI invocations with real fixture `.specs/` directories
- **SDK-isolated tests (Level 3b):** Commands executed via `claude-agent-sdk` with controlled inputs
- **End-to-end tests (Level 3c):** Full pipeline: `spec.specify` → `spec.plan` → `spec.implement`
- **Chaos tests:** Broken/malformed `.specs/` fixtures — validator must not crash, must report clearly

### How to Test
- Test files live in `tests/` — unit tests at `tests/test_*.py`, integration at `tests/integration/`
- Fixtures are in `tests/fixtures/` (real `.specs/` directory snapshots)
- Every test description references the rule or behavior it validates
- pytest markers: `level_3a` (no LLM), `level_3b` (SDK isolated), `level_3c` (full pipeline), `chaos`, `slow`

### No Visual Testing
- This project has no UI — visual testing is not applicable
- The `playground/` HTML files are dev tools, not tested components

### Testing Reference
- See `.specs/testing/strategy.md` for the full project testing strategy
- Concrete test commands are in the Resolved Test Commands table

---

## Code Conventions

### Naming (Python)
- **Files/modules:** `snake_case` (`graph_builder.py`, `rule_engine.py`)
- **Classes:** `PascalCase` (`RuleEngine`, `ValidationResult`)
- **Functions/methods:** `snake_case` (`run_coherence()`, `validate_all()`)
- **Constants:** `SCREAMING_SNAKE_CASE` (`MAX_VIOLATION_COUNT`)
- **Type aliases:** `PascalCase` (`SpecPath = Path`)

### Structure
- Max file length: 300 lines (split beyond that)
- Max function length: 50 lines (extract helpers beyond that)
- One public function or class per module where possible
- No God objects — single responsibility per class

### Formatting and Quality
- **Ruff** for linting (rules: E, F, I, UP, RUF, B, SIM) and formatting (replaces black/isort)
- **Pyright** in strict mode for type checking — all types must be explicit
- No unused imports, no commented-out code committed
- All function signatures include type annotations and docstrings

### Error Handling
- Domain-specific exceptions in `validator/exceptions.py`
- CLI boundary converts domain exceptions to `typer.Exit` with meaningful messages
- Never swallow `Exception` — always re-raise or log explicitly

---

## Spec Conventions

### Gherkin + Mermaid Required
- Every user story in a spec.md MUST have Gherkin scenarios (```gherkin blocks) — source of truth for AI and test scaffolding
- Every user story MUST have a matching Mermaid flowchart — visual representation of the same flow
- Every plan.md with API calls MUST have Gherkin interaction scenarios + sequence diagrams
- Every plan.md with stateful entities MUST have Gherkin transition scenarios + state diagrams
- ER diagrams use Mermaid only (no behavioral flow)

### Living Documentation
- Specs are updated when behavior changes — never let them become stale
- `implementation.md` is updated after every code change, with `@spec ID: description` anchor comments in source files
- `changelog.md` gets an entry for every feature/bugfix/refactor

### Update Rules
- **Behavior change:** Update spec.md + implementation.md + changelog.md
- **Code refactor (no behavior change):** Update implementation.md + changelog.md only
- **Bug fix:** Update implementation.md + changelog.md with Bugfix type entry
- **Spec update only:** Update spec.md + changelog.md with Spec Update type entry

---

## Decision Rules

When uncertain about an architectural choice, apply these rules in order:

1. **Does the constitution say anything about it?** → Follow it
2. **Does an existing pattern in the codebase solve it?** → Follow the pattern
3. **Is there a relevant ADR in `.specs/stacks/decisions/`?** → Follow the decision
4. **Still unclear?** → Add a `[DECISION NEEDED]` marker and ask the human

Do NOT make silent architectural decisions. Document them.

---

*Generated by `spec.init --from-code` on 2026-04-13 — LiveSpec v3*
*Update this file as the project architecture evolves.*
