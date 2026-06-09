---
created: 2026-05-07
feature: 030-ui-runner-ios-watchos
status: Done
title: UI Runner iOS / watchOS — Implementation
updated: 2026-05-07
---

# Implementation: UI Runner iOS / watchOS (Feature 030)

## FR → File Mapping

| FR | Description | File | @spec Anchor |
|---|---|---|---|
| FR-001 | Author iOS runner manifest | `livespec/ui-runners/ios.yaml` | `# @spec FR-001: iOS/watchOS runner manifest` |
| FR-001 | Manifest runner Python module | `validator/ui_runner_xcuitest.py` | `# @spec FR-001: iOS/watchOS XCUITest manifest runner` |
| FR-001 | Surface detection in generate-surfaces.js | `scripts/generate-surfaces.js` | `// @spec FR-001: iOS/watchOS surface detection` |
| FR-002 | .xcresult bundle parsing + HEIC→PNG | `validator/ui_runner_xcuitest.py` | `# @spec FR-002: .xcresult parsing + HEIC→PNG` |
| FR-002 | Shell script xcresult extraction | `scripts/xcuitest-capture.sh` | `# @spec FR-002: .xcresult parsing + HEIC→PNG` |
| FR-003 | Simulator boot orchestration | `validator/ui_runner_xcuitest.py` | `# @spec FR-003: Simulator boot orchestration` |
| FR-003 | Shell script simulator boot | `scripts/xcuitest-capture.sh` | `# @spec FR-003: simulator boot orchestration` |
| FR-004 | watchOS destination filtering | `validator/ui_runner_xcuitest.py` | `# @spec FR-004: watchOS destination filtering` |
| FR-005 | launch_arguments injection | `validator/ui_runner_xcuitest.py` | `# @spec FR-005: launch_arguments injection` |
| FR-005 | Swift template launch args | `livespec/ui-runners/xcuitest-template/LSSampleUITests.swift` | `// @spec FR-005: launch_arguments injection` |
| FR-006 | Xcode license detection | `validator/ui_runner_xcuitest.py` | `# @spec FR-006: Xcode license detection` |
| FR-007 | Integration tests iOS | `tests/test_ui_runner_xcuitest.py` | pytest.mark.macos tests |
| FR-008 | Integration tests watchOS | `tests/test_ui_runner_xcuitest.py` | pytest.mark.macos tests |
| FR-009 | Developer documentation | `docs/ui-runners/xcuitest.md` | `<!-- @spec FR-009: developer documentation -->` |

## AC → Test Mapping

| AC | Description | Test File | Test Name |
|---|---|---|---|
| AC-001 | ios.yaml validates against UIRunnerSchema | `tests/test_xcuitest_manifest.py` | Multiple manifest tests |
| AC-002 | detect.files matches .xcodeproj/.xcworkspace/Package.swift | `tests/test_xcuitest_manifest.py` | `test_manifest_detect_files_*` |
| AC-003 | destinations array with default iOS Simulator | `tests/test_xcuitest_manifest.py` | `test_manifest_has_ios_simulator_destination` |
| AC-004 | capture_screenshot runs xcodebuild, parses .xcresult | `tests/test_ui_runner_xcuitest.py` | `test_xcresult_parsing_png` |
| AC-005 | run_flow surfaces test failures | `tests/test_ui_runner_xcuitest.py` | `test_non_macos_run_flow_returns_skipped` |
| AC-006 | compare_baseline reuses pixelmatch | `tests/test_ui_runner_xcuitest.py` | `test_compare_baseline_delegates_to_pixelmatch` |
| AC-007 | --platform=watchos filters destinations | `tests/test_ui_runner_xcuitest.py` | `test_filter_destinations_by_platform` |
| AC-008 | Simulator auto-boot | `tests/test_ui_runner_xcuitest.py` | `test_simulator_boot_from_shutdown` |
| AC-009 | Missing watchOS runtime → clear error | `tests/test_ui_runner_xcuitest.py` | filter + error message tests |
| AC-010 | launch_arguments per scenario | `tests/test_ui_runner_xcuitest.py` | `test_launch_arguments_propagated_to_env` |
| AC-011 | Coordinated execution | Via dispatch table in spec.test command |
| AC-012 | HEIC→PNG conversion | `tests/test_ui_runner_xcuitest.py` | `test_xcresult_heic_conversion` |
| AC-013 | Per-destination output subdirs | `validator/ui_runner_xcuitest.py` | `_parse_xcresult` destination_id param |
| AC-014 | Xcode license recovery hint | `tests/test_ui_runner_xcuitest.py` | `test_xcode_license_not_accepted_returns_error` |

