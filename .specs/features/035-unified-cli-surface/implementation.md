---
feature: 035-unified-cli-surface
title: Unified CLI Surface
status: In Progress
updated: 2026-10-12
---

# Implementation — 035 Unified CLI Surface

> Created 2026-10-12 by `/spec-fix` (AC-013 and the human decisions recorded in the spec Clarifications). The original delivery (2026-05-07) shipped no implementation map.

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `validator/cli_commands/test_cmd.py`, `validator/cli_commands/test_selection.py` | `@spec FR-001: test subcommand` | ✅ Implemented | 2026-10-12 |
| FR-002 | `validator/cli_commands/coverage_cmd.py` | `@spec FR-002: coverage subcommand` | ✅ Implemented | 2026-10-12 |
| FR-003 | `validator/cli_commands/drivers_cmd.py` | `@spec FR-003: drivers subcommand` | ✅ Implemented | 2026-10-12 |
| FR-004 | `validator/cli_commands/mutation_cmd.py` | `@spec FR-004: mutation subcommand` | ✅ Implemented | 2026-10-12 |
| FR-005 | `validator/cli_commands/preflight_cmd.py` | `@spec FR-005: preflight subcommand` | ✅ Implemented | 2026-10-12 |
| FR-006 | `validator/cli_resolvers.py` | `@spec FR-006: Pure resolver helpers`, `@spec AC-004: origin/HEAD first`, `@spec AC-002: Unique feature directory` | ✅ Implemented | 2026-10-12 |
| FR-007 | `validator/cli_exit_codes.py` | `@spec FR-007: Structured exit codes` | ✅ Implemented (0/1/2/3/130; codes 2–5 of the old taxonomy retired) | 2026-10-12 |
| FR-008 | `validator/cli_commands/_common.py` | `@spec FR-008: Single-line errors unless --debug` | ✅ Implemented | 2026-10-12 |
| FR-009 | `validator/cli_commands/_common.py`, `validator/cli_commands/drivers_cmd.py` | `@spec FR-009: Structured CI summary` | ✅ Implemented (stderr with `--json`) | 2026-10-12 |
| FR-010 | `docs/cli-reference.md` | Exit-code table, base order, `--feature`, JSON channel | ✅ Implemented | 2026-10-12 |
| FR-011 | `.claude/commands/cli.md`, `.agent-sync/skills/source-command-cli/SKILL.md` | Interactive CLI command | ✅ Implemented | 2026-10-12 |
| FR-012 | `tests/test_cli_unified.py`, `tests/test_cli_unified_exit_codes.py`, `tests/test_cli_unified_feature.py`, `tests/test_cli_unified_acceptance.py` | `@spec FR-012` | ✅ Implemented | 2026-10-12 |

## Acceptance Criteria Mapping

| AC | Test File | Status |
|---|---|---|
| AC-001 | `tests/test_cli_unified.py::test_test_subcommand_happy_path` | ✅ Implemented |
| AC-002 | `tests/test_cli_unified_feature.py::TestResolveFeatureDir::*`, `::TestRunCapabilitySelection::*`, `::TestTestCommandFeature::*` | ✅ Implemented (2026-10-12; previously informational only) |
| AC-003 | `tests/test_cli_unified_acceptance.py::test_test_mutation_output_is_separate_from_coverage` | ✅ Implemented |
| AC-004 | `tests/test_cli_unified_exit_codes.py::TestBaseBranchOrder::*` | ✅ Implemented (origin/HEAD, then main, master, develop, dev) |
| AC-005 | `tests/test_cli_unified_acceptance.py::test_coverage_base_flag_overrides_detection` | ✅ Implemented |
| AC-006 | `tests/test_cli_unified.py::test_drivers_table_shows_python` | ✅ Implemented |
| AC-007 | `tests/test_cli_unified.py::test_drivers_json`, `tests/test_cli_unified_exit_codes.py::test_drivers_json_keeps_stdout_pure_json` | ✅ Implemented |
| AC-008 | `tests/test_cli_unified_acceptance.py::test_mutation_writes_dated_report` | ✅ Implemented |
| AC-009 | `tests/test_cli_unified.py::test_preflight_read_only_table` | ✅ Implemented |
| AC-010 | `tests/test_cli_unified_acceptance.py::test_preflight_fix_delegates_to_feature_034` | ✅ Implemented |
| AC-011 | `tests/test_cli_unified_exit_codes.py::TestExitCodes::*`, `tests/test_cli_unified.py::test_missing_specs_exits_1` | ✅ Implemented |
| AC-012 | `tests/test_cli_unified_exit_codes.py::test_drivers_json_keeps_stdout_pure_json`, `::test_drivers_table_summary_stays_on_stdout` | ✅ Implemented |
| AC-013 | `tests/test_cli_unified_exit_codes.py::test_help_ends_with_executable_example`, `::test_help_example_parser_rejects_unknown_option` | ✅ Implemented (2026-10-12) |
| AC-014 | `tests/test_cli_unified_acceptance.py::test_errors_are_one_line_unless_debug` | ✅ Implemented |
| AC-015 | `docs/cli-reference.md` | ✅ Implemented (documentary) |
| AC-016 | `.claude/commands/cli.md` | ✅ Implemented (documentary) |

## Files Created/Modified

| File | Description |
|---|---|
| `validator/cli_exit_codes.py` | `EXIT_FAILURE`, `EXIT_USAGE`, `EXIT_CONFIG`, `EXIT_INTERRUPTED`; `EXIT_MISSING_SPECS` stays 1 (shared resolver). |
| `validator/cli_commands/_common.py` | Exit 3 without driver, 130 on Ctrl+C, 1 on unexpected errors; `emit_summary(to_stderr=)`; `help_epilog`. |
| `validator/cli_commands/test_cmd.py`, `validator/cli_commands/test_selection.py` | `--feature` resolution and selection, coverage/mutation steps moved out of `test_cmd.py` (now below 300 lines). |
| `validator/cli_commands/coverage_cmd.py`, `drivers_cmd.py`, `mutation_cmd.py`, `preflight_cmd.py` | New exit codes, `--help` examples, JSON summary on stderr. |
| `validator/cli_resolvers.py` | `detect_base_branch` (origin/HEAD, then local branches, tags excluded), `resolve_feature_dir`. |
| `validator/drivers/schemas.py`, `validator/drivers/runner.py` | Additive `DriverCapability.test_selection: append`; `run_capability(test_paths=)` refuses selection without it (`DriverTestSelectionError`; the plan's working name was `TestSelectionUnsupportedError`, renamed so pytest never collects it as a test class). |
| `validator/exceptions.py` | `FeatureResolutionError`, `DriverTestSelectionError`. |
| `livespec/drivers/python.yaml`, `livespec/drivers/templates/custom-driver-template.yaml` | Python coverage declares `test_selection: append`; template documents the field. |
| `docs/cli-reference.md`, `.claude/commands/cli.md`, `.agent-sync/skills/source-command-cli/SKILL.md` | Reference aligned with the new taxonomy, base order, JSON channel and `--feature`. |

## Closure

Feature closure requires a feature-scope `livespec conventions verify --feature 035-unified-cli-surface` PASS. On 2026-10-12 it reports 24 blocking findings, almost all pre-existing debt in touched files: function and file length in `test_cmd.test_command` (feature 078 native options), `coverage_cmd._run_coverage`, `drivers_cmd._run_drivers` and the journey modules, plus `# noqa`/`# type: ignore` directives. The status therefore stays **In Progress** until that debt is burned down (`/spec-fix 035-unified-cli-surface --conventions`).
