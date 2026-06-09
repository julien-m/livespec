---
title: "Implementation - Cross-Feature User Journeys v2"
feature: 057-cross-feature-user-journeys-v2
status: Implemented
implemented: 2026-06-04
last_verified: 2026-06-09
---

# Implementation - Cross-Feature User Journeys v2

## Summary

Implemented global User Journeys v2 across schema, validation, indexing, history governance, assignment/bootstrap, impact analysis, compile/run lifecycle, CLI, visual checks, migration, doctor findings, and skill/docs integration.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `validator/journeys/schema.py` | `@spec FR-001` | ✅ Implemented | 2026-06-05 |
| FR-002 | `validator/journeys/paths.py` | `@spec FR-002` | ✅ Implemented | 2026-06-05 |
| FR-003 | `validator/journeys/paths.py`, `validator/journeys/manifest.py` | `@spec FR-003` | ✅ Implemented | 2026-06-05 |
| FR-004 | `validator/journeys/paths.py`, `validator/journeys/validator.py` | `@spec FR-004` | ✅ Implemented | 2026-06-05 |
| FR-005 | `validator/journeys/schema.py` | `@spec FR-005` | ✅ Implemented | 2026-06-05 |
| FR-006 | `validator/journeys/schema.py`, `validator/journeys/validator.py` | `@spec FR-006` | ✅ Implemented | 2026-06-05 |
| FR-007 | `validator/journeys/backlinks.py`, `validator/journeys/paths.py` | `@spec FR-007` | ✅ Implemented | 2026-06-05 |
| FR-008 | `validator/journeys/impact.py`, `.agent-sync/skills/spec-feature/SKILL.md` | `@spec FR-008` | ✅ Implemented | 2026-06-05 |
| FR-009 | `validator/journeys/history.py` | `@spec FR-009` | ✅ Implemented | 2026-06-05 |
| FR-010 | `validator/journeys/history.py` | `@spec FR-010` | ✅ Implemented | 2026-06-05 |
| FR-011 | `validator/journeys/history.py` | `@spec FR-011` | ✅ Implemented | 2026-06-05 |
| FR-012 | `validator/journeys/history.py` | `@spec FR-012` | ✅ Implemented | 2026-06-05 |
| FR-013 | `validator/journeys/assignment.py`, `.agent-sync/skills/spec-journey/SKILL.md` | `@spec FR-013` | ✅ Implemented | 2026-06-05 |
| FR-014 | `validator/journeys/assignment.py`, `.agent-sync/skills/spec-journey/SKILL.md` | `@spec FR-014` | ✅ Implemented | 2026-06-05 |
| FR-015 | `validator/journeys/bootstrap.py`, `.agent-sync/skills/spec-journey/SKILL.md` | `@spec FR-015` | ✅ Implemented | 2026-06-05 |
| FR-016 | `validator/journeys/assignment.py`, `.agent-sync/skills/spec-journey/SKILL.md` | `@spec FR-016` | ✅ Implemented | 2026-06-05 |
| FR-017 | `validator/journeys/schema.py`, `validator/journeys/validator.py` | `@spec FR-017` | ✅ Implemented | 2026-06-05 |
| FR-018 | `validator/journeys/validator.py`, `validator/journeys/scanner.py` | `@spec FR-018` | ✅ Implemented | 2026-06-05 |
| FR-019 | `validator/journeys/impact.py` | `@spec FR-019` | ✅ Implemented | 2026-06-05 |
| FR-020 | `validator/journeys/impact.py` | `@spec FR-020` | ✅ Implemented | 2026-06-05 |
| FR-021 | `validator/journeys/impact.py` | `@spec FR-021` | ✅ Implemented | 2026-06-05 |
| FR-022 | `validator/cli_commands/journey_cmd.py` | `@spec FR-022` | ✅ Implemented | 2026-06-05 |
| FR-023 | `validator/journeys/compiler.py`, `validator/cli_commands/journey_cmd.py` | `@spec FR-023` | ✅ Implemented | 2026-06-08 |
| FR-024 | `validator/journeys/runner.py`, `validator/cli_commands/test_cmd.py`, `validator/cli_commands/journey_cmd.py` | `@spec FR-024` | ✅ Implemented | 2026-06-08 |
| FR-025 | `.agent-sync/skills/spec-feature/SKILL.md`, `.agent-sync/skills/spec-implement/SKILL.md` | `@spec FR-025` | ✅ Implemented | 2026-06-05 |
| FR-026 | `.agent-sync/skills/spec-test/SKILL.md`, `validator/cli_commands/test_cmd.py` | `@spec FR-026` | ✅ Implemented | 2026-06-08 |
| FR-027 | `validator/journeys/runner.py`, `validator/cli_commands/journey_cmd.py` | `@spec FR-027` | ✅ Implemented | 2026-06-08 |
| FR-028 | `validator/journeys/compiler_registry.py`, `validator/journeys/capabilities.py`, `validator/journeys/compiler.py` | `@spec FR-028` | ✅ Implemented | 2026-06-05 |
| FR-029 | `validator/journeys/manifest.py`, `validator/journeys/compiler.py`, `validator/journeys/runner.py`, `validator/journeys/scanner.py` | `@spec FR-029` | ✅ Implemented | 2026-06-08 |
| FR-030 | `validator/journeys/manifest.py`, `validator/journeys/compiler.py` | `@spec FR-030` | ✅ Implemented | 2026-06-05 |
| FR-031 | `validator/journeys/schema.py` | `@spec FR-031` | ✅ Implemented | 2026-06-05 |
| FR-032 | `validator/journeys/schema.py`, `validator/journeys/impact.py` | `@spec FR-032` | ✅ Implemented | 2026-06-05 |
| FR-033 | `validator/journeys/schema.py`, `validator/journeys/visual_contracts.py` | `@spec FR-033` | ✅ Implemented | 2026-06-05 |
| FR-034 | `validator/journeys/visual_contracts.py`, `validator/journeys/compiler.py` | `@spec FR-034` | ✅ Implemented | 2026-06-05 |
| FR-035 | `validator/journeys/schema.py`, `validator/journeys/visual_contracts.py`, `validator/journeys/llm_visual.py` | `@spec FR-035` | ✅ Implemented | 2026-06-05 |
| FR-036 | `validator/journeys/compiler.py`, `validator/journeys/llm_visual.py` | `@spec FR-036` | ✅ Implemented | 2026-06-05 |
| FR-037 | `validator/journeys/schema.py`, `validator/journeys/llm_visual.py` | `@spec FR-037` | ✅ Implemented | 2026-06-05 |
| FR-038 | `validator/journeys/schema.py`, `validator/journeys/llm_visual.py` | `@spec FR-038` | ✅ Implemented | 2026-06-05 |
| FR-039 | `validator/journeys/schema.py`, `validator/journeys/llm_visual.py` | `@spec FR-039` | ✅ Implemented | 2026-06-05 |
| FR-040 | `validator/journeys/migration.py`, `validator/journeys/paths.py`, `migrations/20/migrate.md`, `scripts/migrate-journeys-compile.sh` | `@spec FR-040` | ✅ Implemented | 2026-06-09 |
| FR-041 | `.agent-sync/skills/spec-journey/SKILL.md`, `system/testing/user-journeys.md`, `.agent-sync/skills/spec-test/SKILL.md`, `.agent-sync/skills/spec-feature/SKILL.md`, `.agent-sync/skills/spec-specify/SKILL.md` | `@spec FR-041` | ✅ Implemented | 2026-06-05 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_journey_v2_validation.py` | ✅ Implemented |
| AC-002 | `tests/test_journey_v2_validation.py`, `tests/test_journey_v2_compiler.py` | ✅ Implemented |
| AC-003 | `tests/test_journey_v2_validation.py`, `tests/test_journey_v2_schema.py` | ✅ Implemented |
| AC-004 | `tests/test_journey_v2_schema.py`, `tests/test_journey_v2_validation.py` | ✅ Implemented |
| AC-005 | `tests/test_journey_v2_validation.py`, `tests/test_journey_v2_schema.py` | ✅ Implemented |
| AC-006 | `tests/test_journey_v2_validation.py` | ✅ Implemented |
| AC-007 | `tests/test_journey_v2_impact.py` | ✅ Implemented |
| AC-008 | `tests/test_journey_v2_history.py` | ✅ Implemented |
| AC-009 | `tests/test_journey_v2_history.py` | ✅ Implemented |
| AC-010 | `tests/test_journey_v2_history.py` | ✅ Implemented |
| AC-011 | `tests/test_journey_v2_history.py` | ✅ Implemented |
| AC-012 | `tests/test_journey_v2_docs_skills.py` | ✅ Implemented |
| AC-013 | `tests/test_journey_v2_assignment_bootstrap.py`, `tests/test_journey_v2_docs_skills.py` | ✅ Implemented |
| AC-014 | `tests/test_journey_v2_assignment_bootstrap.py` | ✅ Implemented |
| AC-015 | `tests/test_journey_v2_assignment_bootstrap.py` | ✅ Implemented |
| AC-016 | `tests/test_journey_v2_assignment_bootstrap.py`, `tests/test_journey_v2_compiler.py`, `tests/test_journey_v2_runner.py` | ✅ Implemented |
| AC-017 | `tests/test_journey_v2_assignment_bootstrap.py`, `tests/test_journey_v2_docs_skills.py` | ✅ Implemented |
| AC-018 | `tests/test_journey_v2_schema.py`, `tests/test_journey_v2_validation.py`, `tests/test_journey_v2_compiler.py` | ✅ Implemented |
| AC-019 | `tests/test_journey_v2_doctor.py`, `tests/test_doctor.py` | ✅ Implemented |
| AC-020 | `tests/test_journey_v2_impact.py`, `tests/test_selector.py` | ✅ Implemented |
| AC-021 | `tests/test_journey_v2_impact.py`, `tests/test_journey_v2_cli.py` | ✅ Implemented |
| AC-022 | `tests/test_journey_v2_impact.py` | ✅ Implemented |
| AC-023 | `tests/test_journey_v2_cli.py` | ✅ Implemented |
| AC-024 | `tests/test_journey_v2_cli.py`, `tests/test_journey_v2_compiler.py` | ✅ Implemented |
| AC-025 | `tests/test_journey_v2_cli.py`, `tests/test_journey_v2_runner.py` | ✅ Implemented |
| AC-026 | `tests/test_journey_v2_cli.py`, `tests/test_journey_v2_migration.py`, `tests/integration/test_migration_v19_user_journeys.py` | ✅ Implemented |
| AC-027 | `tests/test_journey_v2_compiler.py`, `tests/test_journey_v2_runner.py` | ✅ Implemented |
| AC-028 | `tests/test_journey_v2_runner.py`, `tests/test_journey_v2_cli.py`, `tests/test_journey_v2_test_integration.py` | ✅ Implemented |
| AC-029 | `tests/test_journey_v2_docs_skills.py`, `tests/test_command_audit_cli.py` | ✅ Implemented |
| AC-030 | `tests/test_journey_v2_test_integration.py`, `tests/test_journey_v2_docs_skills.py` | ✅ Implemented |
| AC-031 | `tests/test_journey_v2_runner.py`, `tests/test_journey_v2_cli.py` | ✅ Implemented |
| AC-032 | `tests/test_journey_v2_compiler.py` | ✅ Implemented |
| AC-033 | `tests/test_journey_v2_compiler.py` | ✅ Implemented |
| AC-034 | `tests/test_journey_v2_compiler.py` | ✅ Implemented |
| AC-035 | `tests/test_journey_v2_schema.py`, `tests/test_journeys.py` | ✅ Implemented |
| AC-036 | `tests/test_journey_v2_schema.py`, `tests/test_journey_v2_impact.py` | ✅ Implemented |
| AC-037 | `tests/test_journey_v2_compiler.py`, `tests/test_journey_v2_schema.py` | ✅ Implemented |
| AC-038 | `tests/test_journey_v2_visual_llm.py`, `tests/test_journey_v2_compiler.py` | ✅ Implemented |
| AC-039 | `tests/test_journey_v2_schema.py`, `tests/test_journey_v2_visual_llm.py` | ✅ Implemented |
| AC-040 | `tests/test_journey_v2_compiler.py`, `tests/test_journey_v2_visual_llm.py` | ✅ Implemented |
| AC-041 | `tests/test_journey_v2_visual_llm.py` | ✅ Implemented |
| AC-042 | `tests/test_journey_v2_schema.py`, `tests/test_journey_v2_visual_llm.py` | ✅ Implemented |
| AC-043 | `tests/test_journey_v2_schema.py`, `tests/test_journey_v2_visual_llm.py` | ✅ Implemented |
| AC-044 | `tests/test_journey_v2_migration.py`, `tests/test_journey_v2_doctor.py` | ✅ Implemented |
| AC-045 | `tests/test_journey_v2_docs_skills.py`, `tests/test_command_registry.py`, `tests/test_agent_sync_layout.py` | ✅ Implemented |
| AC-046 | `tests/test_journey_v2_*.py`, `tests/test_journeys.py` | ✅ Implemented |

## Files Created/Modified

| File | Description |
|---|---|
| `validator/journeys/schema.py` | Pydantic v2 source, coverage, target, action, visual, and privacy models. |
| `validator/journeys/paths.py` | Global v2 path helpers plus explicit v1 discovery for migration only. |
| `validator/journeys/validator.py` | Project-aware v2 validation, qualified ref checks, and history integration. |
| `validator/journeys/index.py` | Reusable journey index by ID, feature, refs, targets, visuals, manifests, and decisions. |
| `validator/journeys/backlinks.py` | Generated feature-local `journeys.md` backlinks. |
| `validator/journeys/history.py` | Changelog/decision/source-hash governance. |
| `validator/journeys/assignment.py` | Deterministic free-form assignment candidates with evidence. |
| `validator/journeys/bootstrap.py` | Existing-project journey candidate bootstrap without writes. |
| `validator/journeys/impact.py` | Journey impact detection from SmartTestSelector, product text, stable selectors, and visual targets. |
| `validator/journeys/compiler.py` | Ahead-of-time compiler facade, native artifact generation, and XcodeGen refresh for generated XCUITest files. |
| `validator/journeys/compiler_registry.py` | Runner backend registry. |
| `validator/journeys/capabilities.py` | Unsupported capability rejection. |
| `validator/journeys/manifest.py` | Compiled manifest read/write semantics plus compiler versioning. |
| `validator/journeys/runner.py` | Compiled-only journey run selection, run-policy gates, stale manifest checks, and native runner execution. |
| `validator/journeys/scanner.py` | Doctor journey stale checks, including old compiler manifests. |
| `validator/journeys/migration.py` | v1 `.journey.yaml` migration to v2 global directories. |
| `validator/journeys/visual_contracts.py` | Native deterministic visual checks. |
| `validator/journeys/llm_visual.py` | Strict JSON LLM screenshot evaluator. |
| `validator/cli_commands/journey_cmd.py` | `livespec journey validate|compile|run|impact|migrate|list|inspect`. |
| `validator/cli_commands/test_cmd.py` | `livespec test` compiled-only journey gate. |
| `.agent-sync/skills/spec-journey/` | User-facing journey create/edit/bootstrap/impact/run/list/inspect workflow. |
| `.agent-sync/skills/spec-feature/SKILL.md` | Compiled-only impacted journey gate wording. |
| `.agent-sync/skills/spec-test/SKILL.md` | Global v2 journey source discovery wording. |
| `.agent-sync/skills/spec-specify/SKILL.md` | Global v2 journey proposal wording. |
| `system/testing/user-journeys.md` | Canonical v2 journey documentation. |
| `README.md` | Public command entrypoint now documents `/spec-journey` and User Journeys v2. |
| `VERSION`, `migrations/19/migrate.md`, `migrations/20/migrate.md`, `scripts/migrate-journeys-compile.sh` | Migration points that refresh agent-sync assets and force old compiled journey manifests to regenerate. |
| `tests/test_journey_v2_*.py` | Focused tests for schema, validation, history, assignment, impact, compile, run, CLI, migration, doctor, docs, and visual/LLM behavior. |
| `tests/integration/test_migration_v19_user_journeys.py` | Integration proof that Migrations 19 and 20 refresh User Journeys assets and force v20 journey recompilation. |

## Verification

- `pytest tests/test_journey_v2_*.py -q` → 38 passed.
- `pytest tests/ --ignore=tests/integration -q` → pass in spec-fix verification.
- `pytest tests/integration/test_migration_v19_user_journeys.py tests/test_journey_v2_docs_skills.py tests/test_command_registry.py tests/test_agent_sync_layout.py -q` → pass in migration/README verification.
- `pytest tests/test_journey_v2_compiler.py tests/test_journey_v2_cli.py tests/integration/test_migration_v19_user_journeys.py -q` → 12 passed.
- Changed-file `ruff check` and `ruff format --check` → pass in spec-fix verification.
- `bash -n scripts/migrate-journeys-compile.sh` → pass.
- `pyright validator/` → pass in spec-fix verification.
