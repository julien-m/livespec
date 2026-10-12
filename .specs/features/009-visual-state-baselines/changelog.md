# Changelog — 009-visual-state-baselines

## 2026-10-12 — [Refactor]: Replace tautological visual-state tests with parsed-taxonomy assertions

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_visual_states.py
- **AC impacted:** AC-001, AC-013, AC-014
- **Author:** claude-code (test-suite cleanup, lot 5)
- **Details:** `test_visual_state_fields` and `test_missing_visual_states_table_returns_empty_list` now assert on traits parsed from the real taxonomy instead of on hand-built dataclasses. `test_all_five_traits_have_visual_states` now requires every documented visual trait to exist with at least 2 states; it absorbed the earlier per-trait loop, which passed silently when a trait was missing. Removed the taxonomy hash test because it exercised the VCS tool, not LiveSpec.

## 2026-04-17 — [Feature]: Spec created

- **Type:** Feature
- **Spec modified:** Yes (sections: all — initial creation)
- **Code modified:** (none)
- **AC impacted:** AC-001 through AC-015
- **Author:** spec.specify

---

## 2026-04-17 — [Plan]: Plan created

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** (none)
- **AC impacted:** AC-001 through AC-015 (all covered in implementation plan)
- **Author:** spec.plan

---

## 2026-04-17 — Test: AC coverage re-validated (run 2) + spec.md status fix

- **Type:** Spec Update
- **Spec modified:** Yes — `status: Draft` → `status: Implemented`
- **Code modified:** (none — 0 tests generated, existing coverage complete)
- **Coverage:** 3/3 Python-testable ACs covered (100%); 12 cmd-only ACs N/A
- **`--regenerate-missing` scan:** 0 features missing tests (EC-004); 10 features scanned
- **Suite:** 446 unit tests passing (+5 from 005.1), 14/14 integration (3a)
- **Report:** `checks/2026-04-17-test.md`
- **Author:** spec.test

---

## 2026-04-17 — Test: AC coverage validated

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** (none — 0 tests generated, existing coverage complete)
- **Coverage:** 3/3 Python-testable ACs covered (100%); 12 cmd-only ACs N/A
- **`--regenerate-missing` scan:** 0 features missing tests (EC-004)
- **Suite:** 441 unit tests passing; integration blocked (anyio not installed)
- **Report:** `checks/2026-04-17-test.md`
- **Author:** spec.test
