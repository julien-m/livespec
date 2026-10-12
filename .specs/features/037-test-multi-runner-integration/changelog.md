## 2026-10-12 — [Refactor]: Protocol test now checks the production runner registry

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_ui_runner_protocol.py
- **AC impacted:** None (FR-002)
- **Author:** claude-code (test-suite cleanup, lot 5)
- **Details:** The registry casts handlers to `RunnerHandler`, so static typing cannot detect drift. The test now asserts the exact `_resolve_registry()` routing (playwright, xcuitest, maestro, tauri; tauri was previously untested). For each route it checks protocol conformance, the stored `project_dir`, and that the handler signatures bind the dispatcher's `capture_screenshot(screen)` and `compare_baseline(...)` calls.

## 2026-06-08 — [Spec Update]: Normalize changelog format

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec.doctor

---

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
  - `commands/spec-test.md` (--visual flag + Phase 4.5 dispatcher narrative)
  - `tests/test_ui_runner_protocol.py` (new, 3 tests)
  - `tests/test_preflight_messages.py` (new, 9 tests)
  - `tests/test_phase_4_5_dispatcher.py` (new, 11 tests)
  - `tests/test_generate_surfaces.js` (extended, +5 tests)
  - `tests/integration/test_generate_surfaces_xcode.py` (new, 3 tests)
  - `tests/integration/test_visual_dispatch_xcuitest.py` (new, 2 tests)
  - `tests/integration/test_visual_dispatch_maestro.py` (new, 2 tests)
  - `tests/integration/test_visual_dispatch_playwright.py` (new, 2 tests)
- **AC impacted:** AC-001..AC-007, AC-008, AC-010, AC-011..AC-015 (AC-009 documented in commands/spec-test.md)
- **Author:** /spec.implement (--auto)

## 2026-10-12 — [Refactor]: Visual dispatch integration tests merged

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/integration/test_visual_dispatch_registry.py (new), tests/integration/test_visual_dispatch_{xcuitest,maestro,playwright}.py (deleted), implementation.md
- **AC impacted:** None (AC-001..AC-003 routing via the production registry kept)
- **Author:** Claude Code (test-suite cleanup, lot 1)
- One parametrized test keeps the only behavior the fake-handler unit tests cannot see: the default registry routes each runner to its real handler class. BLOCKED, legacy fallback and no-artifact cases were duplicates of tests/test_phase_4_5_dispatcher.py.

## 2026-10-12 — [Bugfix]: runner handlers accept RunnerHandler protocol keywords and Path baselines; registry cast removed; one shared UICapabilityResult

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:** tests/test_runner_registry_protocol.py, validator/runner_dispatcher_impl.py, validator/runner_maestro_impl.py, validator/runner_web_impl.py, validator/runner_xcuitest_impl.py
- **AC impacted:** FR-002
- **Author:** livespec bugfix record
- **Base revision:** HEAD
- **Regression tests:** tests/test_runner_registry_protocol.py::test_registry_run_flow_accepts_protocol_keywords[maestro], tests/test_runner_registry_protocol.py::test_registry_run_flow_accepts_protocol_keywords[playwright], tests/test_runner_registry_protocol.py::test_registry_run_flow_accepts_protocol_keywords[xcuitest]
- **RED receipt:** `.specs/.execution/1ca6a78d8c8549308b6739975ce0bedd/receipt.json`
- **GREEN receipt:** `.specs/.execution/60a7a8bec5cb48b28c8ee4444024dcfb/receipt.json`
<!-- bugfix:60a7a8bec5cb48b28c8ee4444024dcfb -->
