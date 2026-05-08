---
title: "Implementation — Test Multi-Runner Integration"
feature: "037-test-multi-runner-integration"
spec_ref: "spec.md"
plan_ref: "plan.md"
status: "Implemented"
updated: 2026-05-08
---

# Implementation: Test Multi-Runner Integration

## FR → @spec mapping

| Requirement | Source file | Anchor | Status | Date |
|---|---|---|---|---|
| [FR-001: Phase 4.5 reads surfaces.yaml + iterates](spec.md#fr-001) | `validator/ui_runner_dispatcher.py` | `# @spec FR-001: Phase 4.5 reads surfaces.yaml + iterates — .specs/features/037-test-multi-runner-integration/spec.md#fr-001` | Implemented | 2026-05-08 |
| [FR-002: Runner registry maps runner→handler](spec.md#fr-002) | `validator/ui_runner_dispatcher.py`, `validator/ui_runner_protocol.py` | `# @spec FR-002: Runner registry maps runner→handler — .specs/features/037-test-multi-runner-integration/spec.md#fr-002` | Implemented | 2026-05-08 |
| [FR-003: No Playwright artefacts for non-playwright runners](spec.md#fr-003) | `validator/ui_runner_dispatcher.py` (gate handlers per runner) | `# @spec FR-003 ...` | Implemented | 2026-05-08 |
| [FR-004: enumerate Xcode test targets](spec.md#fr-004) | `scripts/lib/pbxproj.js`, `scripts/generate-surfaces.js` | `// @spec FR-004 ...` | Implemented | 2026-05-08 |
| [FR-005: pbxproj fallback glob](spec.md#fr-005) | `scripts/lib/pbxproj.js` (`fallbackGlobTestDirs`) | `// @spec FR-005 ...` | Implemented | 2026-05-08 |
| [FR-006: omit non-existent testDir + WARNING](spec.md#fr-006) | `scripts/lib/pbxproj.js` (`enumerateAndFallback`) + caller in `generate-surfaces.js` | `// @spec FR-006 ...` | Implemented | 2026-05-08 |
| [FR-007: watchOS/widget classification](spec.md#fr-007) | `scripts/lib/pbxproj.js` (`classifyTestTarget`) | `// @spec FR-007 ...` | Implemented | 2026-05-08 |
| [FR-008: --visual flag accepted](spec.md#fr-008) | `commands/test.md` (Flags table) | `(documentation)` | Implemented | 2026-05-08 |
| [FR-009: --visual --no-visual mutually exclusive](spec.md#fr-009) | `commands/test.md` (Flags table) | `(documentation)` | Implemented | 2026-05-08 |
| [FR-010: --visual documented](spec.md#fr-010) | `commands/test.md` | `(documentation)` | Implemented | 2026-05-08 |
| [FR-011: dispatcher detect() preflight gate](spec.md#fr-011) | `validator/ui_runner_dispatcher.py`, all three handlers' `preflight_message()` | `# @spec FR-011 ...` | Implemented | 2026-05-08 |
| [FR-012: XCUITest preflight diagnostics](spec.md#fr-012) | `validator/ui_runner_xcuitest.py` | `# @spec FR-012 ...` | Implemented | 2026-05-08 |
| [FR-013: Maestro preflight diagnostics](spec.md#fr-013) | `validator/ui_runner_maestro.py` | `# @spec FR-013 ...` | Implemented | 2026-05-08 |
| [FR-014: Phase 5 aggregated table](spec.md#fr-014) | `validator/ui_runner_dispatcher.py` (`VisualPhaseResult`) — reporter wiring deferred | `# @spec FR-014 ...` | Partial (data shape ready) | 2026-05-08 |
| [FR-015: skip unknown/manual runners](spec.md#fr-015) | `validator/ui_runner_dispatcher.py` (`_dispatch` unknown runner branch) | `# @spec FR-015 ...` | Implemented | 2026-05-08 |

## Files created

- `validator/ui_runner_protocol.py`
- `validator/ui_runner_dispatcher.py`
- `scripts/lib/pbxproj.js`
- `tests/test_ui_runner_protocol.py`
- `tests/test_preflight_messages.py`
- `tests/test_phase_4_5_dispatcher.py`
- `tests/integration/test_generate_surfaces_xcode.py`
- `tests/integration/test_visual_dispatch_xcuitest.py`
- `tests/integration/test_visual_dispatch_maestro.py`
- `tests/integration/test_visual_dispatch_playwright.py`

## Files modified

- `validator/ui_runner_web.py` — added `preflight_message()`
- `validator/ui_runner_xcuitest.py` — added `preflight_message()`
- `validator/ui_runner_maestro.py` — added `preflight_message()` and made `screen` the first positional argument of `capture_screenshot`
- `scripts/generate-surfaces.js` — replaced single-target xcuitest branch with `enumerateAndFallback`-driven multi-target emission
- `tests/test_generate_surfaces.js` — added 5 new tests for pbxproj parsing
- `commands/test.md` — added `--visual` flag row and runner-aware Phase 4.5 narrative

## Test results

- Python: 1190 passed, 32 skipped (2 pre-existing failures unrelated to this feature)
- JavaScript (bun): 27 / 27 passed
- ruff: clean
- pyright: clean on every touched file

## Notes / Future work

- **Phase 5 reporter wiring (FR-014)**: the `VisualPhaseResult` dataclass and aggregation are in place, but the actual Markdown table emission via `validator/reporter.py` is left as a future improvement (the dispatcher already returns the aggregated rows ready for rendering).
- **Optional UI runner manifest parity (Step 15)**: skipped per plan §6 (marked OPTIONAL for documentation parity only).
