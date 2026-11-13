# Plan: Review Led Delivery

## Summary

Replace default skill ceremony with useful checks and independent final review while retaining historical diagnostic semantics.

## Technical Context

Python validator and Markdown skills/role prompts, filesystem state, Claude/Codex projections. No dependency, database or UI changes.

## Constitution Check

Diagnostics keep explicit errors and original verdicts. Source/file boundaries and user decisions remain enforced. The user explicitly replaces former delivery certification prerequisites; this change is implemented manually outside spec commands.

## Implementation Plan

1. Replace ten skill bodies and four role prompts; retain their original public versions beside them.
2. Select certification.md in goal compilation with fallback to SKILL.md.
3. Update shared policy, routing and five system introductions; document project-copy resolution.
4. Document consumer migration, checkpoint, rollback and preservation of newer runtime fixes.
5. Verify compatibility, inspect official projection, review the public diff, publish to main and test the installed result.
6. Reload Atlas only after that validation and observe its real continuation.

## Testing Strategy

Use existing pytest commands, the new archived-inventory regression, Ruff/typing, projection inspection and a real consumer continuation. Report actual failures and time limits; do not invent machine certification.

## Risks & Considerations

Private/public histories differ. Publish only this feature and original public archives. Atlas is ahead of public main: port the policy onto its runtime rather than downgrade it. Preserve customized mutable roles and use a generic native reviewer when necessary.
