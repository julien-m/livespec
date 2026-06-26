---
title: Journey Fixture Bootstrap Contract Implementation
feature: 060-journey-fixture-bootstrap-contract
status: Implemented
created: 2026-06-11
updated: 2026-06-25
---

# Implementation — Journey Fixture Bootstrap Contract (060)

**Date:** 2026-06-11
**Status:** Implemented
**Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Contract models, loader, path helper](spec.md#fr-001) | validator/journeys/fixtures.py, validator/journeys/paths.py | `# @spec FR-001: Contract models and loader — .specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-001` · `# @spec FR-001: fixtures_contract_path helper — …#fr-001` | ✅ Implemented | 2026-06-11 |
| [FR-002: resolve_bootstrap derivation](spec.md#fr-002) | validator/journeys/fixtures.py | `# @spec FR-002: resolve_bootstrap derivation rules — .specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-002` | ✅ Implemented | 2026-06-11 |
| [FR-003: preconditions.bootstrap override](spec.md#fr-003) | validator/journeys/schema.py | `# @spec FR-003: Optional preconditions.bootstrap override — .specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-003` | ✅ Implemented | 2026-06-11 |
| [FR-004: Five blocking validation rules](spec.md#fr-004) | validator/journeys/validator.py, validator/journeys/_fixtures_helpers.py | `# @spec FR-004: Five blocking fixture-contract validation rules — …#fr-004` · `# @spec FR-004: Paste-ready contract skeleton — …#fr-004` | ✅ Implemented | 2026-06-11 |
| [FR-005: Derived XCUITest bootstrap waits](spec.md#fr-005) | validator/journeys/compiler.py | `# @spec FR-005: Derived bootstrap waits enter codegen, FR-006: contract hash — …#fr-005` · `# @spec FR-005: Bootstrap waits emitted after app.launch() — …#fr-005` | ✅ Implemented | 2026-06-11 |
| [FR-006: Compiler bump + additive contract hash](spec.md#fr-006) | validator/journeys/manifest.py, validator/journeys/compiler.py | `# @spec FR-006: Version bump and additive fixtures_contract_hash — …#fr-006` | ✅ Implemented | 2026-06-11 |
| [FR-007: Runner contract-hash staleness](spec.md#fr-007) | validator/journeys/runner.py | `# @spec FR-007: Contract hash staleness check — …#fr-007` | ✅ Implemented | 2026-06-11 |
| [FR-008: Bootstrap failure reclassification](spec.md#fr-008) | validator/journeys/runner.py, validator/journeys/fixtures.py (`BOOTSTRAP_FAILURE_PREFIX`) | `# @spec FR-008: Bootstrap failure prefix reclassification — …#fr-008` | ✅ Implemented | 2026-06-11 |
| [FR-009: Scaffold + CLI subcommand](spec.md#fr-009) | validator/journeys/_fixtures_helpers.py (re-exported by fixtures.py), validator/cli_commands/journey_cmd.py | `# @spec FR-009: Idempotent fixtures contract scaffold — …#fr-009` · `# @spec FR-009: journey fixtures scaffold CLI subcommand — …#fr-009` | ✅ Implemented | 2026-06-11 |
| [FR-010: Migration v21](spec.md#fr-010) | migrations/21/migrate.md, scripts/migrate-journeys-fixtures-scaffold.sh, VERSION (20→21) | `<!-- @spec FR-010: Fully automatic migration v21 — …#fr-010 -->` · `# @spec(FR-010)` | ✅ Implemented | 2026-06-11 |
| [FR-011: user-journeys.md doc section](spec.md#fr-011) | system/testing/user-journeys.md | `<!-- @spec FR-011: Fixture bootstrap contract documentation — …#fr-011 -->` | ✅ Implemented | 2026-06-11 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| [AC-001](spec.md#ac-001) Contract parses; invalid input → `journey_fixtures_contract_invalid` | tests/test_journey_v2_fixtures_contract.py (`test_read_full_contract_parses_models`, `test_read_minimal_contract_defaults`, `test_read_contract_invalid_yaml_is_blocking_issue`, `test_read_contract_non_mapping_root_is_blocking_issue`, `test_read_contract_rejects_unknown_keys`, `test_read_contract_rejects_out_of_bounds_timeouts`, `test_validation_invalid_contract_is_blocking`, chaos: binary/partial/huge) | ✅ |
| [AC-002](spec.md#ac-002) Sorted deduplicated union, 0–1 distinct screen | `test_resolve_bootstrap_single_fixture_full_plan`, `test_resolve_bootstrap_union_is_sorted_and_deduplicated`, `test_resolve_bootstrap_zero_screens_omits_expected_screen`, `test_resolve_bootstrap_seed_only_fixture_is_ready_only`, `test_compile_v2_xcuitest_seed_only_fixture_waits_ready_only` | ✅ |
| [AC-003](spec.md#ac-003) Ambiguity → `journey_bootstrap_ambiguous` | `test_resolve_bootstrap_ambiguous_screens_raise`, `test_validation_ambiguous_screens_block_without_override`, `test_validation_ambiguous_screens_pass_with_override` | ✅ |
| [AC-004](spec.md#ac-004) Override replaces screen / appends markers; schema_version stays 2 | `test_resolve_bootstrap_override_replaces_screen_and_appends_markers`, `test_journey_schema_accepts_bootstrap_override`, `test_journey_schema_without_bootstrap_stays_valid` | ✅ |
| [AC-005](spec.md#ac-005) Wait order + `XCTFail` prefix helper, per-wait timeout | tests/test_journey_v2_compiler.py (`test_compile_v2_xcuitest_emits_bootstrap_waits_in_order`) | ✅ |
| [AC-006](spec.md#ac-006) Missing contract → skeleton in message (incl. deleted-after-compile) | `test_validation_missing_contract_embeds_skeleton`, `test_validation_contract_deleted_after_compile_blocks` | ✅ |
| [AC-007](spec.md#ac-007) Unknown id / surface mismatch; XCUITest-only enforcement | `test_validation_unknown_fixture_and_mock_ids_block`, `test_validation_surface_mismatch_blocks`, `test_validation_non_xcuitest_journey_is_not_enforced`, `test_validation_correctly_declared_journey_passes` | ✅ |
| [AC-008](spec.md#ac-008) `journeys-v2-3` + unconditional `journey_compiler_stale` | tests/test_journey_v2_compiler.py (`test_compile_v2_manifest_records_version_bump_and_contract_hash`), tests/test_journey_v2_runner.py (`test_run_journeys_reports_compiler_stale_before_contract_hash`, `test_run_journeys_fails_old_compiler_manifest_without_recompiling`) | ✅ |
| [AC-009](spec.md#ac-009) Additive `fixtures_contract_hash`, tolerant reader, runner staleness | `test_compile_v2_manifest_contract_hash_empty_without_contract`, `test_manifest_reader_tolerates_missing_contract_hash_field`, `test_run_journeys_fails_stale_contract_hash_without_recompiling`, `test_run_journeys_fails_when_contract_deleted_after_compile` | ✅ |
| [AC-010](spec.md#ac-010) Prefix scan reclassification, no xcresult parsing | tests/test_journey_v2_runner.py (`test_run_journeys_reclassifies_bootstrap_failure_prefix`, `test_run_journeys_keeps_native_run_failed_without_prefix`, `test_run_journeys_ignores_prefix_on_passing_run`) | ✅ |
| [AC-011](spec.md#ac-011) Scaffold enumerates/infers, idempotent, round-trips | `test_scaffold_enumerates_ids_and_infers_surfaces`, `test_scaffold_never_overwrites_existing_contract`, `test_scaffold_round_trip_validates_and_compiles_without_waits` | ✅ |
| [AC-012](spec.md#ac-012) Migration v21 end-to-end automatic, green with/without fixture journeys | `test_migration_v21_manifest_structure`, `test_migration_v21_scaffold_script_wrapper`, `test_migration_shaped_scaffold_compile_round_trip`, `test_migration_shaped_project_without_fixture_journeys`, `test_scaffold_without_fixture_journeys_writes_nothing` | ✅ |
| [AC-013](spec.md#ac-013) CLI `livespec journey fixtures scaffold` exit codes/output | `test_cli_journey_fixtures_scaffold_exit_codes_and_output`, `test_cli_journey_fixtures_scaffold_no_fixture_journeys` | ✅ |
| [AC-014](spec.md#ac-014) Fixture-less identity (byte-identical codegen, no contract required) | `test_compile_v2_fixture_less_codegen_is_identity_snapshot`, `test_resolve_bootstrap_no_fixtures_no_mocks_is_none`, `test_resolve_bootstrap_collapses_empty_plan_to_none`, `test_validation_journey_without_fixtures_needs_no_contract` | ✅ |
| [AC-015](spec.md#ac-015) Doc section in user-journeys.md | Manual review — `system/testing/user-journeys.md` § "Fixture Bootstrap Contract" (schema, derivation, app-side responsibilities, staleness/recompilation, 5 error codes + scaffold recovery) | ✅ |

> **Verified by `/spec-test` 2026-06-11** — 15/15 AC Covered/Pass (100%), 0 generated; feature suites 102/102 with zero skips; full no-LLM suite 1882 passed / 4 pre-existing hardware-gated skips; ruff + pyright clean. Report: [checks/2026-06-11-test.md](checks/2026-06-11-test.md)

## Files Created/Modified

**Created:**
- `validator/journeys/fixtures.py` — public API: contract models (frozen Pydantic), `read_fixtures_contract[_with_hash]`, `fixtures_contract_hash`, `resolve_bootstrap` + `BootstrapAmbiguityError`, `render_contract_skeleton`, `scaffold_fixtures_contract` (re-exported), `BOOTSTRAP_FAILURE_PREFIX` — 260 lines
- `validator/journeys/_fixtures_helpers.py` — private internals (skeleton renderer, scaffold, journey-source reader), 132 lines — extraction per the plan-locked 300-line constitution resolution; the public surface stays importable from `fixtures.py`
- `tests/test_journey_v2_fixtures_contract.py` — 43 tests (parsing, derivation, validation rules, scaffold, CLI, migration-shaped, chaos)
- `migrations/21/migrate.md` — asset-sync migration: agent-sync refresh → fixtures scaffold → force compile → SET_VERSION 21
- `scripts/migrate-journeys-fixtures-scaffold.sh` — versioned-CLI scaffold wrapper (exit 0 for all no-op outcomes)

**Modified:**
- `validator/journeys/paths.py` — `fixtures_contract_path()`
- `validator/journeys/schema.py` — `BootstrapOverride`, `Preconditions.bootstrap` (additive, schema_version stays 2)
- `validator/journeys/validator.py` — `_validate_fixtures_contract` + reference/ambiguity helpers (5 blocking ERROR codes)
- `validator/journeys/compiler.py` — single contract read per compile, `_xcuitest_bootstrap_waits`, `waitForJourneyBootstrap` helper via `_xcuitest_helpers`, both manifest write paths pass `fixtures_contract_hash`
- `validator/journeys/manifest.py` — `COMPILER_VERSION = "journeys-v2-3"`, additive `CompiledManifest.fixtures_contract_hash` with tolerant reader (`MANIFEST_SCHEMA_VERSION` stays 1)
- `validator/journeys/runner.py` — contract-hash staleness check (order: source_hash → compiler_version → fixtures_contract_hash) + `journey_bootstrap_marker_missing` reclassification (no xcresult access)
- `validator/cli_commands/journey_cmd.py` — nested `fixtures` Typer app with `scaffold` command
- `system/testing/user-journeys.md` — "Fixture Bootstrap Contract" section + Execution Rules staleness bullet
- `VERSION` — 20 → 21
- `tests/test_journey_v2_compiler.py` — 6 new tests + contract added to pre-existing preconditions test (now required by blocking enforcement)
- `tests/test_journey_v2_runner.py` — 6 new tests
- `tests/test_journeys.py` — legacy `_write_journey` fixture: deep-link route for XCUITest (fixes a pre-existing failure at HEAD caused by feature 057's capability gate)

## Visual Baselines

Not applicable — CLI/codegen feature, no UI, no `## Screens` section.

## Notes

- Plan steps 5 and 6 landed as one atomic diff (locked review resolution #1); steps 2 and 3 landed as one small combined diff because override semantics (FR-002) require the schema field (FR-003) — both recorded as separate checkpoints with shared green gates.
- E2E simulator verification is consumer-side (STRAPT) post-release per plan Resolved Test Commands (CI has no simulator).