## Files Created/Modified

### New files

| File | Description |
|---|---|
| `validator/ui_runner_xcuitest.py` | Python orchestrator (mirrors ui_runner_web.py shape) |
| `livespec/ui-runners/ios.yaml` | Runner manifest: detect rules, capabilities, destinations |
| `scripts/xcuitest-capture.sh` | Shell script for .xcresult capture (CI-invocable) |
| `livespec/ui-runners/xcuitest-template/LSSampleUITests.swift` | XCUITest Swift template for downstream projects |
| `livespec/ui-runners/xcuitest-template/README.md` | Setup guide for downstream project integration |
| `tests/test_ui_runner_xcuitest.py` | Unit tests (all mocked, run on any OS) |
| `tests/test_xcuitest_manifest.py` | YAML manifest schema validation tests |
| `tests/integration/test_surfaces_xcuitest.py` | Surface detection integration tests |
| `docs/ui-runners/xcuitest.md` | Developer documentation |

### Modified files

| File | Change |
|---|---|
| `scripts/generate-surfaces.js` | Added `hasXcodeProject()`, `hasAndroidProject()`, `hasMaestroFlows()` + iOS/Android detection in `detectSurfaces()` + `runMigrateNativeSurfaces()` (migration v12) + `platform` field in `surfaceToYamlLines()` |

## Graceful Degradation

| Scenario | Behavior |
|---|---|
| Non-macOS host | Returns `UICapabilityResult(success=False, error="iOS UI runner requires macOS — skipped on non-macOS hosts", metadata={"skipped": True})` |
| Xcode not installed | Returns error with App Store install link |
| Xcode license not accepted | Returns `"Xcode license not accepted. Run: sudo xcodebuild -license accept"` |
| watchOS runtime missing | Returns `"watchOS simulator runtime not installed. Install via Xcode > Settings > Platforms."` |
| Simulator not found | Returns error with `xcrun simctl list devices` hint |
| Corrupted .xcresult | Returns partial list of screenshots without crash (EC-002) |

---

*Implementation completed 2026-05-07*

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` | @spec(FR-001) | ✅ Implemented | 2026-06-08 |
| FR-002 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` | @spec(FR-002) | ✅ Implemented | 2026-06-08 |
| FR-003 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` | @spec(FR-003) | ✅ Implemented | 2026-06-08 |
| FR-004 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` | @spec(FR-004) | ✅ Implemented | 2026-06-08 |
| FR-005 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` | @spec(FR-005) | ✅ Implemented | 2026-06-08 |
| FR-006 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` | @spec(FR-006) | ✅ Implemented | 2026-06-08 |
| FR-007 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` | @spec(FR-007) | ✅ Implemented | 2026-06-08 |
| FR-008 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` | @spec(FR-008) | ✅ Implemented | 2026-06-08 |
| FR-009 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` | @spec(FR-009) | ✅ Implemented | 2026-06-08 |

## Acceptance Criteria

| AC | Test File | Status |
|---|---|---|
| AC-001 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-001) | ✅ Implemented |
| AC-002 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-002) | ✅ Implemented |
| AC-003 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-003) | ✅ Implemented |
| AC-004 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-004) | ✅ Implemented |
| AC-005 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-005) | ✅ Implemented |
| AC-006 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-006) | ✅ Implemented |
| AC-007 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-007) | ✅ Implemented |
| AC-008 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-008) | ✅ Implemented |
| AC-009 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-009) | ✅ Implemented |
| AC-010 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-010) | ✅ Implemented |
| AC-011 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-011) | ✅ Implemented |
| AC-012 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-012) | ✅ Implemented |
| AC-013 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-013) | ✅ Implemented |
| AC-014 | `.specs/features/030-ui-runner-ios-watchos/implementation.md` @spec(AC-014) | ✅ Implemented |
