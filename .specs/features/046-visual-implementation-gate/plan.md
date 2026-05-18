# Plan - Feature 046 - Visual Implementation Gate

## Summary

Tighten the command-layer contract so `/spec.implement` delegates visual certification to `/spec.test --auto --visual` before finalizing UI features, and lock that behavior with regression tests.

## Technical Context

- **Language:** Markdown command contracts plus Python pytest regression tests.
- **Testing framework:** pytest.
- **Storage:** `.specs/features/046-visual-implementation-gate/` for spec artifacts.
- **Project type:** LiveSpec command framework.

## Constitution Check

| Principle | Compliance |
|---|---|
| Spec as source of truth | Feature 046 spec defines the new behavior before command edits. |
| Living specs | `implementation.md` and changelogs will be updated after edits. |
| Visual and testable specs | Gherkin and Mermaid flows are included for all user stories. |
| Traceability | Tests and command edits will include `@spec` anchors where applicable. |

## Implementation Plan

1. Add regression tests in `tests/test_visual_implementation_gate.py`.
2. Run the focused test and confirm RED.
3. Update `commands/spec-implement.md`:
   - Insert Phase 6.5 visual gate.
   - Make visual tooling unavailable blocking for UI features.
   - Cap `--no-visual` UI features at `In Progress`.
   - Add command-level DoD items.
4. Update `commands/spec-test.md`:
   - Add structured `Visual Gate Verdict`.
   - Define `PASS`, `FAIL`, `BLOCKED` and exit-code behavior for visual gate use.
5. Update `commands/spec-implement.expectations.md` and `commands/spec-test.expectations.md`.
6. Add `implementation.md`, `changelog.md`, and global changelog/README entries.
7. Run focused tests.

## Testing Strategy

- `pytest tests/test_visual_implementation_gate.py -q`
- If time permits, run the expectations corpus parse test because expectations files are touched:
  `pytest tests/test_builtin_expectations_corpus.py -q`

## Risks & Considerations

- This feature changes command contracts, not executable command Python. The regression tests therefore assert the required command text and expectation-contract invariants directly.
- The existing `/spec.test` visual runner details remain the source of execution behavior; `/spec.implement` should call into that path rather than duplicate implementation details.
