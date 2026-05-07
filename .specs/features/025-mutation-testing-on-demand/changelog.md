## 2026-05-07 — Implement: feature shipped

- **Type:** Implementation
- **Spec modified:** No
- **Code modified:** Yes
  - `validator/drivers/mutation_report.py` (new) — orchestration, dataclasses, normalisers, writer.
  - `validator/drivers/__init__.py` — re-export public surface.
  - `tests/test_mutation_report.py` (new) — 15 unit tests.
  - `commands/test.md` — `--mutation` flag documentation.
- **AC impacted:** AC-001..AC-007 + EC-001..EC-003 + SC-001..SC-003 covered.
- **Tests:** 15 new, 874 total passed, 0 failed, 28 skipped.
- **Author:** spec.feature

## 2026-05-06 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-007 (all defined)
- **Author:** spec.specify
