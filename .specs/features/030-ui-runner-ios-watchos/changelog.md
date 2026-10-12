## 2026-10-12 — [Refactor]: Remove unconditional-skip integration stubs; FR-007/FR-008 marked Missing

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_ui_runner_xcuitest.py, implementation.md
- **AC impacted:** None (FR-007, FR-008 status corrected)
- **Author:** claude-code (test-suite cleanup, lot 5)
- **Details:** `test_real_simulator_boot_integration` and `test_real_xcresult_extraction_integration` always called `pytest.skip()` and never asserted anything, yet implementation.md mapped FR-007/FR-008 to them as Implemented. The stubs are removed and both FRs now show Missing until a real macOS fixture test exists.

## 2026-05-06 — [Spec Update]: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-014 (all defined)
- **Author:** spec.specify

## 2026-10-12 — [Refactor]: Surface generator tests assert parsed output

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/integration/test_surfaces_xcuitest.py, tests/integration/helpers/surfaces_script.py (new)
- **AC impacted:** None
- **Author:** Claude Code (test-suite cleanup, lot 1)
- Tests parse the YAML that generate-surfaces.js would write instead of searching stdout for 'xcuitest'; three Android cases duplicated from test_surfaces_maestro.py removed; explicit skip when `node` is absent.

## 2026-10-12 — Refactor: runner detection reads the ios.yaml manifest

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** validator/ui_runner_manifest.py (new), validator/runner_xcuitest_impl.py, validator/runner_maestro_impl.py, tests/test_ui_runner_manifest_detect.py (new)
- **AC impacted:** AC-002 (now enforced through the production detection path)
- **Author:** Claude Code (dead-code resolution)
- `load_xcuitest_runner_manifest` had no production caller: the handler hardcoded the same markers that `ios.yaml` declares. `detect()` now evaluates the manifest `detect:` block (files globs, dirs, OR/AND logic), so the manifest is the single source of truth; a dispatcher-level test fails without the wiring. Behaviour on the built-in manifests is unchanged.

## 2026-10-12 — Feature: per-project ios.yaml configuration

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** validator/ios_project_config.py (new), validator/ios_runner_core.py, validator/dispatcher_core.py, tests/test_ios_project_config.py (new), docs/ui-runners/xcuitest.md
- **AC impacted:** AC-010 (scenario launch arguments now come from the project config)
- **Author:** Claude Code (dead-code resolution, user decision)
- The documented project `livespec/ui-runners/ios.yaml` was never read. `capture_screenshot` and `run_flow` now resolve `test_scheme` and `launch_arguments` with explicit values (runnerConfig / direct arguments) > project config (scenario from `runnerConfig.scenario`, else `default`, else first; then top-level `test_scheme`) > scheme autodetection. Malformed configs and unknown scenarios fail with `Invalid iOS runner config`. The doc no longer advertises the unsupported `timeout_seconds` key.
