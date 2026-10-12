## 2026-10-12 — [Feature]: Additive `test_selection` field on driver capabilities

- **Type:** Feature (additive, backward compatible)
- **Spec modified:** No
- **Code modified:** `validator/drivers/schemas.py` (`DriverCapability.test_selection: Literal["append"] | None = None`), `validator/drivers/runner.py` (`run_capability(test_paths=)` appends selected paths only on `append`, otherwise raises `DriverTestSelectionError`), `livespec/drivers/python.yaml`, `livespec/drivers/templates/custom-driver-template.yaml`
- **AC impacted:** None (existing manifests load unchanged); consumer: feature 035 AC-002
- **Author:** spec-fix 035 (Claude Opus 5.5)

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
