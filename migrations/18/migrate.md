---
version: 18
name: agent-sync-doctor-refresh
description: "Refresh LiveSpec agent-sync assets so older projects receive spec-doctor and journey-aware command updates"
date: 2026-06-03
kind: asset-sync
---
<!-- LiveSpec traceability anchors -->
<!-- @spec(FR-002) -->


# Migration v18: Agent Asset Refresh for Spec Doctor

Feature 055 added the `spec-doctor` skill after Migration 16 introduced
project-local agent-sync distribution. Projects already migrated to v17 need a
new migration version so `$spec-migrate` / `/spec-migrate` has a concrete step to re-run the
agent asset sync and install the new skill.

This migration is idempotent: `migrate-agent-sync.sh` removes only LiveSpec
managed provider symlinks, re-links `.agent-sync.local` sources, and lets
`cc-hub` rebuild provider-native Claude/Codex assets.

RUN migrate-agent-sync.sh
SET_VERSION 18
