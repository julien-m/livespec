---
created_at: '2026-05-07'
current_state: Done
feature_slug: 036-multi-surface-detection-and-migration
owner_command: spec-feature
schema_version: 1
updated_at: '2026-05-07'
---

# Pipeline — 036-multi-surface-detection-and-migration

**Started:** 2026-05-07 15:18
**Flags:** `--auto`
**Feature Description:** Support detection of multiple Playwright surfaces (e2e + visual) in `.specs/surfaces.yaml`. For new projects, the surface generator must auto-detect when both `tests/e2e/` and `tests/visual/` coexist (with their respective `playwright.config.ts` and `playwright.visual.config.ts`) and emit one entry per surface. For legacy projects already initialized with a single-surface manifest, provide a migration path to add and manage the missing visual surface(s) — there may be more than one visual surface per project (e.g., monorepos with multiple web apps each having their own visual suite). Without breaking projects already on the canonical post-`migrate-visual-tests.js` layout (single unified surface).

| Phase | Status | Completed At |
|-------|--------|--------------|
| Specify | Done | 2026-05-07 |
| Spec Review | Done | 2026-05-07 15:24 |
| Plan | Done | 2026-05-07 15:29 |
| Plan Review | Done | 2026-05-07 15:29 |
| Preflight | Done | 2026-05-07 15:29 |
| Implement | Done | 2026-05-07 15:35 |
| Test | Done | 2026-05-07 15:37 |
