---
created: 2026-04-13
feature: 002-layer-3-cli-surface
plan_ref: plan.md
spec_ref: spec.md
title: Layer 3 CLI Surface
type: implementation
updated: 2026-04-13
---

# Implementation: Layer 3 CLI Surface

## Files Changed

| File | Action | Description |
|---|---|---|
| `validator/exceptions.py` | Modified | Added `SdkDependencyError` and `SdkTestRunError` domain exceptions |
| `validator/sdk_test_runner.py` | Created | `SdkTestRunner` service — subprocess wrapper for Level 3b pytest invocation |
| `validator/cli.py` | Modified | Added `--sdk-isolated` flag, `_resolve_feature_slug()`, `_output_sdk_result_json()` |
| `tests/test_sdk_test_runner.py` | Created | Unit tests for SdkTestRunner with mocked subprocess |
| `tests/test_cli.py` | Modified | CLI integration tests for `--sdk-isolated` flag |

## Spec Anchor Mappings

| Source | Anchor | Location |
|---|---|---|
| @spec FR-001 | `spec.md#fr-001` | `validator/cli.py` — `--sdk-isolated` flag routing block |
| @spec FR-002 | `spec.md#fr-002` | `validator/cli.py` — SDK dependency check, `validator/exceptions.py` — `SdkDependencyError` |
| @spec FR-003 | `spec.md#fr-003` | `validator/cli.py` — ANTHROPIC_API_KEY warning |
| @spec FR-004 | `spec.md#fr-004` | `validator/sdk_test_runner.py` — `SdkTestRunner.run()`, `validator/exceptions.py` — `SdkTestRunError` |
| @spec FR-005 | `spec.md#fr-005` | `validator/cli.py` — exit code mapping (exit 5 → 0, non-zero → 1) |
| @spec FR-006 | `spec.md#fr-006` | `validator/cli.py:92` — `_resolve_feature_slug()`, `validator/sdk_test_runner.py:97` — `-k` filter append |
| @spec FR-007 | `spec.md#fr-007` | `validator/sdk_test_runner.py:102` — `_build_subprocess_env()` budget forwarding |
| @spec FR-008 | `spec.md#fr-008` | `validator/cli.py` — `_output_sdk_result_json()`, `validator/sdk_test_runner.py:19` — `SdkTestResult` schema |
| @spec FR-009 | `spec.md#fr-009` | `validator/sdk_test_runner.py:166` — stderr streaming loop in `run()` |

## AC Coverage

| AC | Status | Test |
|---|---|---|
| AC-001 | Covered | `test_sdk_isolated_flag_calls_runner` |
| AC-002 | Covered | `test_sdk_isolated_missing_sdk_exits_1` |
| AC-003 | Covered | `test_sdk_isolated_no_api_key_warns` |
| AC-004 | Covered | `test_sdk_isolated_budget_exit_2_maps_to_1`, `test_sdk_isolated_flag_calls_runner` |
| AC-005 | Covered | `test_sdk_isolated_feature_path_adds_k_filter` |
| AC-006 | Covered | `test_sdk_isolated_exit_5_maps_to_0` |
| AC-007 | Covered | `test_budget_forwarded_to_env` |
| AC-008 | Covered | `test_sdk_isolated_format_json` |
| AC-009 | Covered | `SdkTestRunner.run()` streams to stderr via Popen |
| AC-010 | Covered | `test_sdk_isolated_help_text_contains_flag` |

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `.specs/features/002-layer-3-cli-surface/implementation.md` | @spec(FR-001) | ✅ Implemented | 2026-06-08 |
| FR-002 | `.specs/features/002-layer-3-cli-surface/implementation.md` | @spec(FR-002) | ✅ Implemented | 2026-06-08 |
| FR-003 | `.specs/features/002-layer-3-cli-surface/implementation.md` | @spec(FR-003) | ✅ Implemented | 2026-06-08 |
| FR-004 | `.specs/features/002-layer-3-cli-surface/implementation.md` | @spec(FR-004) | ✅ Implemented | 2026-06-08 |
| FR-005 | `.specs/features/002-layer-3-cli-surface/implementation.md` | @spec(FR-005) | ✅ Implemented | 2026-06-08 |
| FR-006 | `.specs/features/002-layer-3-cli-surface/implementation.md` | @spec(FR-006) | ✅ Implemented | 2026-06-08 |
| FR-007 | `.specs/features/002-layer-3-cli-surface/implementation.md` | @spec(FR-007) | ✅ Implemented | 2026-06-08 |
| FR-008 | `.specs/features/002-layer-3-cli-surface/implementation.md` | @spec(FR-008) | ✅ Implemented | 2026-06-08 |
| FR-009 | `.specs/features/002-layer-3-cli-surface/implementation.md` | @spec(FR-009) | ✅ Implemented | 2026-06-08 |
