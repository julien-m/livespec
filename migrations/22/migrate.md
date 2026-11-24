---
version: 22
name: conventions-migration-docs
description: "Bootstrap conventions gates, rulebook, scaffold, first debt report, and docs for conventions enforcement"
date: 2026-06-13
kind: asset-sync
---

<!-- @spec(FR-001) -->

<!-- @spec FR-001: Migration v22 conventions bootstrap
     — ../../.specs/features/065-conventions-migration-docs/spec.md#fr-001 -->
<!-- @spec FR-004: Preserve migration pre-images and keep checks advisory
     — ../../.specs/features/122-review-led-delivery/spec.md#fr-004 -->

# Migration v22: Conventions Migration Docs

Feature 065 makes conventions checks available for existing projects. The
migration refreshes portable agent assets, initializes conventions gates where
possible, compiles the conventions rulebook when a `.conventions/manifest.yaml`
exists, scaffolds linter config from gates, and records an initial conventions
verification report without blocking the migration.

The first verify step is advisory. Subsequent delivery uses the shared final
review. Conventions results inform that review when relevant.

Before running the generators, this migration records the files and directories
they can change. Apply the inverse in [inverse.md](inverse.md) to restore this
scope. The restore point and debt reports stay local to the checkout.

RUN migrate-restore-point.py record 22 .agent-sync .agent-sync.local .agents .claude .codex .gitignore .ruff_cache .specs/conventions .specs/conventions-gates.yaml .specs/conventions-rulebook.yaml .specs/livespec-version AGENTS.md CLAUDE.md pyproject.toml .eslintrc.json .swiftlint.yml
GITIGNORE /.specs/.migration-restore/
GITIGNORE /.specs/conventions/debt.json
GITIGNORE /.specs/conventions/debt-report.md
RUN migrate-agent-sync.sh
RUN migrate-conventions-gates-init.sh
RUN migrate-conventions-compile.sh
RUN migrate-conventions-scaffold.sh
RUN migrate-conventions-first-verify.sh
SET_VERSION 22
