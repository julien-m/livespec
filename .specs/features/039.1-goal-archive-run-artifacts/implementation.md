---
feature: 039.1-goal-archive-run-artifacts
title: Implementation — Feature 039.1 — Goal Archive & Run Artifacts v2
---

# Implementation — Feature 039.1 — Goal Archive & Run Artifacts v2

> Maps every FR and AC from `spec.md` to the `@spec` anchor in source code.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: goal archive CLI surface](spec.md#fr-001) | `validator/cli_commands/goal_cmd.py` | `# @spec FR-001: archive CLI surface + exit mapping — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-001` | ✅ Implemented | 2026-06-10 |
| [FR-002: RunArtifact v2 schema + writer](spec.md#fr-002) | `validator/run_artifacts.py` | `# @spec FR-002: v2 schema + atomic timestamp-led writer — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-002` | ✅ Implemented | 2026-06-10 |
| [FR-003: transcript handling](spec.md#fr-003) | `validator/run_artifacts.py` (embedding), `validator/verify_output.py` (`_evaluate_contains` SKIP) | `# @spec FR-003: optional transcript embedding — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-003` | ✅ Implemented | 2026-06-10 |
| [FR-004: receipt integrity re-verification](spec.md#fr-004) | `validator/run_receipts.py` | `# @spec FR-004: receipt integrity re-verification — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-004` | ✅ Implemented | 2026-06-10 |
| [FR-005: verify-output CLI surface](spec.md#fr-005) | `validator/cli_commands/verify_output_cmd.py`, `validator/cli_commands/__init__.py` (registration), `validator/run_artifacts.py` (`find_latest_artifact`, `load_run_artifact`) | `# @spec FR-005: verify-output CLI + alias + blocked handling — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-005` | ✅ Implemented | 2026-06-10 |
| [FR-006: shared rule engine](spec.md#fr-006) | `validator/verify_output.py`, `validator/verify_output_report.py` (rendering split) | `# @spec FR-006: shared engine 4 kinds + cumulative when — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-006` | ✅ Implemented | 2026-06-10 |
| [FR-007: outcome + placeholder wiring](spec.md#fr-007) | `validator/verify_output.py` (reuses `validator/outcome.py`, `validator/placeholders.py`) | `# @spec FR-007: outcome + placeholder wiring — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-007` | ✅ Implemented | 2026-06-10 |
| [FR-008: real preview.py](spec.md#fr-008) | `validator/preview.py` | `# @spec FR-008: render_preview 4 sources + save_preview — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-008` | ✅ Implemented | 2026-06-10 |
| [FR-009: 3 canonical preview errors](spec.md#fr-009) | `validator/cli_commands/verify_output_cmd.py` (`_run_preview`), `validator/expectations.py` (existing AC-008/009 messages, unchanged) | `# @spec FR-009: 3 canonical preview error paths, exit 2 — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-009` | ✅ Implemented | 2026-06-10 |
| [FR-010: documentation truth-fixes](spec.md#fr-010) | `.specs/features/039-command-expectations-and-verify-output/implementation.md`, `.specs/features/040-expectations-rich-and-verify-preview/implementation.md`, `system/expectations.md` (§8.6 RunArtifact v2), `.agent-sync/skills/spec-feature/SKILL.md` (§Run Artifact Emission), `.agent-sync/skills/spec-verify-output/expectations.md` (§4/§13 + `last_reviewed`) | Markdown truth-fixes — guarded by `tests/test_run_artifact.py::TestTruthFixes` | ✅ Implemented | 2026-06-10 |
| [FR-011: protected scope](spec.md#fr-011) | _(no file changes by design)_ — `validator/journeys/runner.py`, `tests/test_journey_v2_runner.py`, roadmap MVP 041/042/043 untouched; no lock primitive for `.specs/.runs/` | Verified via `git diff --name-only` at Step 9 | ✅ Implemented | 2026-06-10 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_goal_archive_cli.py::TestGoalArchiveCli::test_archive_success_round_trip`, `tests/test_run_artifact.py::TestArchiveHappyPath::test_inputs_not_mutated` | ✅ |
| AC-002 | `tests/test_goal_archive_cli.py` (success 0 / drift 1 / blocked 2, nothing written) | ✅ |
| AC-003 | `tests/test_run_artifact.py::TestArchiveHappyPath::{test_filename_is_timestamp_led_with_hash8, test_atomic_write_leaves_no_tmp_residue}` | ✅ |
| AC-004 | `tests/test_run_artifact.py::TestArchiveHappyPath::{test_complete_goal_archives_as_success, test_goal_snapshot_fields, test_v1_unobservable_fields_absent}` | ✅ |
| AC-005 | `tests/test_run_artifact.py::TestArchiveTranscripts`, `tests/test_verify_output.py::TestSkipSemantics` | ✅ |
| AC-006 | `tests/test_run_artifact.py::TestReceiptIntegrity` (valid / tampered / missing / feature scoping) | ✅ |
| AC-007 | `tests/test_verify_output_cli.py` (latest, `--run`, `--scenario`, `--feature`, `--json`, alias resolution, malformed blocked) | ✅ |
| AC-008 | `tests/test_verify_output.py::{TestWhenBranches, TestNoShortCircuit, TestMayAndMustNot, TestPathRules}` | ✅ |
| AC-009 | `tests/test_verify_output.py::{TestOutcomeMatrix, TestPlaceholders}` (`<date>` from artifact timestamp) | ✅ |
| AC-010 | `tests/test_preview.py::{TestRenderPreview, TestSavePreview}` + live `livespec verify-output specify --preview` on this repo (exit 0, real slugs + stack) | ✅ |
| AC-011 | `tests/test_preview.py::TestPreviewCli` (3 canonical errors, exit 2) | ✅ |
| AC-012 | `tests/test_run_artifact.py::TestTruthFixes` (4 static assertions) | ✅ |
| AC-013 | Step 9 protected-scope check (`git diff --name-only`); no `validator/locks.py` import in new modules | ✅ |

## Edge Case Coverage

| EC | Coverage |
|---|---|
| EC-001 | `tests/test_run_artifact.py::TestArchiveOutcomes::test_hash_mismatch_blocks_and_writes_nothing`, `tests/test_goal_archive_cli.py::test_archive_hash_mismatch_blocks_exit_2` |
| EC-002 | `tests/test_run_artifact.py::TestArchiveOutcomes::test_incomplete_goal_is_drift` |
| EC-003 | `tests/test_run_artifact.py::TestArtifactHelpers::{test_same_second_archives_coexist, test_find_latest_artifact_picks_lex_last}` |
| EC-004 | `tests/test_run_artifact.py::TestReceiptIntegrity::test_missing_receipt_file_is_error` |
| EC-005 | `tests/test_run_artifact.py::TestArchiveTranscripts::test_contains_rules_skip_without_transcript`, `tests/test_verify_output.py::TestSkipSemantics::test_contains_skip_without_transcript` |
| EC-006 | `tests/test_verify_output.py::TestPlaceholders::test_date_resolved_from_artifact_timestamp_not_clock` |
| EC-007 | `tests/test_run_artifact.py::TestArtifactHelpers::test_load_run_artifact_names_malformed_path`, `tests/test_verify_output_cli.py::test_malformed_artifact_blocks_naming_path` |
| EC-008 | `tests/test_run_artifact.py::TestReceiptIntegrity::test_feature_scoping_only_with_feature` |
| EC-009 | `tests/test_preview.py::TestRenderPreview::{test_partial_sources_render_not_configured, test_empty_screens_directory_not_configured}` |
| EC-010 | `tests/test_run_artifact.py::TestArtifactHelpers::test_same_second_archives_coexist` |
| EC-011 | `tests/test_run_artifact.py::TestArchiveOutcomes::test_null_exit_code_records_null_and_skips_exit_rules`, `tests/test_verify_output.py::TestSkipSemantics::test_exit_code_rule_skips_when_exit_code_null` |

## Files Created

- `validator/run_artifacts.py` — RunArtifact v2 schema, builder, atomic writer, loader (232 lines)
- `validator/run_receipts.py` — receipt integrity re-verification (split for the 300-line cap, `finalize_receipt.py` precedent)
- `validator/verify_output.py` — shared 4-state rule engine
- `validator/verify_output_report.py` — report table + JSON envelope (rendering split per plan risk note)
- `validator/preview.py` — real `render_preview` (4 sources) + `save_preview`
- `validator/cli_commands/verify_output_cmd.py` — `livespec verify-output` CLI
- `tests/test_run_artifact.py`, `tests/test_verify_output.py`, `tests/test_verify_output_cli.py`, `tests/test_preview.py`, `tests/test_goal_archive_cli.py` — 81 tests (71 initial + audit/security invariant tests)

## Files Modified

- `validator/cli_commands/goal_cmd.py` — `goal archive` subcommand
- `validator/cli_commands/__init__.py` — `verify-output` registration
- `.agent-sync/skills/spec-feature/SKILL.md` — §Run Artifact Emission rewritten to `livespec goal archive`
- `.agent-sync/skills/spec-verify-output/expectations.md` — §4/§13 contradiction resolved, `last_reviewed` bumped
- `system/expectations.md` — §8.6 "RunArtifact v2 (goal archive)" added
- `.specs/features/039-command-expectations-and-verify-output/implementation.md` — FR-005/006/007 + EC rows remapped to real files
- `.specs/features/040-expectations-rich-and-verify-preview/implementation.md` — FR-005..009/011 rows remapped to real files

## Test Results

```
Full suite: 1762 passed, 4 skipped (same skip count as the pre-change baseline: 1691 passed, 4 skipped)
Pre-existing failure unrelated to this feature: tests/test_journeys.py::test_compile_generates_xcuitest_for_ios_and_watchos (protected journeys WIP)
ruff check . — clean · ruff format --check . — clean · pyright — 0 errors
```

**Verified by `/spec-test` (2026-06-10):** 13/13 AC covered, 71/71 initial feature tests pass in isolation; post-audit feature suite is 81/81 passing. Full suite 1762 passed / 4 skipped (baseline) / 1 pre-existing journeys-WIP failure; pyright + ruff clean. Report: [`checks/2026-06-10-test.md`](checks/2026-06-10-test.md).
