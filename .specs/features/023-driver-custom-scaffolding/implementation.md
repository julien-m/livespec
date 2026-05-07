# Implementation — 023 Driver Custom Scaffolding & Graceful Degradation

- **Date:** 2026-05-07
- **Branch:** feature/023-driver-custom-scaffolding
- **Status:** Implemented

## Summary

Closed the gaps left by feature 016 around the custom-driver UX:
1. CLI subcommand renamed from `spec-driver` to `spec.driver` (with hidden alias for back-compat).
2. YAML template promoted to embedded resource at `livespec/drivers/templates/custom-driver-template.yaml`.
3. `detect.files` pre-filled when the stack is recognized (elixir, ruby, php, python, node, typescript, swift, go, rust, jvm).
4. Inline documentation for each capability (`command:` vs `script:`, `report_path`, threshold, patch_threshold).
5. Stack name sanitization (hyphens / dots) and automatic `.specs/drivers/` creation.
6. Degradation message reformatted with `⚠ Stack not supported` prefix, explicit "No driver registered for this stack", and integration link.
7. Public helper `run_all_capabilities` for partial-driver orchestration (returns `None` for non-implemented capabilities instead of raising).
8. CLI prints next-steps after scaffold (edit, verify with `spec.check`, integration doc).

## Files

| File | Change |
|---|---|
| `livespec/drivers/templates/custom-driver-template.yaml` | New — embedded YAML template with inline docs (FR-002, AC-001, AC-005, Story 3). |
| `validator/drivers/scaffold.py` | Loads template via Path resolution, pre-fills detect.files, sanitizes stack names (FR-001, AC-005, EC-001, EC-002). |
| `validator/drivers/degradation.py` | New structured message format with ⚠ prefix and integration link (FR-003, FR-004, AC-006, AC-008). |
| `validator/drivers/cli.py` | Typer name `spec.driver`, richer next-steps output, EC-004 warning when `.specs/` is missing (FR-001, AC-010, EC-004). |
| `validator/drivers/runner.py` | New `run_all_capabilities` helper (FR-005, AC-009). |
| `validator/drivers/__init__.py` | Export `run_all_capabilities`. |
| `validator/cli.py` | Mount driver_app under `spec.driver` + hidden `spec-driver` back-compat alias. |
| `tests/test_drivers.py` | Updated existing tests to use `spec.driver`; added 8 new tests covering AC-002, AC-005, AC-006 SC-004, AC-009, AC-010, EC-001, EC-002. |

## AC traceability

| AC | Test |
|---|---|
| AC-001 | `test_scaffold_creates_yaml` |
| AC-002 | `test_scaffold_template_passes_schema_validation`, `test_scaffold_unknown_stack_still_validates` |
| AC-003 | `test_scaffold_refuses_overwrite`, `test_cli_spec_driver_new_refuses_overwrite` |
| AC-004 | `test_scaffold_force_overwrites`, `test_cli_spec_driver_force` |
| AC-005 | `test_scaffold_creates_yaml` (mix.exs assertion) |
| AC-006 | `test_format_degradation_message_elixir` |
| AC-007 | Existing engine integration: degradation is informational; helper returns text only. |
| AC-008 | `test_format_degradation_message_no_signals` |
| AC-009 | `test_run_all_capabilities_partial_driver` |
| AC-010 | `test_cli_spec_driver_new_creates_file` (Next steps assertion) |
| EC-001 | `test_scaffold_sanitizes_hyphenated_name` |
| EC-002 | `test_scaffold_creates_specs_drivers_dir` |
| SC-004 | `test_format_degradation_message_ruby_inference`, `test_format_degradation_message_php_inference` |

## Test results

- `pytest tests/`: 852 passed, 28 skipped (44 driver tests).
- `pyright validator/drivers/ validator/cli.py`: 0 errors, 0 warnings.
- `ruff check validator/`: passes.

## Notes

- YAML aliases gotcha: glob patterns starting with `*` (e.g. `*.ex`) must be quoted in YAML to avoid being parsed as alias references. The `_detect_files_yaml` renderer quotes every entry.
- Capability sections in the template remain **commented out** so an as-shipped scaffold passes schema validation (`DriverCapability` requires either `command:` or `script:` non-None when present). Inline documentation is preserved for each section.

---

*LiveSpec Implementation — 2026-05-07*
