---
type: implementation
title: Cross-Language Test Driver Architecture
feature: 016-cross-language-test-driver-architecture
spec_ref: spec.md
plan_ref: plan.md
created: 2026-05-06
updated: 2026-05-06
status: Implemented
---

# Implementation — Cross-Language Test Driver Architecture

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `validator/drivers/schemas.py` | `@spec FR-001: YAML driver schema with 5 optional capabilities` | Implemented | 2026-05-06 |
| FR-002 | `validator/drivers/registry.py` | `@spec FR-002: DriverRegistry with built-in + custom scan` | Implemented | 2026-05-06 |
| FR-003 | `validator/drivers/runner.py` | `@spec FR-003: run_driver_capability function` | Implemented | 2026-05-06 |
| FR-004 | `validator/drivers/degradation.py` | `@spec FR-004: Degradation message when registry empty` | Implemented | 2026-05-06 |
| FR-005 | `validator/drivers/patch_coverage.py` | `@spec FR-005: compute_patch_coverage` | Implemented | 2026-05-06 |
| FR-006 | `validator/drivers/scaffold.py`, `validator/drivers/cli.py` | `@spec FR-006: livespec spec-driver --new` | Implemented | 2026-05-06 |
| FR-007 | `validator/drivers/__init__.py` | `@spec FR-007: Stable Python API for slash commands` | Implemented | 2026-05-06 |
| FR-008 | `validator/drivers/loader.py` | `@spec FR-008: Schema validation on load` | Implemented | 2026-05-06 |

## Files Created

| File | Purpose |
|---|---|
| `validator/drivers/__init__.py` | Public API re-exports |
| `validator/drivers/schemas.py` | Pydantic models (`DriverManifest`, `DriverCapability`, `CapabilityResult`, `PatchCoverageReport`, `CapabilityNotImplementedError`) |
| `validator/drivers/loader.py` | `load_manifest()` — YAML parse + Pydantic validate, WARNING on failure |
| `validator/drivers/registry.py` | `DriverRegistry` — discover built-in + custom drivers, match against project root |
| `validator/drivers/runner.py` | `run_capability()` — subprocess exec for `command` / `script`, captures result |
| `validator/drivers/patch_coverage.py` | `parse_lcov`, `parse_diff`, `compute_patch_coverage`, `git_diff` (local, no external service) |
| `validator/drivers/degradation.py` | `format_degradation_message()` for unsupported stacks |
| `validator/drivers/scaffold.py` | `scaffold_custom_driver()` — writes `.specs/drivers/<stack>.yaml` from template |
| `validator/drivers/cli.py` | Typer subcommand `livespec spec-driver --new <stack> [--force]` |
| `livespec/drivers/python.yaml` | Built-in driver stub (detect only) |
| `livespec/drivers/typescript.yaml` | Built-in driver stub (detect only) |
| `livespec/drivers/swift.yaml` | Built-in driver stub (detect only) |
| `livespec/drivers/go.yaml` | Built-in driver stub (detect only) |
| `livespec/drivers/jvm.yaml` | Built-in driver stub (detect only) |
| `tests/test_drivers.py` | 35 tests covering schemas, loader, registry, runner, patch coverage, degradation, scaffold, CLI |

## Files Modified

| File | Change |
|---|---|
| `validator/cli.py` | Register `driver_app` under `livespec spec-driver` namespace |

## Functional Requirements Mapping

| Requirement | File(s) | @spec Anchor | Status |
|---|---|---|---|
| FR-001 | `validator/drivers/schemas.py` | `# @spec FR-001` | Implemented |
| FR-002 | `validator/drivers/registry.py` | `# @spec FR-002` | Implemented |
| FR-003 | `validator/drivers/runner.py` | `# @spec FR-003` | Implemented |
| FR-004 | `validator/drivers/degradation.py` | `# @spec FR-004` | Implemented |
| FR-005 | `validator/drivers/patch_coverage.py` | `# @spec FR-005` | Implemented |
| FR-006 | `validator/drivers/scaffold.py`, `validator/drivers/cli.py` | `# @spec FR-006` | Implemented |
| FR-007 | `validator/drivers/__init__.py` | `# @spec FR-007` | Implemented |
| FR-008 | `validator/drivers/loader.py` | `# @spec FR-008` | Implemented |

## Acceptance Criteria Mapping

| AC | Test Case | Status |
|---|---|---|
| AC-001 | `test_driver_manifest_all_capabilities_optional`, `test_driver_capability_unknown_field_rejected` | Implemented |
| AC-002 | `test_driver_manifest_all_capabilities_optional`, `test_run_capability_missing_capability_raises` | Implemented |
| AC-003 | `test_builtin_drivers_load_via_default_dir`, `test_registry_default_builtin_dir_resolves` | Implemented |
| AC-004 | `test_registry_custom_overrides_builtin` | Implemented |
| AC-005 | `test_registry_discovers_builtin_only` | Implemented |
| AC-006 | `test_registry_custom_overrides_builtin`, `test_registry_alphabetical_among_custom` | Implemented |
| AC-007 | `test_format_degradation_message_elixir`, `test_format_degradation_message_no_signals` | Implemented |
| AC-008 | `test_scaffold_creates_yaml`, `test_scaffold_refuses_overwrite`, `test_scaffold_force_overwrites`, `test_cli_spec_driver_new_*` | Implemented |
| AC-009 | `test_run_capability_command_success`, `test_run_capability_command_failure` | Implemented |
| AC-010 | `test_run_capability_script_runs`, `test_run_capability_script_missing_raises` | Implemented |
| AC-011 | `test_run_capability_coverage_validates_report_exists`, `test_run_capability_coverage_with_report_present` | Implemented |
| AC-012 | `test_compute_patch_coverage_full_partial_missing`, `test_compute_patch_coverage_empty_diff` | Implemented |
| AC-013 | Public API exposed via `validator.drivers.run_capability` | Implemented |
| AC-014 | `test_load_manifest_malformed_yaml_returns_none`, `test_registry_skips_malformed_and_loads_rest` | Implemented |
| AC-015 | No imports of Codecov/Coveralls/SonarCloud (verified by grep + dependency list) | Implemented |

## Test Results

- 35 driver tests pass
- 637 tests pass overall (no regressions)
- `ruff check` passes on all new files

## Notes

- Built-in drivers (`livespec/drivers/*.yaml`) only declare `detect` rules in this feature. Capability blocks will be filled by features 017–022.
- `livespec spec-driver --new <stack>` is the public scaffold entry point (FR-006).
- Patch coverage is fully local — no Codecov / Coveralls / SonarCloud dependency (AC-015).
- `/spec.test`, `/spec.feature`, and `/spec.implement` slash commands will call `validator.drivers.run_capability()` once feature 017+ wiring lands. The stable Python API is in place (FR-007).
