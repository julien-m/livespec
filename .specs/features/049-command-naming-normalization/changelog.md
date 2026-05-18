# Changelog - Command Naming Normalization

## 2026-05-18 — [Spec Update]: Created

- **Type:** Spec Update
- **Spec modified:** Yes (initial feature spec and plan)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-010
- **Author:** tool-name

## 2026-05-18 — [Feature]: Implemented

- **Type:** Feature
- **Spec modified:** Yes (status Draft → Implemented; AC-009 clarified to basename-normalized artifacts)
- **Code modified:** `validator/command_registry.py`, `validator/cli_commands/verify_output_cmd.py`, `validator/cli_commands/run_cmd.py`, `validator/hooks_cli.py`, `validator/hook_resolver.py`, `validator/integrations.py`, `scripts/link-local.sh`, `scripts/install.sh`, `migrations/15/migrate.md`, command docs
- **AC impacted:** AC-001 through AC-010
- **Author:** codex

## 2026-05-18 — [Feature]: Canonical source filenames

- **Type:** Feature
- **Spec modified:** Yes (added AC-011 and FR-011 for `commands/spec-*` source files)
- **Code modified:** `commands/spec-*.md`, `commands/spec-*.expectations.md`, `validator/command_registry.py`, `validator/command_audit.py`, `validator/run_artifact.py`, `scripts/link-local.sh`, `scripts/install.sh`, tests
- **AC impacted:** AC-001 through AC-011
- **Author:** codex
