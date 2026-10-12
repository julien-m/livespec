## 2026-10-12 — [Refactor]: Deterministic web-runner output-path tests

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_runner_path_contracts.py — the canonical `feature_slug`+`run_id` and legacy opt-in cases launched a real `npx playwright test` when npx was installed and only asserted that no guard fired. They now replace the Playwright subprocess, then assert success, the exact resolved PNG path, the command, cwd and `LIVESPEC_SCREENSHOT_PATH_<SCREEN>`.
- **AC impacted:** None
- **Author:** claude-code

## 2026-05-07 — [Plan]: Technical plan generated

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** None (plan.md created)
- **AC impacted:** None (pre-implementation)
- **Author:** spec.plan

## 2026-05-07 — [Implementation]: Core web runner implementation

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** livespec/ui-runners/web.yaml, validator/ui_runner_web.py, implementation.md
- **AC impacted:** AC-001, AC-003, AC-004, AC-005, AC-006
- **Author:** spec.feature

## 2026-05-06 — [Spec Update]: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-008 (all defined)
- **Author:** spec.specify

## 2026-10-12 — Refactor: web runner detection reads web.yaml

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** validator/runner_web_impl.py, validator/ui_runner_manifest.py (brace alternatives), tests/test_ui_runner_manifest_detect.py
- **AC impacted:** AC-002 (detection now driven by the manifest)
- **Author:** Claude Code (dead-code resolution)
- `load_web_runner_manifest` had no production caller. `detect()` now evaluates `package.json` AND `playwright*.config.{ts,js,mjs}` from web.yaml, matching EC-001; configs with other extensions (e.g. `.cjs`) no longer match, as the spec states.
