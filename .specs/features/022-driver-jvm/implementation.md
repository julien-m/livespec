---
type: implementation
title: Driver JVM (Java + Kotlin) — Built-in Test Orchestration Driver
feature: 022-driver-jvm
spec_ref: spec.md
plan_ref: plan.md
created: 2026-05-07
updated: 2026-05-07
status: Implemented
---

# Implementation — Driver JVM (Java + Kotlin)

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `livespec/drivers/jvm.yaml` | `@spec FR-001: JVM driver YAML — .specs/features/022-driver-jvm/spec.md#fr-001` | Implemented | 2026-05-07 |
| FR-002 | `validator/drivers/jvm_detector.py::detect_build_tool` | `@spec FR-002: build tool detection (Gradle priority)` | Implemented | 2026-05-07 |
| FR-003 | `validator/drivers/jvm_detector.py::parse_gradle_build`, `parse_maven_pom` | `@spec FR-003: build.gradle / pom.xml plugin and dependency parser` | Implemented | 2026-05-07 |
| FR-004 | `validator/drivers/jvm_detector.py::parse_pitest_xml` | `@spec FR-004: pitest XML parser` | Implemented | 2026-05-07 |
| FR-005 | `tests/integration/test_driver_jvm.py` | `@spec FR-005: integration tests for the JVM driver` | Implemented | 2026-05-07 |
| FR-006 | `tests/unit/test_jvm_detector.py`, `tests/unit/test_jvm_coverage_gate.py`, `tests/unit/test_jvm_mutation_script.py` | `@spec FR-006: unit tests for parsers + scripts` | Implemented | 2026-05-07 |

## Files Created

| File | Purpose |
|---|---|
| `livespec/drivers/scripts/jvm-coverage-gate.sh` | Escape-hatch script: detects Gradle vs Maven (Gradle priority per AC-010), probes for JaCoCo plugin presence, dispatches `./gradlew test jacocoTestReport jacocoTestCoverageVerification` or `mvn verify`, locates lcov.info at the standard path, exits 0 with a setup-guide message when JaCoCo is absent (AC-004). |
| `livespec/drivers/scripts/jvm-snapshots.sh` | Detects kotest-snapshot or approvaltests in the build file; runs `./gradlew test` / `mvn test` if present; emits the documented skip-message and exits 0 if neither library is configured (AC-005). |
| `livespec/drivers/scripts/jvm-properties.sh` | Detects kotest-property or jqwik in the build file; same dispatch + skip-message contract (AC-006). |
| `livespec/drivers/scripts/jvm-mutation.sh` | Detects pitest plugin (Gradle or Maven), runs `./gradlew pitest` or `mvn org.pitest:pitest-maven:mutationCoverage`, locates `mutations.xml` (Gradle path or globbed Maven timestamped path per EC-004); emits setup hint + exits 0 when pitest is absent (AC-007). |
| `validator/drivers/jvm_detector.py` | Pure-Python JVM build file parsers + pitest XML parser. Gradle DSL parsed via permissive token regex (Gradle is Turing-complete; tokens are consultative); Maven POM parsed via shallow `<artifactId>` regex (avoids the stdlib XML backend, which depends on pyexpat and is broken on some Python distributions); pitest XML parsed via shallow `<mutation status="...">` regex returning KILLED/SURVIVED/TIMED_OUT/NO_COVERAGE/MEMORY_ERROR/RUN_ERROR counts. |
| `tests/unit/test_jvm_detector.py` | 24 unit tests covering build tool detection (Gradle priority, Kotlin DSL, Maven-only, empty), Gradle Groovy/Kotlin DSL parsing, Maven POM artifactId extraction, comment stripping, malformed/unreadable input degradation, substring `has_jvm_dependency` lookups (case-insensitive), and the pitest XML parser (counts, zero-fill, mixed case, malformed, empty, unknown statuses, missing attributes). |
| `tests/unit/test_jvm_coverage_gate.py` | 8 bash-script unit tests for `jvm-coverage-gate.sh`: no build file, JaCoCo absent (Gradle/Maven), JaCoCo present with/without lcov, Gradle-priority-over-Maven dispatch, executable bit. |
| `tests/unit/test_jvm_mutation_script.py` | 12 bash-script unit tests covering all three sibling scripts (`jvm-mutation.sh`, `jvm-snapshots.sh`, `jvm-properties.sh`): probe-only paths, skip-with-hint paths, library detection on Gradle Groovy/Kotlin DSL/Maven. |
| `tests/integration/test_driver_jvm.py` | 15 integration tests covering registry detection on each of the three build files, schema validation, all-4-capability metadata, script-escape-hatch wiring, dependency detection on Gradle Groovy / Gradle Kotlin / Maven fixtures, and Gradle-priority detection. |

