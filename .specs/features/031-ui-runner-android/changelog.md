## 2026-10-12 — [Refactor]: Android manifest tests consolidated around the production loader

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_maestro_manifest.py, implementation.md (AC-001 row)
- **AC impacted:** AC-001, AC-003
- **Author:** claude-code (test-suite cleanup lot 3)

37 one-line key/value checks became one structural test loaded through `load_maestro_runner_manifest`, the AC-003 priority test, and a new check that every declared detect file/dir is honoured by `MaestroRunnerHandler.detect()`.

## 2026-10-12 — [Refactor]: Replace vacuous capture test and remove unconditional-skip stubs

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_ui_runner_maestro.py
- **AC impacted:** AC-005 (tagged/fallback capture, existing tests unchanged)
- **Author:** claude-code (test-suite cleanup, lot 5)
- **Details:** `test_capture_screenshot_uses_avd_subdirectory` passed vacuously: with no output context the runner refuses capture, so its conditional assertion never ran. It is replaced by two tests. One checks that both flows are captured into `.specs/features/<slug>/run/<id>/android/`. The other checks the explicit `missing_output_context` refusal. The two always-skipped `pytest.mark.android` stubs are removed.

## 2026-05-06 — [Spec Update]: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-013 (all defined)
- **Author:** spec.specify

## 2026-10-12 — [Refactor]: Surface generator tests assert parsed output

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/integration/test_surfaces_maestro.py, tests/integration/helpers/surfaces_script.py (new)
- **AC impacted:** None
- **Author:** Claude Code (test-suite cleanup, lot 1)
- Tests parse the generated surfaces (runner, platform, path, testDir) instead of searching stdout for 'maestro'; explicit skip when `node` is absent.

## 2026-10-12 — Refactor: runner detection reads the android.yaml manifest

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** validator/ui_runner_manifest.py (new), validator/runner_xcuitest_impl.py, validator/runner_maestro_impl.py, tests/test_ui_runner_manifest_detect.py (new)
- **AC impacted:** AC-002 (now enforced through the production detection path)
- **Author:** Claude Code (dead-code resolution)
- `load_maestro_runner_manifest` had no production caller: the handler hardcoded the same markers that `android.yaml` declares. `detect()` now evaluates the manifest `detect:` block (files globs, dirs, OR/AND logic), so the manifest is the single source of truth; a dispatcher-level test fails without the wiring. Behaviour on the built-in manifests is unchanged.
