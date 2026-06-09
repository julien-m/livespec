---
created: 2026-05-08
feature: 038
spec_ref: .specs/features/038-runner-config-wiring/spec.md
status: Complete
title: Runner Config Wiring — Plan
updated: 2026-06-08
---

# Plan: 038 — Runner Config Wiring

## Summary

Wire `runnerConfig` from `.specs/surfaces.yaml` through generation, parsing, dispatch, and native runner handlers. The implementation must support structured native config while preserving legacy string config for Playwright.

## Implementation Steps

| Step | Scope | Files | FR |
|---|---|---|---|
| 1 | Normalize `runnerConfig` to a dict inside the dispatcher surface model | `validator/ui_runner_dispatcher.py` | FR-001, FR-007 |
| 2 | Translate supported native keys into `capture_screenshot()` kwargs | `validator/ui_runner_dispatcher.py`; `validator/ui_runner_protocol.py` | FR-001, FR-006, FR-007 |
| 3 | Generate xcuitest config from shared Xcode schemes | `scripts/generate-surfaces.js`; `scripts/lib/pbxproj.js` | FR-002 |
| 4 | Generate Maestro config with Android platform metadata | `scripts/generate-surfaces.js` | FR-006 |
| 5 | Emit structured YAML maps for object config and preserve legacy string form | `scripts/generate-surfaces.js` | FR-005 |
| 6 | Auto-detect Xcode project/workspace, scheme, and destination in the handler when config is absent | `validator/ui_runner_xcuitest.py` | FR-003, FR-004, FR-008 |
| 7 | Add regression tests for dispatcher propagation, generator output, scheme selection, and XCUITest fallback | `tests/test_phase_4_5_dispatcher.py`; `tests/test_generate_surfaces.js`; `tests/test_xcuitest_scheme_detection.py` | AC-001..AC-007 |

## Runner Config Flow

```mermaid
flowchart LR
    A["scripts/generate-surfaces.js"] --> B[".specs/surfaces.yaml runnerConfig"]
    B --> C["Surface.from_dict()"]
    C --> D["_runner_config_to_kwargs()"]
    D --> E["handler.capture_screenshot(**kwargs)"]
    E --> F["XCUITest / Maestro runtime"]
```

## Verification Plan

| Check | Command | Coverage |
|---|---|---|
| Dispatcher propagation | `pytest tests/test_phase_4_5_dispatcher.py -q` | AC-001, AC-002, AC-003, AC-007 |
| XCUITest fallback | `pytest tests/test_xcuitest_scheme_detection.py -q` | AC-004, AC-007 |
| Surface generator | `npm test -- tests/test_generate_surfaces.js` | AC-004, AC-005, AC-006 |
| Full regression | `pytest -q`; `ruff check .` | Project health |

## Notes

The generator intentionally omits `destination`; `XCUITestRunnerHandler` detects an available simulator at runtime. This avoids stale manifests that hardcode unavailable devices such as `iPhone 16`.

## Testing Strategy

- Run focused tests for the mapped implementation.
- Run full project validation before completion.

## Risks & Considerations

- Keep this compatibility plan aligned with the living spec and implementation map.
