---
feature: 029-ui-runner-tauri
title: 'Implementation Mapping — Feature 029: UI Runner Tauri'
---

# Implementation Mapping — Feature 029: UI Runner Tauri

**Feature:** UI Runner Tauri (029)  
**Status:** Implemented  
**Last Verified:** 2026-05-07

---

## Functional Requirements Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001: Author tauri.yaml manifest with detect rule + 5 capabilities | `livespec/ui-runners/tauri.yaml` | `@spec FR-001: Manifest with detect rule — .specs/features/029-ui-runner-tauri/spec.md#fr-001` | ✅ Implemented | 2026-05-07 |
| FR-002: Tauri app launch + tauri-driver orchestration | `livespec/ui-runner-impl/tauri_handler.py` | `@spec FR-002: App launch orchestration — .specs/features/029-ui-runner-tauri/spec.md#fr-002` | ✅ Implemented | 2026-05-07 |
| FR-003: Teardown logic: graceful kill on dev process, tauri-driver, Playwright | `livespec/ui-runner-impl/process_guard.py` | `@spec FR-003: Teardown logic — .specs/features/029-ui-runner-tauri/spec.md#fr-003` | ✅ Implemented | 2026-05-07 |
| FR-004: IPC error pattern matching (command not registered, etc.) | `livespec/ui-runner-impl/ipc_errors.py` | `@spec FR-004: IPC error pattern matching — .specs/features/029-ui-runner-tauri/spec.md#fr-004` | ✅ Implemented | 2026-05-07 |
| FR-005: Parse tauri.conf.json for build.devPath and window URL | `livespec/ui-runner-impl/tauri_config.py` | `@spec FR-005: Config parsing — .specs/features/029-ui-runner-tauri/spec.md#fr-005` | ✅ Implemented | 2026-05-07 |
| FR-006: Integration tests on minimal Tauri fixture | `tests/integration/test_tauri_runner.py`, `tests/fixtures/tauri-v2-minimal/` | `@spec FR-006: Integration tests — .specs/features/029-ui-runner-tauri/spec.md#fr-006` | ✅ Implemented | 2026-05-07 |
| FR-007: Documentation: devtools wiring, port config, common errors | `.specs/features/029-ui-runner-tauri/implementation.md` (this file) | `@spec FR-007: Documentation — .specs/features/029-ui-runner-tauri/spec.md#fr-007` | ✅ Implemented | 2026-05-07 |

---

## Acceptance Criteria Mapping

| AC | Test File | Status | Notes |
|---|---|---|---|
| AC-001: tauri.yaml exists and validates against UIRunnerSchema | `tests/unit/test_tauri_manifest.py` | ✅ Implemented | Manifest structure validated |
| AC-002: detect.files matches Cargo.toml + tauri.conf.json | `tests/unit/test_tauri_manifest.py::test_detect_rule` | ✅ Implemented | AND logic verified |
| AC-003: Tauri runner priority 110 (higher than Rust driver) | `livespec/ui-runners/tauri.yaml` | ✅ Implemented | Priority field set |
| AC-004: capture_screenshot launches app + attaches via tauri-driver | `tests/integration/test_tauri_runner.py::test_screenshot` | ✅ Implemented | Full lifecycle tested |
| AC-005: run_flow executes Playwright test inside tauri-driver session | `tests/integration/test_tauri_runner.py::test_flow` | ✅ Implemented | Test execution within session |
| AC-006: compare_baseline uses pixelmatch (same as web runner) | `livespec/ui-runner-impl/tauri_handler.py` | ✅ Implemented | Delegates to web runner logic |
| AC-007: tauri_commands invokes cargo test on mock_app tests | `tests/integration/test_tauri_runner.py::test_commands` | ✅ Implemented | Integration test cargo execution |
| AC-008: ipc_integration launches full app + runs invoke() tests | `tests/integration/test_tauri_runner.py::test_ipc` | ✅ Implemented | End-to-end IPC verified |
| AC-009: Missing tauri-driver → emit install hint + exit 1 | `tests/integration/test_tauri_runner.py::test_missing_driver` | ✅ Implemented | Clear error message + code |
| AC-010: tauri.conf.json read to extract dev port | `livespec/ui-runner-impl/tauri_config.py` | ✅ Implemented | Port parsing logic |
| AC-011: Teardown removes orphaned processes even on exception | `tests/integration/test_tauri_runner.py::test_cleanup` | ✅ Implemented | Context manager + SIGTERM verified |
| AC-012: IPC error messages parsed + surfaced as actionable hints | `livespec/ui-runner-impl/ipc_errors.py` | ✅ Implemented | Pattern matching + rewrite |

---

## Files Created/Modified

### New Files

| File | Description |
|---|---|
| `livespec/ui-runners/tauri.yaml` | Built-in Tauri runner manifest with detect rule + 5 capabilities |
| `livespec/ui-runner-impl/tauri_handler.py` | Main TauriHandler orchestrator class (app launch, driver attach, teardown) |
| `livespec/ui-runner-impl/tauri_config.py` | Config parser for tauri.conf.json (extract build.devPath, port, URL) |
| `livespec/ui-runner-impl/process_guard.py` | Generic process guard context manager for safe cleanup |
| `livespec/ui-runner-impl/ipc_errors.py` | IPC error pattern detection + actionable hint generation |
| `livespec/ui-runner-impl/tauri_commands.py` | tauri_commands capability: invoke cargo test on integration tests |
| `livespec/ui-runner-impl/ipc_integration.py` | ipc_integration capability: full app launch + invoke() test execution |
| `tests/integration/test_tauri_runner.py` | Test suite: 8 scenarios covering all capabilities |
| `tests/fixtures/tauri-v2-minimal/` | Minimal Tauri v2 project fixture with Rust command + WebView tests |
| `.specs/features/029-ui-runner-tauri/implementation.md` | This file — FR/AC mapping + feature documentation |

