---
version: 10
description: "Enrich preflight.md with driver/runner entries from features 016-033 (Feature 034)"
date: 2026-05-07
---

# Migration v10: Preflight Auto-Install Enrichment

Feature 034 (Preflight Auto-Install & Init) introduces a `--fix` flag
to `/spec.preflight` that auto-installs missing tools and initialises
simulators/AVDs. To benefit from it, downstream projects need their
`.specs/preflight.md` to declare entries for the drivers and UI
runners shipped in features 016-033 (test drivers, UI runners,
visual testing, Tauri/iOS/Android scaffolding…).

This migration scans the project filesystem (`.specs/drivers/*.yaml`,
`.specs/runners/*.yaml`, plus heuristic stack detection from
`pyproject.toml`, `Cargo.toml`, `package.json`, etc.) and appends
matching preflight entries between LiveSpec section markers
(`<!-- preflight:livespec:start -->` … `<!-- preflight:livespec:end -->`).

User-authored content (anywhere outside the LiveSpec markers, including
the existing `<!-- preflight:custom:start -->` / `…:end -->` block) is
preserved verbatim. Re-running the migration is a no-op once the markers
contain the expected block.

## Actions

RUN preflight-enrich.py
SET_VERSION 10
