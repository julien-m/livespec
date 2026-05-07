# Implementation: Conventions Propagation by Stack

- **Feature:** 026-conventions-propagation-by-stack
- **Date:** 2026-05-07
- **Status:** Done

---

## Summary

Implemented per-stack test config propagation as a pure-Python module
(`validator/drivers/test_config.py`) plus a Typer subcommand
(`livespec init test-config`) consumed by `/spec.init` Phase C and
`/spec.refresh-conventions`.

## Files

| File | Action | Purpose |
|------|--------|---------|
| `validator/drivers/test_config.py` | Created | Core module: `GeneratedFile`, per-stack generators, `generate_test_config`, `generate_ci_workflow`, `update_conventions_testing_domain`, `materialize_files`, `pick_primary_driver`. |
| `validator/drivers/test_config_cli.py` | Created | `livespec init test-config` Typer app. |
| `validator/cli.py` | Modified | Registered `init_app` under the root Typer. |
| `validator/drivers/__init__.py` | Modified | Re-exports the new public API. |
| `tests/test_drivers_test_config.py` | Created | 43 unit + CLI integration tests. |

## Acceptance Criteria coverage

| AC | Test |
|----|------|
| AC-001 | `test_stack_generators_emit_threshold`, `test_init_test_config_python_project` |
| AC-002 | `test_init_test_config_unsupported_stack_skips` |
| AC-003 | `test_generate_ci_workflow_uses_livespec_spec_test`, `test_generate_ci_workflow_includes_install_step_before_test_step` |
| AC-004 | `test_threshold_propagates_to_python_config`, `test_init_test_config_threshold_flag_propagates` |
| AC-005 | `test_init_test_config_updates_conventions_index`, `test_update_conventions_creates_block_when_absent` |
| AC-006 | `test_init_test_config_refresh_only_skips_writes`, `test_update_conventions_replaces_existing_block` |
| AC-007 | `test_init_test_config_python_project` (asserts file paths in output) |
| AC-008 | `test_materialize_patches_existing_pyproject`, `test_materialize_skips_existing_ci_workflow` |
| EC-001 | `test_init_test_config_existing_vitest_is_patched` |
| EC-002 | `test_materialize_skips_existing_ci_workflow` |
| EC-003 | `test_pick_primary_driver_prefers_highest_match_count` |
| EC-004 | `test_materialize_creates_ci_workflow_in_missing_directory` |
| SC-002 | `test_generate_ci_workflow_yaml_is_valid` |

## Verification

- `pytest tests/` — 917 passed, 28 skipped (+15 from 902 baseline)
- `ruff check validator/` — passes
- `pyright validator/` — 117 errors (1 fewer than 118 baseline; new files clean)

## Notes

- `materialize_files` honors a `force=True` override so
  `/spec.refresh-conventions` can rewrite the CI workflow when the stack
  changes; default behavior is `skip_if_exists` (EC-002).
- Conventions index uses HTML markers (`<!-- livespec:testing:begin -->`)
  for idempotent rewrites — survives manual edits around the block.
- `pick_primary_driver` resolves polyglot projects deterministically by
  match count; ties fall back to the input order from `DriverRegistry`
  (custom drivers > built-ins, alphabetical within each tier).
