---
title: Runner Config Wiring (xcuitest scheme/project + maestro AVD)
status: Implemented
scope: M
priority: P1
created: 2026-05-08
---

# Feature 038 — Runner Config Wiring

## Why

After Feature 037 merged, `livespec ui-runner dispatch` failed with `xcodebuild` exit
65 in real client projects (Strapt, etc.) because the dispatcher invoked
`xcodebuild test` without `-scheme` and `-project` flags. The `runnerConfig` field
existed in `Surface.from_dict()` but was never propagated to `handler.capture_screenshot()`,
and `generate-surfaces.js` never populated it.

This feature wires `runnerConfig` end-to-end so xcuitest and maestro surfaces work
in real conditions, not just with mocks.

## User stories

- **US-001 (P1):** As a project author, when I run `/spec.test --visual`, the
  dispatcher invokes `xcodebuild` with the right `-scheme`, `-project`, and
  `-destination` resolved from `surfaces.yaml`.
- **US-002 (P1):** As a project author with iPhone + Apple Watch surfaces, the
  dispatcher picks the right scheme per platform (`STRAPT` for iOS, `STRAPT Watch App`
  for watchOS).
- **US-003 (P1):** As a project author with an existing v8/v12 `surfaces.yaml`
  that lacks `runnerConfig`, the dispatcher auto-detects scheme/project from
  `xcshareddata/xcschemes/` so I don't need to migrate manually.

## Functional requirements

- **FR-001:** Dispatcher MUST translate `surface.runner_config` keys into
  `handler.capture_screenshot(**kwargs)` (e.g. `scheme` → `test_scheme`,
  `destination` → `destination`).
- **FR-002:** `generate-surfaces.js` MUST extract scheme names from
  `<xcodeproj>/xcshareddata/xcschemes/*.xcscheme` and populate xcuitest
  surface `runnerConfig` with `project`, `scheme`, `destination`.
- **FR-003:** `XCUITestRunnerHandler.capture_screenshot()` MUST auto-detect the
  scheme via `xcshareddata/xcschemes/` when `test_scheme` is not provided.
- **FR-004:** `XCUITestRunnerHandler.capture_screenshot()` MUST auto-detect the
  `.xcodeproj` (or `.xcworkspace`) when `project` is not provided.
- **FR-005:** `surfaces.yaml` writer MUST emit `runnerConfig` as a nested YAML
  map when it is an object, preserving the legacy single-line form when it is
  a string (Playwright config path).
- **FR-006:** Maestro surfaces MUST receive `runnerConfig` containing
  `flowsDir` and `platform: android` (extensible to `avdName`, `appId`).
- **FR-007:** Unknown `runnerConfig` keys MUST be silently dropped at dispatch
  time so future fields don't crash existing dispatchers.
- **FR-008:** `XCUITestRunnerHandler` MUST emit a typed BLOCKED reason when no
  scheme can be located, instructing the user to share a scheme via
  Xcode > Product > Scheme > Manage Schemes.

## Acceptance criteria

- **AC-001:** `Surface(runner_config={"scheme": "S"})` results in
  `capture_screenshot(screen, test_scheme="S")` being called.
- **AC-002:** `Surface(runner_config={"avdName": "Pixel_8_API_35"})` results
  in `capture_screenshot(screen, avd_name="Pixel_8_API_35")` for maestro.
- **AC-003:** Legacy `runnerConfig: <string>` is normalized to
  `{"_path": "<string>"}` for backward compat.
- **AC-004:** `buildXcuitestRunnerConfig` returns `{project, scheme, destination}`
  when shared schemes exist, and `{project, destination}` (no scheme) otherwise.
- **AC-005:** `pickSchemeForPlatform(["App", "App Watch App"], "watchos")`
  returns `"App Watch App"`.
- **AC-006:** Existing legacy fixture (`runnerConfig: apps/web/playwright.config.ts`)
  continues to pass tests unchanged.
- **AC-007:** `XCUITestRunnerHandler` returns a `BLOCKED` UICapabilityResult
  with actionable message when no scheme is shareable.

## Non-goals

- Migrating existing `surfaces.yaml` files to add `runnerConfig` — auto-detect
  is sufficient. A separate migration (v13) can be added later if needed.
- Wear OS scheme detection — relies on the same `watch` heuristic as iOS.
- xcrun-based scheme listing for non-shared schemes — explicit user opt-in
  is the only path (share via Xcode UI).
