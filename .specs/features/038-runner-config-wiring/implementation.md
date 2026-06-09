---
created: 2026-05-08
feature: 038
status: Complete
title: Runner Config Wiring — Implementation
updated: 2026-06-08
---

# Implementation: 038 — Runner Config Wiring

## Summary

Implemented end-to-end `runnerConfig` propagation for native UI runners. Structured config now survives YAML generation and dispatcher parsing, supported keys are translated to handler kwargs, XCUITest can recover project/scheme/destination when legacy manifests omit config, and unknown keys are ignored for forward compatibility.

## Requirement Mapping
| Requirement | Implementation | Tests / Evidence | Status |
|---|---|---|---|
| FR-001 | `validator/ui_runner_dispatcher.py`; `validator/ui_runner_protocol.py` | `tests/test_phase_4_5_dispatcher.py` | Complete |
| FR-002 | `scripts/generate-surfaces.js`; `scripts/lib/pbxproj.js` | `tests/test_generate_surfaces.js` | Complete |
| FR-003 | `validator/ui_runner_xcuitest.py` | `tests/test_xcuitest_scheme_detection.py` | Complete |
| FR-004 | `validator/ui_runner_xcuitest.py` | `tests/test_xcuitest_scheme_detection.py` | Complete |
| FR-005 | `scripts/generate-surfaces.js` | `tests/test_generate_surfaces.js` | Complete |
| FR-006 | `scripts/generate-surfaces.js`; `validator/ui_runner_dispatcher.py`; `validator/ui_runner_maestro.py` | `tests/test_generate_surfaces.js`; `tests/test_phase_4_5_dispatcher.py` | Complete |
| FR-007 | `validator/ui_runner_dispatcher.py` | `tests/test_phase_4_5_dispatcher.py` | Complete |
| FR-008 | `validator/ui_runner_xcuitest.py` | `tests/test_xcuitest_scheme_detection.py`; `tests/test_phase_4_5_dispatcher.py` | Complete |

## Acceptance Criteria Map

| AC | Evidence | Status |
|---|---|---|
| AC-001 | `validator/ui_runner_dispatcher.py`; `tests/test_phase_4_5_dispatcher.py` | Complete |
| AC-002 | `validator/ui_runner_dispatcher.py`; `validator/ui_runner_maestro.py`; `tests/test_phase_4_5_dispatcher.py` | Complete |
| AC-003 | `validator/ui_runner_dispatcher.py`; `tests/test_phase_4_5_dispatcher.py`; `tests/test_generate_surfaces.js` | Complete |
| AC-004 | `scripts/generate-surfaces.js`; `scripts/lib/pbxproj.js`; `tests/test_generate_surfaces.js` | Complete |
| AC-005 | `scripts/lib/pbxproj.js`; `tests/test_generate_surfaces.js` | Complete |
| AC-006 | `scripts/generate-surfaces.js`; `tests/test_generate_surfaces.js` | Complete |
| AC-007 | `validator/ui_runner_xcuitest.py`; `tests/test_xcuitest_scheme_detection.py`; `tests/test_phase_4_5_dispatcher.py` | Complete |

## Verification

Read [`plan.md`](plan.md) for the verification commands used to validate this feature.

## Traceability Anchors

<!-- @spec(FR-001) -->
<!-- @spec(FR-002) -->
<!-- @spec(FR-003) -->
<!-- @spec(FR-004) -->
<!-- @spec(FR-005) -->
<!-- @spec(FR-006) -->
<!-- @spec(FR-007) -->
<!-- @spec(FR-008) -->
<!-- @spec(AC-001) -->
<!-- @spec(AC-002) -->
<!-- @spec(AC-003) -->
<!-- @spec(AC-004) -->
<!-- @spec(AC-005) -->
<!-- @spec(AC-006) -->
<!-- @spec(AC-007) -->
