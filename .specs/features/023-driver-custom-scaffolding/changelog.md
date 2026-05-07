## 2026-05-07 — Implementation: scaffold, degradation, partial-driver helper

- **Type:** Implementation
- **Spec modified:** No
- **Code modified:** Yes
  - `livespec/drivers/templates/custom-driver-template.yaml` (new)
  - `validator/drivers/scaffold.py` (template-driven, sanitization, pre-fill)
  - `validator/drivers/degradation.py` (new structured format)
  - `validator/drivers/cli.py` (renamed `spec-driver` → `spec.driver`, next-steps output)
  - `validator/drivers/runner.py` (added `run_all_capabilities`)
  - `validator/drivers/__init__.py` (export new helper)
  - `validator/cli.py` (mount `spec.driver` + hidden alias)
  - `tests/test_drivers.py` (updated + 8 new tests)
- **AC impacted:** AC-001 through AC-010, EC-001/002, SC-004
- **Tests:** Targeted driver coverage added in `tests/test_drivers.py`; audit verification is tracked separately from this implementation note.
- **Author:** spec.implement

## 2026-05-06 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-010 (all defined)
- **Author:** spec.specify
