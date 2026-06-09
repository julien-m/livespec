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

## 2026-05-07 — Done

- Added `evaluate_patch_gate(coverage, threshold)` to `validator/drivers/patch_coverage.py` (AC-007, FR-004).
- Added `summarise_patch_coverage(report, *, threshold=None)` formatter for `/spec.test` summaries (AC-009, FR-005).
- Re-exported both helpers from `validator.drivers`.
- Added 7 unit tests in `tests/test_drivers.py` covering gate logic and summary rendering (FR-006).
- Documented the module path deviation (`validator/drivers/patch_coverage.py` vs spec's `livespec/coverage/patch.py`) in `implementation.md`.
