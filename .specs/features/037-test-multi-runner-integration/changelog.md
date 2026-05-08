# Feature 037 — Changelog

### 2026-05-08 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-015 (all defined)
- **Author:** /spec.specify (--auto)

### 2026-05-08 — Plan: Technical plan generated

- **Type:** Feature
- **Spec modified:** No
- **Code modified:** None (plan.md created)
- **AC impacted:** None (pre-implementation)
- **Author:** /spec.plan (--auto)

### 2026-05-08 — Feature: Initial implementation of multi-runner Phase 4.5 dispatcher

- **Type:** Feature
- **Spec modified:** No
- **Code modified:**
  - `validator/ui_runner_protocol.py` (new)
  - `validator/ui_runner_dispatcher.py` (new)
  - `validator/ui_runner_web.py` (preflight_message)
  - `validator/ui_runner_xcuitest.py` (preflight_message)
  - `validator/ui_runner_maestro.py` (preflight_message + screen first arg)
  - `scripts/lib/pbxproj.js` (new)
  - `scripts/generate-surfaces.js` (multi-target Xcode enumeration)
  - `commands/test.md` (--visual flag + Phase 4.5 dispatcher narrative)
  - `tests/test_ui_runner_protocol.py` (new, 3 tests)
  - `tests/test_preflight_messages.py` (new, 9 tests)
  - `tests/test_phase_4_5_dispatcher.py` (new, 11 tests)
  - `tests/test_generate_surfaces.js` (extended, +5 tests)
  - `tests/integration/test_generate_surfaces_xcode.py` (new, 3 tests)
  - `tests/integration/test_visual_dispatch_xcuitest.py` (new, 2 tests)
  - `tests/integration/test_visual_dispatch_maestro.py` (new, 2 tests)
  - `tests/integration/test_visual_dispatch_playwright.py` (new, 2 tests)
- **AC impacted:** AC-001..AC-007, AC-008, AC-010, AC-011..AC-015 (AC-009 documented in commands/test.md)
- **Author:** /spec.implement (--auto)