## Files Modified

| File | Change |
|---|---|
| `livespec/drivers/jvm.yaml` | Replaced Feature 016 stub with full 4-capability manifest. All capabilities use `script:` escape hatches (Gradle vs Maven dispatch happens before any concrete tool invocation, so no native `command:` is sufficient). |

## Acceptance Criteria Mapping

| AC | Test Case(s) | Status |
|---|---|---|
| AC-001 | `test_registry_loads_jvm_driver_on_gradle`, `test_registry_loads_jvm_driver_on_gradle_kts`, `test_registry_loads_jvm_driver_on_maven`, `test_jvm_driver_detect_files` | Implemented |
| AC-002 | `test_coverage_capability_uses_script_escape_hatch`, `test_gate_jacoco_present_with_lcov_passes` (gate runs build tool only when not in probe-only mode; integration test asserts script wiring) | Implemented |
| AC-003 | `test_coverage_capability_uses_script_escape_hatch` (asserts `report_path: build/reports/jacoco/test/lcov.info` and `threshold: 80`); gate script handles Maven path `target/site/jacoco/lcov.info` natively | Implemented |
| AC-004 | `test_gate_jacoco_absent_on_gradle_skips_with_setup_guide`, `test_gate_jacoco_absent_on_maven_skips_with_setup_guide` | Implemented |
| AC-005 | `test_snapshots_capability_uses_script_escape_hatch`, `test_snapshots_no_library_skips`, `test_snapshots_kotest_detected_on_gradle_kts`, `test_snapshots_approvaltests_detected_on_maven` | Implemented |
| AC-006 | `test_properties_capability_uses_script_escape_hatch`, `test_properties_no_library_skips`, `test_properties_jqwik_detected_on_maven`, `test_properties_kotest_property_detected_on_gradle_kts` | Implemented |
| AC-007 | `test_mutation_capability_uses_script_escape_hatch`, `test_mutation_pitest_absent_on_gradle_skips_with_setup_hint`, `test_mutation_pitest_absent_on_maven_skips_with_setup_hint`, `test_mutation_pitest_present_on_gradle_probe_only`, `test_mutation_pitest_present_on_maven_probe_only` | Implemented |
| AC-008 | `test_parse_pitest_xml_extracts_counts`, `test_parse_pitest_xml_zero_fills_missing_statuses`, `test_parse_pitest_xml_handles_lowercase_status`, `test_parse_pitest_xml_ignores_unknown_statuses`, `test_parse_pitest_xml_ignores_mutation_without_status_attribute` | Implemented |
| AC-009 | `test_jvm_driver_schema_validation`, `test_jvm_driver_capabilities_exist` | Implemented |
| AC-010 | `test_detect_build_tool_gradle_priority_over_maven`, `test_gradle_priority_over_maven_in_detect_build_tool`, `test_gate_gradle_priority_over_maven` | Implemented |
| AC-011 | `test_detect_build_tool_gradle_kotlin`, `test_parse_gradle_build_kotlin_dsl`, `test_dependency_detection_in_gradle_kotlin_fixture`, `test_snapshots_kotest_detected_on_gradle_kts`, `test_properties_kotest_property_detected_on_gradle_kts` | Implemented |

## Test Results

- **New unit tests:** 44 (24 detector + 8 coverage-gate + 12 mutation/snapshots/properties scripts) — all pass.
- **New integration tests:** 15 — all pass.
- **Full suite:** 843 passed, 28 skipped, 0 failed (Python 3.14).
- **Type audit:** `pyright validator/drivers/` — 0 errors, 0 warnings.
- **Lint audit:** `ruff check` on driver + new test files passes.

