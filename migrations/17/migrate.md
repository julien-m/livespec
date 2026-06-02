---
version: 17
name: penflow-backfill-and-migration-planner
description: "Backfill Penflow from current UI and legacy mockups; supersede unsafe legacy restore state"
date: 2026-06-01
kind: backfill
supersedes: [3]
invalidates_restore_points: [3]
replaces_when_unapplied: [3]
---

# Migration v17: Penflow Backfill + Migration Planner Metadata

Feature 054 adds a planner for `/spec-migrate` and backfills root `penflow/`
artifacts for older projects only when this can be done without inventing UI
truth from legacy screenshots.

RUN migrate-penflow-backfill.py
SET_VERSION 17
