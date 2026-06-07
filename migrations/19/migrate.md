---
version: 19
name: user-journeys-v2-agent-refresh
description: "Refresh LiveSpec agent-sync assets so older projects receive spec-journey and User Journeys v2 guidance"
date: 2026-06-07
kind: asset-sync
---

# Migration v19: Agent Asset Refresh for User Journeys v2

Feature 057 adds the `spec-journey` skill and updates command guidance so
existing LiveSpec projects can create, bootstrap, impact-check, compile, and run
global User Journeys v2.

Projects already at v18 need a concrete migration point so `$spec-migrate` /
`/spec-migrate` re-runs agent asset sync and installs the new skill, routing
rule, and journey-aware command documentation.

This migration is idempotent: `migrate-agent-sync.sh` removes only LiveSpec
managed provider symlinks, re-links `.agent-sync.local` sources, and lets
`cc-hub` rebuild provider-native Claude/Codex assets.

RUN migrate-agent-sync.sh
SET_VERSION 19
