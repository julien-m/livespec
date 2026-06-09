## 2026-06-08 — [Spec Update]: Normalize changelog format

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec.doctor

---

## 2026-05-06 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-009 (all defined)
- **Author:** spec.specify

## 2026-05-07 — Plan: Approved

- **Type:** Plan Update
- **Plan modified:** Yes (created — Approved)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-009
- **Author:** spec.feature

## 2026-05-07 — Implementation: Go driver shipped

- **Type:** Implementation
- **Spec modified:** No
- **Plan modified:** No
- **Code modified:**
  - `livespec/drivers/go.yaml` (3 capabilities; mutation intentionally absent)
  - `livespec/drivers/scripts/go-coverage-gate.sh` (new — escape-hatch gate + inline lcov conversion)
  - `validator/drivers/go_detector.py` (new — go.mod module + require parser)
  - `tests/unit/test_go_detector.py` (new — 14 tests)
  - `tests/unit/test_go_coverage_gate.py` (new — 9 tests)
  - `tests/integration/test_driver_go.py` (new — 10 tests)
- **AC impacted:** AC-001 through AC-009 — all Implemented
- **Tests:** Targeted Go driver unit and integration coverage added; verification status is recorded in the implementation report for this feature.
- **Author:** spec.feature
