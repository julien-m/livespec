## 2026-06-08 — [Spec Update]: Normalize changelog format

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec.doctor

---

## 2026-05-06 — Feature: Complete Python driver implementation

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** livespec/drivers/python.yaml, validator/drivers/python_detector.py, validator/drivers/syrupy_detector.py, validator/drivers/mutmut_parser.py, tests/unit/test_python_detector.py, tests/unit/test_mutmut_parser.py, tests/integration/test_driver_python.py
- **AC impacted:** AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-007, AC-008, AC-009, AC-010, AC-011, AC-012
- **Author:** claude-code

## 2026-05-06 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-012 (all defined)
- **Author:** spec.specify

## 2026-10-12 — [Refactor]: Driver integration tests reduced to real behavior

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/integration/test_driver_python.py, tests/integration/helpers/driver_manifests.py (new), implementation.md
- **AC impacted:** None
- **Author:** Claude Code (test-suite cleanup, lot 1)
- Kept registry discovery and schema-validated capability set; removed YAML value pins (threshold, report path, command presence).

## 2026-10-12 — Bugfix: wire module detection, retire syrupy probes

- **Type:** Bugfix
- **Spec modified:** Yes (FR-003, FR-004, AC-005, AC-007 marked Removed)
- **Code modified:** validator/drivers/placeholders.py (new), validator/drivers/runner.py, validator/drivers/syrupy_detector.py (deleted), tests/test_driver_placeholders.py (new), tests/integration/test_driver_python_coverage_flow.py (new)
- **AC impacted:** AC-002, AC-004 (now enforced in the real flow), AC-005, AC-007 (removed)
- **Author:** Claude Code (dead-code resolution)
- `detect_python_module` had no production caller and the coverage command reached pytest with literal `{module}`/`{report_path}`/`{threshold}` (exit 3). The runner now resolves these placeholders, proved by a `livespec test` level-3A test that fails without the fix.
- `syrupy_detector` (FR-003/FR-004) was never called: no production command runs the snapshots capability, and the probe checked LiveSpec's interpreter instead of the project's environment. Removed rather than wired.
