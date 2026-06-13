---
version: 22
name: conventions-migration-docs
description: "Bootstrap conventions gates, rulebook, scaffold, first debt report, and docs for conventions enforcement"
date: 2026-06-13
kind: asset-sync
---

<!-- @spec FR-001: Migration v22 conventions bootstrap
     — ../../.specs/features/065-conventions-migration-docs/spec.md#fr-001 -->

# Migration v22: Conventions Migration Docs

Feature 065 makes conventions enforcement explicit for existing projects. The
migration refreshes portable agent assets, initializes conventions gates where
possible, compiles the conventions rulebook when a `.conventions/manifest.yaml`
exists, scaffolds linter config from gates, and records an initial conventions
verification report without blocking the migration.

The first verify step is advisory and always exits 0. Blocking starts on the
next implement/test/fix pipeline run, where conventions receipts are mandatory.

SET_VERSION 22
RUN migrate-agent-sync.sh
RUN migrate-conventions-gates-init.sh
RUN migrate-conventions-compile.sh
RUN migrate-conventions-scaffold.sh
RUN migrate-conventions-first-verify.sh
