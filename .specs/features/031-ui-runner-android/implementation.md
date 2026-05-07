---
title: "Feature 031 — Implementation Reference"
status: "Done"
created: 2026-05-07
updated: 2026-05-07
---

# Implementation Reference: UI Runner Android (Maestro)

## FR → File Mapping

| FR | Description | File | Anchor |
|---|---|---|---|
| FR-001 | Android/Maestro runner manifest | `livespec/ui-runners/android.yaml` | Module-level comment |
| FR-001 | Manifest loading + detection | `validator/ui_runner_maestro.py` | `MaestroRunnerHandler.detect()`, `maestro_runner_manifest_path()`, `load_maestro_runner_manifest()`, `detect_maestro_runner()` |
| FR-001 | Android surface detection | `scripts/generate-surfaces.js` | `hasAndroidProject()`, `hasMaestroFlows()` |
| FR-002 | AVD orchestration | `validator/ui_runner_maestro.py` | `_check_android_sdk()`, `_check_maestro()`, `_list_avds()`, `_get_running_emulator()`, `_boot_avd()`, `_wait_for_boot()`, `_boot_avd_and_wait()` |
| FR-003 | Maestro screenshot extraction | `validator/ui_runner_maestro.py` | `_find_maestro_screenshots()`, `capture_screenshot()` |
| FR-004 | adb fallback screenshot | `validator/ui_runner_maestro.py` | `_capture_adb_screenshot()` |
| FR-004 | adb fallback screenshot script | `scripts/maestro-capture.sh` | Module-level comment |
| FR-005 | Device override + per-device baselines | `validator/ui_runner_maestro.py` | `_select_avd()`, `_resolve_baseline_path()` |
| FR-006 | Wear OS experimental warning | `validator/ui_runner_maestro.py` | `run_flow()`, `capture_screenshot()` (wearos branch) |
| FR-007 | Integration tests | `tests/integration/test_surfaces_maestro.py` | All test functions |
| FR-008 | Maestro flow conventions | `docs/ui-runners/maestro.md` | Full document |
| FR-008 | Flow templates | `livespec/ui-runners/maestro-template/` | `flows/home.yaml`, `flows/checkout.yaml`, `README.md` |

## AC → Test Mapping

| AC | Description | Test File | Test Function |
|---|---|---|---|
| AC-001 | `android.yaml` validates against UIRunnerSchema | `tests/test_maestro_manifest.py` | `test_manifest_is_valid_yaml`, `test_manifest_has_runner_section`, ... |
| AC-002 | detect.files matches build.gradle/build.gradle.kts | `tests/test_ui_runner_maestro.py` | `test_detect_build_gradle`, `test_detect_build_gradle_kts` |
| AC-003 | Android runner priority 50 > JVM driver | `tests/test_maestro_manifest.py` | `test_manifest_runner_priority_is_50` |
| AC-004 | run_flow invokes maestro test | `tests/test_ui_runner_maestro.py` | `test_run_flow_executes_maestro_test` |
| AC-005 | capture_screenshot handles tagged + fallback | `tests/test_ui_runner_maestro.py` | `test_find_maestro_screenshots_*`, `test_capture_adb_screenshot_*` |
| AC-006 | compare_baseline reuses pixelmatch | `tests/test_ui_runner_maestro.py` | `test_compare_baseline_delegates_to_pixelmatch` |
| AC-007 | Emulator auto-boot | `tests/test_ui_runner_maestro.py` | `test_boot_avd_starts_emulator`, `test_wait_for_boot_polls_boot_completed` |
| AC-008 | --device flag + missing AVD error | `tests/test_ui_runner_maestro.py` | `test_avd_not_found_lists_available_and_returns_error` |
| AC-009 | Maestro CLI absence emits curl hint | `tests/test_ui_runner_maestro.py` | `test_run_flow_no_maestro_returns_error` |
| AC-010 | Per-device baselines under device subdir | `tests/test_ui_runner_maestro.py` | `test_per_device_baseline_path_includes_device_name` |
| AC-011 | Failed flow does not stop others (configurable) | `tests/test_ui_runner_maestro.py` | `test_run_flow_continues_after_single_flow_failure`, `test_run_flow_fail_fast_stops_on_first_failure` |
| AC-012 | Coordinated /spec.test (JVM + Maestro) | Documented in `docs/ui-runners/maestro.md` | — |
| AC-013 | Wear OS experimental warning | `tests/test_ui_runner_maestro.py` | `test_wearos_platform_emits_experimental_warning` |

## @spec Anchor Summary

All FRs are anchored in production source files per the LiveSpec spec anchor convention:

- `validator/ui_runner_maestro.py` — Module-level anchors for FR-001 through FR-006
- Per-method anchors on `detect()`, `_check_android_sdk()`, `_check_maestro()`, AVD methods, screenshot methods, `run_flow()`, `capture_screenshot()`, `compare_baseline()`
- `livespec/ui-runners/android.yaml` — Module-level anchor for FR-001
- `scripts/maestro-capture.sh` — Module-level anchor for FR-004
- `scripts/generate-surfaces.js` — Inline anchors on `hasAndroidProject()`, `hasMaestroFlows()`, `detectSurfaces()` Android branch, `runMigrateNativeSurfaces()`
