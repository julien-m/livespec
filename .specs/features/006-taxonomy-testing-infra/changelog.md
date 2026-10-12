## 2026-06-08 — [Spec Update]: Normalize changelog format

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec.doctor

---

### 2026-04-15 — Plan: Technical plan generated

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** None (plan.md created)
- **AC impacted:** None (pre-implementation)
- **Author:** spec.plan

---

### 2026-04-15 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-015 (all defined)
- **Author:** spec.specify

## 2026-10-12 — Spec Update: retire deduplicate_tests and a tautological test

- **Type:** Spec Update
- **Spec modified:** Yes (FR-005, FR-006, AC-009, AC-010, AC-011 marked Removed; Story 2 annotated; AC-012/FR-008 annotated)
- **Code modified:** validator/taxonomy.py (MergedTest, deduplicate_tests and private overlap helpers deleted), tests/test_taxonomy_detection.py
- **AC impacted:** AC-009, AC-010, AC-011 (removed), AC-012 (test count annotated)
- **Author:** Claude Code (dead-code resolution)
- `deduplicate_tests` had no caller in validator/, scripts/ or any skill. Wiring it into `/spec-implement` was rejected: a single shared content word is enough to merge two tests, so false merges would silently drop dedicated AC tests. EC-002/EC-004 remain semantic taxonomy rules applied by `/spec-implement`.
- `test_graceful_degradation_pattern` only exercised its own try/except around `detect_traits`; it proved nothing about LiveSpec. Fail-fast loading stays covered by the AC-003/AC-008 tests.
