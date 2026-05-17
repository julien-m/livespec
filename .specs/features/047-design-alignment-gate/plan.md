# Plan - Feature 047 - Design Alignment Gate

## Summary

Promote the CloudSkill mockup-code alignment workflow into LiveSpec as a reusable Design Alignment Gate, with docs, schema, Python comparator, CLI, `/spec.test --visual` integration, and regression tests.

## Technical Context

- **Language:** Python 3.11+ and Markdown command contracts.
- **CLI framework:** Typer.
- **Input format:** JSON-compatible `.pen` contract subset and runtime JSON contract. The parser is intentionally permissive so it can consume exported Pencil trees or normalized files produced by future adapters.
- **Output:** Markdown report, JSON diff, YAML-like manifest written as JSON-compatible text.
- **Testing:** pytest + Typer CliRunner.
- **Project type:** LiveSpec CLI/framework.

## Constitution Check

| Principle | Compliance |
|---|---|
| Spec source of truth | Feature 047 defines behavior before code. |
| Visual/testable specs | Every story has Gherkin and Mermaid. |
| Traceability | New modules include `@spec` anchors. |
| Fail clearly | PASS/FAIL/BLOCKED map to exit 0/1/2. |
| Reusable workflows | Procedure lives under `system/testing/`, not embedded in a command blob. |

## Implementation Plan

1. Add failing tests in `tests/test_design_alignment.py`.
2. Add failing command-contract test in `tests/test_design_alignment_command_contract.py`.
3. Implement `validator/design_alignment/`:
   - models/verdicts
   - permissive contract loading from JSON `.pen` / runtime JSON
   - support parity checker
   - node/property comparator
   - report/manifest writer
4. Add CLI module `validator/cli_commands/design_alignment_cmd.py` and register it.
5. Add workflow docs:
   - `system/testing/design-alignment.md`
   - `system/testing/design-alignment-quality.md`
   - `system/schemas/design-alignment-manifest.md`
6. Update `commands/test.md` with Phase 4.5.0.
7. Update `commands/test.expectations.md`.
8. Add feature implementation/progress/changelog and update global indexes.
9. Run focused and supporting tests.

## Testing Strategy

- `pytest tests/test_design_alignment.py -q`
- `pytest tests/test_design_alignment_command_contract.py -q`
- `pytest tests/test_builtin_expectations_corpus.py -q`
- `pytest tests/test_schemas.py -q`

## Risks & Considerations

- The first version compares normalized contracts, not raw binary Pencil internals. This is deliberate: it gives LiveSpec a stable contract and lets future Pencil adapters evolve without changing verdict semantics.
- Runtime extraction differs by platform; this feature defines the common comparator and CLI. UI runners can produce the runtime contract in follow-up work while already consuming the same verdict model.
