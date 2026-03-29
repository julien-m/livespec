# Before Plan — Ensure Fresh Conventions

Before `/spec.plan` starts, verify that `.conventions/conventions.md` is up to date with the current stack and ai-ressources knowledge base.

## Instructions

### Freshness check

Read three dates:
1. `generated` from `.conventions/conventions.md` YAML frontmatter
2. `updated` from `.specs/stacks/_default.md` YAML frontmatter
3. Content of `~/projects/ai-ressources/.last-updated`

### Decision

- If `.conventions/conventions.md` does **not** exist AND `.specs/stacks/_default.md` exists:
  → Run `/conventions.init`. Report: `Conventions initialized before planning.`

- If `.conventions/conventions.md` exists AND `generated` < `updated` (stack changed since last conventions generation):
  → Run `/conventions.refresh --full`. Report: `Conventions refreshed (stack changed since last generation).`

- If `.conventions/conventions.md` exists AND `generated` < `ai-ressources/.last-updated` (rules changed):
  → Run `/conventions.refresh`. Report: `Conventions refreshed (ai-ressources updated).`

- If `.conventions/conventions.md` exists AND `generated` >= both dates:
  → Skip silently. Do not report anything.

- If `.specs/stacks/_default.md` does **not** exist:
  → Skip silently. This project does not use LiveSpec stack management.

### Notes

- If `updated` is missing from `_default.md` frontmatter, treat it as "always stale" (triggers refresh). The refresh will not add the field — that is `/spec.stack`'s responsibility.
- If `~/projects/ai-ressources/.last-updated` does not exist, skip that comparison.
