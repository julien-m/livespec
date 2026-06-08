---
version: 20
name: user-journeys-native-runner-refresh
description: "Refresh User Journeys v2 assets and force regeneration of old compiled journey manifests"
date: 2026-06-08
kind: asset-sync
---

# Migration v20: User Journeys Native Runner Refresh

Feature 057 originally installed User Journeys v2, but older compiled manifests
used compiler `journeys-v2-1`, which only proved freshness and did not guarantee
native runner execution.

This migration refreshes LiveSpec agent-sync assets and bumps project
`livespec-version` so older projects receive the corrected guidance:

- `livespec journey run` executes native compiled artifacts without recompiling.
- XCUITest compilation runs `xcodegen generate` when `project.yml` or
  `project.yaml` is present.
- Old compiled manifests are rejected as `journey_compiled_stale` until the
  operator re-runs `livespec journey compile` or
  `livespec journey compile --journey <id>`.

RUN migrate-agent-sync.sh
SET_VERSION 20