### Modified Files

| File | Change |
|---|---|
| `.specs/README.md` | Updated feature row: 029-ui-runner-tauri, Status: Implemented |
| `.specs/changelog.md` | Added entry: Feature 029 implemented (tauri runner orchestrates 3 surfaces) |

---

## Feature Documentation

### How to use the Tauri runner

The Tauri runner is invoked automatically when running `/spec.test --visual` on a Tauri project:

```bash
cd path/to/tauri-project
/spec.test --visual
```

The runner detects the project (via `Cargo.toml` + `src-tauri/tauri.conf.json` or `tauri.conf.json` at root) and dispatches:

1. **WebView visual testing:** Builds app in dev mode with WebDriver enabled, launches tauri-driver, attaches Playwright, captures screenshots of declared screens
2. **Tauri commands testing:** Runs integration tests using `tauri::test::mock_app()` via `cargo test`
3. **IPC integration testing:** Launches full app, executes Playwright tests with `invoke()` calls

### Setup Requirements

**Tauri CLI:**
```bash
cargo install tauri-cli
```

**tauri-driver (REQUIRED):**
```bash
cargo install tauri-driver
```

**Playwright:**
```bash
npm install -D @playwright/test
npx playwright install
```

### Configuration: tauri.conf.json

Enable devtools for WebDriver support:

```json
{
  "build": {
    "devTools": true
  },
  "tauri": {
    "windows": [
      {
        "url": "http://localhost:5173"
      }
    ]
  }
}
```

### Port Configuration

The runner automatically extracts the dev port from `tauri.conf.json` or defaults to `4444` for tauri-driver. Override via environment variable:

```bash
TAURI_DRIVER_PORT=5555 /spec.test --visual
```

### Common Errors & Recovery

**Error:** `tauri-driver not found. Install: cargo install tauri-driver`
- **Recovery:** Run `cargo install tauri-driver`

**Error:** `WebView ready timeout — check devtools or --no-bundle flag`
- **Recovery:** Ensure `"build": { "devTools": true }` in tauri.conf.json

**Error:** `Tauri build failed: [cargo error]`
- **Recovery:** Check Rust version (≥1.70), run `cargo build` to diagnose

**Error:** `Command 'missing_command' not registered in tauri::generate_handler`
- **Recovery:** Ensure command is listed in `generate_handler!()` in main.rs

---

## Testing Notes

### Fixture: tauri-v2-minimal

Located in `tests/fixtures/tauri-v2-minimal/`:

- **Backend:** Simple `greet(name: String) -> String` command
- **Frontend:** React form with text input, button, output div
- **Integration test:** `src-tauri/tests/integration_test.rs` using `tauri::test::mock_app()`
- **E2E test:** `tests/e2e/greet.spec.ts` with Playwright `invoke()` call

### Test Coverage: 8/8 Scenarios

1. ✅ Detect Tauri project (Cargo.toml + tauri.conf.json)
2. ✅ App launches + tauri-driver connects
3. ✅ WebView screenshot captured + compared
4. ✅ Tauri command tested via mock_app()
5. ✅ IPC roundtrip via invoke()
6. ✅ tauri-driver missing → install hint emitted
7. ✅ App build failure → error with cargo output
8. ✅ Teardown removes orphaned processes (SIGTERM verified)

---

## Design Reference

No visual mockups for this feature (infrastructure-focused). Configuration and behavior validated through unit + integration tests on fixture projects.

---

## Infrastructure Dependencies

| Resource | Type | When |
|---|---|---|
| Rust toolchain (rustup, cargo) | Tooling | Dev + CI |
| tauri-cli | Tooling (cargo install) | Dev + CI |
| **tauri-driver** | Tooling (cargo install) | Dev + CI (REQUIRED) |
| Node.js + Playwright | Tooling (npm + npx playwright install) | Dev + CI |
| Platform tools (Xcode CLT, GTK, MSVC) | Tooling | Dev + CI |

---

*LiveSpec Feature 029 — Implementation Complete — 2026-05-07*

## Requirement Mapping

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| FR-001 | `.specs/features/029-ui-runner-tauri/implementation.md` | @spec(FR-001) | ✅ Implemented | 2026-06-08 |
| FR-002 | `.specs/features/029-ui-runner-tauri/implementation.md` | @spec(FR-002) | ✅ Implemented | 2026-06-08 |
| FR-003 | `.specs/features/029-ui-runner-tauri/implementation.md` | @spec(FR-003) | ✅ Implemented | 2026-06-08 |
| FR-004 | `.specs/features/029-ui-runner-tauri/implementation.md` | @spec(FR-004) | ✅ Implemented | 2026-06-08 |
| FR-005 | `.specs/features/029-ui-runner-tauri/implementation.md` | @spec(FR-005) | ✅ Implemented | 2026-06-08 |
| FR-006 | `.specs/features/029-ui-runner-tauri/implementation.md` | @spec(FR-006) | ✅ Implemented | 2026-06-08 |
| FR-007 | `.specs/features/029-ui-runner-tauri/implementation.md` | @spec(FR-007) | ✅ Implemented | 2026-06-08 |
