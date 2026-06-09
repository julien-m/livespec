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
- **AC impacted:** AC-001 through AC-012 (all defined)
- **Author:** spec.specify

## 2026-05-07 — Plan + Implementation: TS/JS driver shipped

- **Type:** Plan + Implementation
- **Spec modified:** No
- **Code modified:**
  - `livespec/drivers/typescript.yaml` (replaced 016 stub with 4-capability manifest)
  - `validator/drivers/typescript_detector.py` (new)
  - `validator/drivers/stryker_parser.py` (new)
  - `tests/unit/test_typescript_detector.py` (new — 16 tests)
  - `tests/unit/test_stryker_parser.py` (new — 11 tests)
  - `tests/integration/test_driver_typescript.py` (new — 11 tests)
- **AC impacted:** AC-001 through AC-012 (all covered)
- **Verification:** `ruff check .` passes. `mypy .` currently reports pre-existing repository issues outside the Feature 018 file set.
- **Author:** spec.feature (auto)
