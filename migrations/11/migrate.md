---
version: 11
description: "Append missing visual surfaces to surfaces.yaml for legacy split layouts (Feature 036)"
date: 2026-05-07
---

# Migration v11: Multi-Surface Detection (e2e + visual)

Feature 036 (Multi-Surface Detection & Migration) updated
`scripts/generate-surfaces.js` so that projects with split Playwright
layouts (`tests/e2e/` + `tests/visual/`, each with their own
`playwright.config.ts` / `playwright.visual.config.ts`) get one
`surfaces.yaml` entry per layout — instead of silently dropping the
visual surface.

Existing projects already on v10 have a single-surface `surfaces.yaml`
that omits the visual entries. This migration detects that legacy state
and appends the missing visual surface(s) using a **text-level append**
strategy: existing entries (and any user-authored comments) are
preserved byte-for-byte. The migration is **idempotent** — re-running
on a manifest that already declares both surfaces is a no-op.

Projects on the canonical post-`migrate-visual-tests.js` layout (single
unified surface, no `tests/visual/` directory) are unaffected: the
detection finds no visual surface to append and the manifest stays
identical.

If `.specs/surfaces.yaml` does not exist yet, the wrapper bootstraps a
fresh manifest via the standard `generate-surfaces.js` path (which is
now multi-surface aware).

## Actions

RUN migrate-surfaces.sh
SET_VERSION 11
