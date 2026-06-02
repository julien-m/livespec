# Executable User Journeys

Canonical journey sources live at `.specs/journeys/<feature-slug>/<journey-id>.journey.yaml`.

## YAML Shape

```yaml
id: login-happy-path
feature: 012-auth
title: User can log in
run_policy: always
covers:
  ac: [AC-001]
  fr: [FR-001]
target:
  surface: web
steps:
  - open: "/login"
  - fill: { label: "Email", value: "user@example.com" }
  - click: { role: "button", name: "Login" }
  - wait: { seconds: 10, until: { text: "Dashboard" } }
  - assert: { text: "Dashboard" }
```

## Required Fields

- `id`, `feature`, `title`, `target.surface`, `steps`.
- `target.surface`: `web`, `ios`, `watchos`, `android`, or `maestro`.
- `run_policy`: `always`, `smoke`, `manual`, or `disabled`; default `always`.
- `manual_reason`: required when `run_policy: manual`.
- `disabled: true`: disables execution but remains visible to `livespec doctor`.

## Actions

- `open`: path or URL.
- `click`: `{ role, name }`.
- `fill`: `{ label, value }`.
- `select`: `{ label, value }`.
- `wait`: `{ seconds, until? }`; fixed waits without `until` require `reason` or warn.
- `assert` / `assert_not`: `{ text }`.
- `screenshot`, `back`, `press`.

## Commands

- `livespec journey validate [--feature <slug>]`: schema/action validation.
- `livespec journey compile [--feature <slug>]`: ahead-of-time native artifact generation.
- `livespec journey test [--feature <slug>]`: compile plus category summary.

## Compilation

- Web → Playwright: `tests/e2e/journeys/<feature>/<id>.spec.ts`.
- iOS/watchOS → XCUITest: `STRAPTUITests/Journeys/<Id>Journey.swift`.
- Android/Maestro → `.specs/maestro/journeys/<feature>/<id>.yaml`.
- Every compiled artifact embeds `livespec-journey-source-hash: <sha256>` for stale detection.

## Doctor

`livespec doctor` reports invalid YAML, missing/superseded AC/FR references, missing/stale compiled artifacts, manual journeys, and disabled journeys. Executable, manual, and disabled journeys never collapse into direct generated tests.
