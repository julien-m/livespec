# Implementation — 059 Pipeline Verify Phase

> Created after implementation by `/spec-implement` (2026-06-11). Maps every FR/AC to `@spec` anchors in source.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Inject archive.run last ordinal](spec.md#fr-001) | validator/goal_contracts.py (`_archive_run_task`, `_build_goal_tasks`), validator/run_artifacts.py (`ARCHIVE_RUN_TASK_ID`) | `# @spec FR-001: Inject archive.run last ordinal — .specs/features/059-pipeline-verify-phase/spec.md#fr-001` | ✅ Implemented | 2026-06-11 |
| [FR-002: Evidence family constants](spec.md#fr-002) | validator/goal_contracts.py (`ARCHIVE_REQUIRED_EVIDENCE`, `ARCHIVE_INVALID_SUBSTITUTES`, `ARCHIVE_REPAIR_ACTIONS`, `ARCHIVE_RUN_TASK_DESCRIPTION`) | `# @spec FR-002: archive.run evidence family constants (finalize.registry model) — .specs/features/059-pipeline-verify-phase/spec.md#fr-002` | ✅ Implemented | 2026-06-11 |
| [FR-003: Read-only prove validator](spec.md#fr-003) | validator/goal_contracts.py (`_validate_archive_run_evidence`, `_archive_run_artifact_mismatches`, `_offers_tmpdir_contract_state_paths`) | `# @spec FR-003: Read-only prove validator for archive.run — .specs/features/059-pipeline-verify-phase/spec.md#fr-003` | ✅ Implemented | 2026-06-11 |
| [FR-004: Classifier excludes archive.run](spec.md#fr-004) | validator/run_artifacts.py (`goal_tasks_incomplete`), validator/cli_commands/verify_output_cmd.py (re-derivation call site) | `# @spec FR-004: Classifier excludes archive.run — .specs/features/059-pipeline-verify-phase/spec.md#fr-004` | ✅ Implemented | 2026-06-11 |
| [FR-005: Pre-059 backward compatibility](spec.md#fr-005) | validator/run_artifacts.py (`goal_tasks_incomplete` — exclusion never matches pre-059 snapshots; `RUN_ARTIFACT_SCHEMA_VERSION` unchanged at 2.0) | `# @spec FR-005: Pre-059 artifact tolerance (no schema change, exclusion never matches) — .specs/features/059-pipeline-verify-phase/spec.md#fr-005` | ✅ Implemented | 2026-06-11 |
| [FR-006: RUN_ARTIFACT in PHASE_RESULT](spec.md#fr-006) | validator/contracts.py (`PhaseResult.run_artifact`, `phase: preflight`, `_legacy_to_phase_result`), system/contracts/PHASE_RESULT.md, .agent-sync/skills/spec-feature/SKILL.md § PHASE_RESULT Schemas | `# @spec FR-006: RUN_ARTIFACT field, legacy-tolerant (None when absent) — .specs/features/059-pipeline-verify-phase/spec.md#fr-006` | ✅ Implemented | 2026-06-11 |
| [FR-007: Supervisor Verify phase](spec.md#fr-007) | .agent-sync/skills/spec-feature/SKILL.md (§ Supervisor Verify Phase + 5 `[always]` Execution Tasks entries + per-phase receive steps) | `<!-- @spec FR-007: Supervisor Verify phase — .specs/features/059-pipeline-verify-phase/spec.md#fr-007 -->` | ✅ Implemented | 2026-06-11 |
| [FR-008: SHIP_RESULT run_artifact + ship gate](spec.md#fr-008) | validator/contracts.py (`ShipResult.run_artifact`), system/contracts/SHIP_RESULT.md, .agent-sync/skills/spec-ship/SKILL.md (Step 3 artifact cross-check + `[always]` task) | `# @spec FR-008: SHIP_RESULT run_artifact gates merge/delete — .specs/features/059-pipeline-verify-phase/spec.md#fr-008` | ✅ Implemented | 2026-06-11 |
| [FR-009: Transcript capture protocol](spec.md#fr-009) | system/anti-drift-block.md (§5 Transcript capture + Archive & prove archive.run), .agent-sync/skills/spec-feature/SKILL.md (phase prompt blocks) | `<!-- @spec FR-009: Transcript capture protocol — .specs/features/059-pipeline-verify-phase/spec.md#fr-009 -->` | ✅ Implemented | 2026-06-11 |
| [FR-010: SKIP semantics preserved](spec.md#fr-010) | tests/test_goal_archive_cli.py (`TestTranscriptContainsRules` — engine-behavior locks, no engine change) | `# @spec FR-010: SKIP semantics independent of transcript availability — .specs/features/059-pipeline-verify-phase/spec.md#fr-010` | ✅ Implemented | 2026-06-11 |
| [FR-011: Protected scope](spec.md#fr-011) | validator/journeys/runner.py, tests/test_journey_v2_runner.py — NOT modified (verified via git status; no 059 test imports them) | n/a (enforced by absence of change) | ✅ Implemented | 2026-06-11 |

## Acceptance Criteria Mapping

| AC | Test File / Evidence | Status |
|---|---|---|
| AC-001 | tests/test_goal_contracts.py `test_every_contract_carries_exactly_one_archive_run_task`, `test_every_registry_command_contract_ends_with_archive_run` (SC-001 sweep) | ✅ Implemented |
| AC-002 | tests/test_goal_contracts.py `test_archive_run_task_has_strictly_highest_ordinal`, `test_archive_run_injection_preserves_hash_determinism` | ✅ Implemented |
| AC-003 | tests/test_goal_contracts.py `test_archive_run_task_evidence_family_matches_constants`, `test_archive_run_task_skips_convention_evidence_layering`, `test_archive_run_prove_rejects_prose_claim`, `test_archive_run_prove_rejects_exit_code_substitute`, `test_archive_run_prove_rejects_tmpdir_contract_state_paths` | ✅ Implemented |
| AC-004 | tests/test_goal_contracts.py `test_archive_run_prove_rejects_path_outside_specs_runs`, `test_archive_run_prove_rejects_malformed_artifact_file`, `test_archive_run_prove_rejects_foreign_goal_artifact`, `test_archive_run_prove_rejects_foreign_command_artifact` | ✅ Implemented |
| AC-005 | tests/test_goal_contracts.py `test_archive_run_prove_accepts_matching_artifact_read_only` (runs-dir listing unchanged) | ✅ Implemented |
| AC-006 | tests/test_run_artifact.py `TestArchiveRunExclusion`, tests/test_verify_output_cli.py `TestArchiveRunExclusion`, tests/test_goal_contracts.py `test_archive_run_end_to_end_drill` (SC-004) | ✅ Implemented |
| AC-007 | tests/test_run_artifact.py `test_pre_059_*`, tests/test_verify_output_cli.py `test_pre_059_artifact_without_archive_run_verifies_cleanly` | ✅ Implemented |
| AC-008 | tests/test_contracts.py `TestPhaseResultRunArtifact`, `TestPhaseResultLegacyRunArtifact` | ✅ Implemented |
| AC-009 | .agent-sync/skills/spec-feature/SKILL.md § Supervisor Verify Phase (matrix) + tests/test_verify_output_cli.py `TestVerifyMatrixSubstrate` (machine substrate per outcome class) | ✅ Implemented |
| AC-010 | SKILL § Supervisor Verify Phase step 2 (latest fallback / canonical BLOCKED) + `TestVerifyMatrixSubstrate::test_outcome_blocked_exit_2_on_missing_run_path` | ✅ Implemented |
| AC-011 | tests/test_contracts.py `TestShipResultRunArtifact` + .agent-sync/skills/spec-ship/SKILL.md Step 3 artifact cross-check | ✅ Implemented |
| AC-012 | spec-ship SKILL Step 3 (cross-check before Step 3.5/4) + `[always]` execution task (enforced goal task, verified via `livespec goal render spec-ship`) | ✅ Implemented |
| AC-013 | tests/test_goal_archive_cli.py `TestTranscriptContainsRules::test_contains_rule_passes_against_embedded_transcript`, `test_contains_rule_fails_when_needle_absent_from_transcript` + system/anti-drift-block.md §5 Transcript capture | ✅ Implemented |
| AC-014 | tests/test_goal_archive_cli.py `test_contains_rule_skips_without_transcript_and_archive_succeeds`, `test_executor_truncated_transcript_is_accepted`, `test_archive_oversized_transcript_blocks_exit_2` (pre-existing regression guard) | ✅ Implemented |
| AC-015 | git status: `validator/journeys/runner.py` and `tests/test_journey_v2_runner.py` carry only their pre-existing WIP diffs; no 059 modification | ✅ Implemented |

> **Test status (2026-06-11, `/spec-test --auto --update`):** 15/15 AC Covered — targeted suite 218/218 passed; full unit suite 1824 passed / 4 env skips / 1 pre-existing protected failure (`tests/test_journeys.py::test_compile_generates_xcuitest_for_ios_and_watchos`, baseline); integration 3a 75/75. Report: [checks/2026-06-11-test.md](checks/2026-06-11-test.md).

## Files Created/Modified

**Modified (validator):**
- `validator/goal_contracts.py` — archive.run constants, compiler-side injection (`_archive_run_task`), prove-validator routing + `_validate_archive_run_evidence`
- `validator/run_artifacts.py` — `ARCHIVE_RUN_TASK_ID`, public `goal_tasks_incomplete` (archive.run exclusion)
- `validator/cli_commands/verify_output_cmd.py` — re-derivation uses shared `goal_tasks_incomplete`
- `validator/contracts.py` — `PhaseResult.run_artifact` + `preflight` literal, `ShipResult.run_artifact`, legacy KV bridge

**Modified (docs/skills):**
- `system/anti-drift-block.md` — §5 Transcript capture + Archive & prove archive.run subsections
- `system/contracts/PHASE_RESULT.md` — run_artifact, preflight, Supervisor Verify caller behaviour
- `system/contracts/SHIP_RESULT.md` — run_artifact, extended critical safety property
- `.agent-sync/skills/spec-feature/SKILL.md` — schemas (incl. Preflight), prompt transcript wiring, § Supervisor Verify Phase, Execution Tasks, Ship Result
- `.agent-sync/skills/spec-ship/SKILL.md` — Step 2 prompt, Step 3 artifact cross-check, Execution Task
- `.agent-sync/skills/spec-ship/expectations.md` — `last_reviewed: 2026-06-11`

**Modified (tests):**
- `tests/test_goal_contracts.py`, `tests/test_run_artifact.py`, `tests/test_verify_output_cli.py`, `tests/test_contracts.py`, `tests/test_goal_archive_cli.py`

**Validation (2026-06-11):** `ruff check .` PASS · `ruff format --check .` PASS (317 files) · `pyright` 0 errors · targeted and integration suites passed; full unit baseline: 1968 passed, 37 skipped, 1 pre-existing protected failure (`tests/test_journeys.py::test_compile_generates_xcuitest_for_ios_and_watchos`, untouched), so full pytest exits non-zero.
