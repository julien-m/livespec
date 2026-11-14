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

## 2026-11-14 automatic delegation follow-up

| Requirement / convention | Decision and owner | Verification |
|---|---|---|
| FR-001 / FR-003; scoped concurrency and ownership | Read [the shared policy](../../../system/review-led-delivery.md): dispatch all useful ready tasks, autonomous worker briefs, coordinated shared writes, one final review, preserved authority/read-only scope | Inspect actual compact entry-point links and the complete policy; parent owns independent correction review |
| AC-007; dependency and integration risks | Read [parallel delivery](../../../system/parallel-delivery.md): distinguish hard prerequisites, stable shared interfaces and later extensions; reserve shared writers/migration IDs, integrate small slices against current base, reconcile already-applied work, preserve partial results and cumulative profile compatibility | Independent review of the documented acceptance cases; check the mandatory policy-to-protocol link, no scheduler/schema/runtime edit |
| Accurate user guidance and source reuse | Read [the README](../../../README.md#multi-agent-mode-default): replace obsolete Superpowers/per-step review requirements with native delegation, independent feature/worktree scheduling and shared-canvas ownership | Resolve added links, inspect diff and run relevant existing diagnostic/hook/runtime documentation regressions |
| No new runtime/data behavior | No Python, dependency, schema, generated skill or historical diagnostic edit | Check changed-file scope and preserve existing consumer runtime lineage during the parent's explicit port |

This extends feature122's existing delivery contract without allocating another feature identifier. Parent publication/adoption and review remain separate from this source correction; no live consumer is silently repinned here.
