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