## Notes

- **All four capabilities use `script:` escape hatches.** The Gradle vs Maven dispatch must happen before any concrete tool invocation, and both build tools differ enough at the CLI level (`./gradlew test jacocoTestReport jacocoTestCoverageVerification` vs `mvn verify`; `./gradlew pitest` vs `mvn org.pitest:pitest-maven:mutationCoverage`) that no single `command:` covers them. This mirrors the Go (020) and Swift (019) script-escape-hatch pattern.
- **No XML stdlib dependency.** The first cut used `xml.etree.ElementTree`, but the local Python 3.14 ships a pyexpat ABI mismatch (`Symbol not found: _XML_SetAllocTrackerActivationThreshold`) that makes ElementTree unusable. Both the Maven POM parser and the pitest XML parser were rewritten as shallow regex matches over `<artifactId>...</artifactId>` and `<mutation status="...">`. The information we extract is shallow enough that this is robust; both parsers reject input that doesn't contain XML-shaped tags so junk strings never accidentally produce non-zero counts.
- **Gradle DSL is parsed by token regex.** Gradle (Groovy or Kotlin) is Turing-complete; we extract identifier tokens (`[A-Za-z][A-Za-z0-9._-]*`) after stripping `//` line comments and `/* */` block comments. The output is consultative — `has_jvm_dependency` does substring matching so callers can look up either short names (`pitest`) or fully qualified plugin coordinates (`info.solidsoft.pitest`).
- **Gradle takes priority over Maven** when both build files are present (AC-010). Implemented in `detect_build_tool` and in every shell script that needs to dispatch.
- **Coverage threshold default is 80%** matching the spec example (Story 1, AC-003). The threshold itself is enforced by JaCoCo's build rule (`jacocoTestCoverageVerification` / `<rule>` element) inside the build tool, not by the gate script — the script only locates lcov.info and surfaces the verdict.
- **lcov.info is not native to JaCoCo.** JaCoCo emits XML and HTML by default; lcov export requires a small Gradle task. Spec AC-003 acknowledges this and supports a configurable override path; the gate script emits a clear "JaCoCo configured but lcov.info not found — add an lcov export task" warning (exit 0) when the file is absent.
- **pitest XML report path varies between build tools** (Gradle: `build/reports/pitest/mutations.xml`; Maven: `target/pit-reports/<timestamp>/mutations.xml`). The mutation script handles both, picking the lexicographic-max timestamped directory on the Maven side per EC-004.
- **Script tests run in probe-only mode** (`LIVESPEC_JVM_SKIP_RUN=1`) so no real `gradle` / `mvn` invocations happen during pytest. Scripts exit 0 with "library detected" / "pitest detected" status messages when probe-only is set.

## Implementation Summary

Feature 022 ships a complete JVM driver covering Java + Kotlin in a single manifest. Detection: `build.gradle`, `build.gradle.kts`, or `pom.xml` (Gradle priority when both present, AC-010). All four capabilities (coverage, snapshots, properties, mutation) use `script:` escape hatches because Gradle vs Maven dispatch happens before any concrete tool invocation. Coverage runs JaCoCo via the build tool (the threshold is enforced by JaCoCo's build rule, not the gate script); snapshots and properties auto-detect the test library (kotest-snapshot/approvaltests, kotest-property/jqwik) and skip with documented messages when absent; mutation runs pitest and locates `mutations.xml` at the Gradle or Maven path. Build file parsing uses a permissive token regex for Gradle DSL (Turing-complete; consultative detection) and a shallow `<artifactId>` regex for Maven POMs (avoids the stdlib XML backend, which depends on pyexpat and is broken on the local Python 3.14). The pitest XML parser is regex-based for the same reason, exposing KILLED/SURVIVED/TIMED_OUT/NO_COVERAGE/MEMORY_ERROR/RUN_ERROR counts. All 59 new tests plus the existing 784-test base pass on Python 3.14 (843 total).

---

*LiveSpec Feature 022 Implementation — Complete — 2026-05-07*
