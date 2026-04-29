---
version: 9
description: "Brainstorm ingestion — auto-import project-brainstorm artifacts into existing .specs/"
date: 2026-04-29
---

# Migration v9: Brainstorm Ingestion

For projects already initialized with LiveSpec that also contain
project-brainstorm artifacts (`specs/flows/*.md`, `mockups/*.png`,
`mockups/manifest.json`, `project-profile.md`) at the project root,
this migration auto-imports those artifacts into the existing
`.specs/` tree using `livespec brainstorm` in refine mode.

Behavior:
- No brainstorm artifacts detected → silent no-op.
- Detected → validates grammar, builds a refine-mode plan, and
  applies it without confirmation prompt. Existing `.specs/features/*`,
  `.specs/roadmap.md`, and `.specs/design/screens/` are merged
  per-file (best-effort); collisions on feature numbering shift to
  the next free NNN.
- Validation failure (grammar / missing mockup) → migration aborts
  with explicit violations; no `.specs/` mutation.

## Actions

SET_VERSION 9
RUN import-brainstorm.sh
