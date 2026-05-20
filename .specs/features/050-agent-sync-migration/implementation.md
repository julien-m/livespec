---
title: "Agent Sync Migration Implementation"
feature: 050-agent-sync-migration
status: Implemented
updated: 2026-05-20
---

# Implementation - Agent Sync Migration

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `.agent-sync/skills/spec-*/SKILL.md` | N/A (portable command content) | Implemented | 2026-05-18 |
| FR-002 | `.agent-sync/skills/spec-*/expectations.md`, `validator/expectations.py` | N/A (expectation corpus) | Implemented | 2026-05-18 |
| FR-003 | `.agent-sync/agents/livespec-*/*` | N/A (portable agent source) | Implemented | 2026-05-18 |
| FR-004 | `.agent-sync/rules/livespec/*.md` | N/A (portable rule source) | Implemented | 2026-05-20 |
| FR-005 | `scripts/sync-agent-assets.sh`, `scripts/link-local.sh`, `scripts/install.sh`, `scripts/init.sh` | N/A (shell migration glue) | Implemented | 2026-05-20 |
| FR-006 | `migrations/16/migrate.md`, `scripts/migrate-agent-sync.sh`, `VERSION` | N/A (migration manifest) | Implemented | 2026-05-18 |
| FR-007 | `validator/command_registry.py`, `validator/command_audit.py`, `validator/integrations.py`, `validator/cli_commands/*.py` | N/A (validator source change) | Implemented | 2026-05-18 |
| FR-008 | `hooks/livespec-last-reviewed.py`, `scripts/audit-antidrift-coverage.sh` | N/A (hook source change) | Implemented | 2026-05-18 |
| FR-009 | `README.md`, `AGENTS.md`, `.specs/spec-system.md`, `system/*.md`, `.checks/livespec-routing-sync.md` | N/A (documentation source change) | Implemented | 2026-05-18 |
| FR-010 | deleted `commands/`, deleted `agents/` | N/A (source layout removal) | Implemented | 2026-05-18 |

## Acceptance Criteria

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_agent_sync_layout.py` | Passed |
| AC-002 | `tests/test_agent_sync_layout.py`, `tests/test_builtin_expectations_corpus.py` | Passed |
| AC-003 | `tests/test_agent_sync_layout.py` | Passed |
| AC-004 | `tests/test_agent_sync_scripts.py`, real cc-hub smoke test | Passed |
| AC-005 | `tests/test_command_aliases.py`, `tests/test_agent_sync_scripts.py` | Passed |
| AC-006 | `tests/test_command_aliases.py`, `tests/test_agent_sync_scripts.py` | Passed |
| AC-007 | `tests/integration/test_migration_v16_agent_sync.py` | Passed |
| AC-008 | `tests/test_command_registry.py`, `tests/test_command_audit_cli.py`, `tests/test_integrations.py` | Passed |
| AC-009 | `tests/test_agent_sync_scripts.py`, `.gitignore` | Passed |
| AC-010 | `bash scripts/check-coherence.sh`, source-path audit | Passed |
| AC-011 | `python3 -m validator.cli command-audit --repo . --naming-policy hyphenated --json` | Passed |
| AC-012 | `ruff check .`, `python3 -m pytest -q`, `bash scripts/check-coherence.sh`, feature validation | Passed |

## Files Created/Modified

- Created `.agent-sync/skills/spec-*` as the canonical command skill source, each with `SKILL.md` and `expectations.md`.
- Created `.agent-sync/agents/livespec-*` with portable `agent.yaml`, `prompt.md`, and provider build outputs.
- Created `.agent-sync/rules/livespec/` for shared LiveSpec routing and command rules.
- Added `scripts/sync-agent-assets.sh` and `scripts/migrate-agent-sync.sh`.
- Updated `scripts/init.sh`, `scripts/install.sh`, and `scripts/link-local.sh` to use cc-hub instead of manual provider symlinks.
- Updated rule sync to link individual project rule files before `cc-hub rule build`, matching provider output paths.
- Updated command registry, command audit, expectations, integration, hook, and CLI helpers to read `.agent-sync/skills`.
- Added migration 16 and bumped `VERSION` to `16`.
- Updated tests and docs to treat `.agent-sync` as the canonical source.
- Removed obsolete `commands/` and `agents/` source folders.
