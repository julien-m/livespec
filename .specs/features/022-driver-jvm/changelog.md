## 2026-05-06 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-011 (all defined)
- **Author:** spec.specify

## 2026-05-07 — Plan: Approved

- **Type:** Plan Update
- **Plan modified:** Yes (created — Approved)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-011
- **Author:** spec.feature

## 2026-05-07 — Implementation: JVM driver shipped

- **Type:** Implementation
- **Spec modified:** No
- **Plan modified:** No
- **Code modified:**
  - `livespec/drivers/jvm.yaml` (replaced Feature 016 stub — all 4 capabilities, script escape hatches)
  - `livespec/drivers/scripts/jvm-coverage-gate.sh` (new — Gradle/Maven dispatch + JaCoCo gate)
  - `livespec/drivers/scripts/jvm-snapshots.sh` (new — kotest-snapshot / approvaltests detection)
  - `livespec/drivers/scripts/jvm-properties.sh` (new — kotest-property / jqwik detection)
  - `livespec/drivers/scripts/jvm-mutation.sh` (new — pitest dispatch + report locator)
  - `validator/drivers/jvm_detector.py` (new — Gradle DSL token parser, Maven POM regex parser, pitest XML parser)
  - `tests/unit/test_jvm_detector.py` (new — 24 tests)
  - `tests/unit/test_jvm_coverage_gate.py` (new — 8 tests)
  - `tests/unit/test_jvm_mutation_script.py` (new — 12 tests covering mutation/snapshots/properties scripts)
  - `tests/integration/test_driver_jvm.py` (new — 15 tests)
- **AC impacted:** AC-001 through AC-011 — all Implemented
- **Tests:** 59 new (44 unit + 15 integration); full suite 843 passed, 28 skipped, 0 failed.
- **Author:** spec.feature
