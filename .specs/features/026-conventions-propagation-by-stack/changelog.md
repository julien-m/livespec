## 2026-05-06 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-008 (all defined)
- **Author:** spec.specify

## 2026-05-07 — Implemented

- **Type:** Implementation
- **Spec modified:** No
- **Code modified:**
  - `validator/drivers/test_config.py` (new) — `GeneratedFile`, per-stack generators, `generate_test_config`, `generate_ci_workflow`, `update_conventions_testing_domain`, `materialize_files`, `pick_primary_driver`.
  - `validator/drivers/test_config_cli.py` (new) — `livespec init test-config` Typer app.
  - `validator/cli.py` — wires `init_app`.
  - `validator/drivers/__init__.py` — exports new public surface.
  - `tests/test_drivers_test_config.py` (new) — 43 tests (8 ACs, 4 ECs, CLI integration).
- **AC impacted:** AC-001 through AC-008 (all covered)
- **Tests:** 917 passed (+43 new vs 874 baseline), 28 skipped, 0 failed
- **Author:** spec.feature
