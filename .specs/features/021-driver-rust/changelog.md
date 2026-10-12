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

## 2026-05-07 — Plan: Approved

- **Type:** Plan Update
- **Plan modified:** Yes (created — Approved)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-010
- **Author:** spec.feature

## 2026-05-07 — Implementation: Rust driver shipped

- **Type:** Implementation
- **Spec modified:** No
- **Plan modified:** No
- **Code modified:**
  - `livespec/drivers/rust.yaml` (new — all 4 capabilities, no escape-hatch script)
  - `validator/drivers/rust_detector.py` (new — Cargo.toml parser via tomllib + cargo-mutants JSON parser)
  - `tests/unit/test_rust_detector.py` (new — 18 tests)
  - `tests/integration/test_driver_rust.py` (new — 10 tests)
- **AC impacted:** AC-001 through AC-010 — all Implemented
- **Tests:** 28 new (18 unit + 10 integration); full suite 784 passed, 28 skipped, 0 failed.
- **Author:** spec.feature

## 2026-10-12 — [Refactor]: Driver integration tests reduced to real behavior

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/integration/test_driver_rust.py, implementation.md
- **AC impacted:** None
- **Author:** Claude Code (test-suite cleanup, lot 1)
- Kept registry discovery and the 4-capability, script-free manifest; removed command-string pins and Cargo parsing duplicated by tests/unit/test_rust_detector.py.
