## 2026-05-06 — [Feature]: Cross-language test driver architecture implemented

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** validator/drivers/{__init__,schemas,loader,registry,runner,patch_coverage,degradation,scaffold,cli}.py, validator/cli.py, livespec/drivers/{python,typescript,swift,go,jvm}.yaml, tests/test_drivers.py
- **AC impacted:** AC-001 through AC-015 (all implemented)
- **Author:** spec.feature

## 2026-05-06 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-015 (all defined)
- **Author:** spec.specify

## 2026-10-12 — [Bugfix]: built-in driver scripts resolve beside their shipped manifest, custom ones stay project-relative

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** tests/test_builtin_driver_scripts.py, validator/drivers/runner.py
- **AC impacted:** FR-003
- **Author:** livespec bugfix record
- **Base revision:** HEAD
- **Regression tests:** tests/test_builtin_driver_scripts.py::test_builtin_script_capability_runs_shipped_script_in_any_project
- **RED receipt:** `.specs/.execution/43a0f6cd9da54d839e88f1b07b8c070e/receipt.json`
- **GREEN receipt:** `.specs/.execution/f6d981248e6644659579d7e7d317fe24/receipt.json`
<!-- bugfix:f6d981248e6644659579d7e7d317fe24 -->
