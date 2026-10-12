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
- **AC impacted:** AC-001 through AC-010 (all defined)
- **Author:** spec.specify

## 2026-05-07 — Plan + Implementation: Swift driver shipped

- **Type:** Plan + Implementation
- **Spec modified:** No
- **Code modified:**
  - `livespec/drivers/swift.yaml` (replaced 016 stub with 4-capability manifest, `script:` escape hatch for coverage)
  - `livespec/drivers/scripts/swift-coverage-gate.sh` (new — coverage threshold gate)
  - `validator/drivers/swift_detector.py` (new — Package.swift parser + Xcode fallback)
  - `tests/unit/test_swift_detector.py` (new — 11 tests)
  - `tests/unit/test_swift_coverage_gate.py` (new — 9 tests)
  - `tests/integration/test_driver_swift.py` (new — 11 tests)
- **AC impacted:** AC-001 through AC-010 (all covered)
- **Verification:** `pytest tests/` — 723 passed, 28 skipped. `pyright validator/drivers/` — 0 errors. `ruff check` — passes.
- **Author:** spec.feature (auto)

## 2026-10-12 — [Refactor]: Driver integration tests reduced to real behavior

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/integration/test_driver_swift.py, implementation.md
- **AC impacted:** None
- **Author:** Claude Code (test-suite cleanup, lot 1)
- Kept registry discovery, Xcode-only non-match, capability set and shipped gate script (now derived from the manifest); removed YAML value pins and SwiftPM parsing duplicated by tests/unit/test_swift_detector.py.
