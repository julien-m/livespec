<!-- LiveSpec traceability anchors -->
<!-- @spec(FR-001) -->
<!-- @spec(FR-041) -->

# Executable User Journeys v2

Canonical journey sources live at `.specs/journeys/<journey-id>/journey.yaml`.

## Directory Contract

- `journey.yaml`: portable source of truth.
- `changelog.md`: concise history.
- `decisions/*.md`: mandatory reason for edits after compilation.
- `compiled/manifest.json`: source hash, compiler version, runner, native outputs, visual contracts.
- `runs/`: local/CI evidence.
- `.specs/features/<feature>/journeys.md`: generated backlink; do not edit manually.

## YAML Shape

```yaml
schema_version: 2
id: onboarding-first-project
title: Onboarding first project
status: active
description: New user signs up and creates a first project.
covers:
  - feature: 001-onboarding
    kind: ac
    ref: AC-001
    reason: Signup starts the path.
run_policy:
  local: impacted
  pre_push: smoke
  ci: always
targets:
  - surface: web
    runner: playwright
steps:
  - action: open
    target: { route: /signup }
privacy:
  llm_allowed: false
  retention: none
```

## Commands

- `livespec journey validate [--journey ID] [--feature SLUG] [--json]`: schema, refs, history, backlinks, privacy.
- `livespec journey compile [--journey ID] [--feature SLUG] [--changed] [--force]`: compile on create/edit only. For XCUITest projects with `project.yml` or `project.yaml`, compilation also runs `xcodegen generate` so generated Swift journey files are included by the Xcode project.
- `livespec journey run [--journey ID] [--feature SLUG] [--stage STAGE] [--json]`: run compiled artifacts through their native runner; does not compile.
- `livespec journey impact --changed-file PATH [--json]`: find journeys touched by changed labels, selectors, semantic IDs, visual targets.
- `livespec journey migrate --from-v1`: convert `.specs/journeys/<feature>/*.journey.yaml` to v2.
- `livespec journey list|inspect`: inspect global coverage.

## Fixture Bootstrap Contract

<!-- @spec FR-011: Fixture bootstrap contract documentation
     — ../../.specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-011 -->

Projects whose XCUITest journeys declare `preconditions.fixtures` or
`preconditions.mocks` MUST declare them in a project-local contract at
`.specs/journeys/fixtures.yaml`. The contract is the single source of truth for
what each fixture guarantees once the app finishes bootstrapping, and drives
derived `waitForJourneyBootstrap` waits in the generated Swift — a fixture
journey can never assert business UI before bootstrap is proven.

### Schema (`schema_version: 1`)

```yaml
schema_version: 1
bootstrap:                      # optional — omit for no ready-marker wait
  ready_marker:                 # per-surface accessibility identifier map
    ios: ui-test-bootstrap-ready
  timeout_seconds: 15           # default 15, bounds 1-60 (per individual wait)
fixtures:
  session-workout:              # opaque id referenced by preconditions.fixtures
    surfaces: [ios]             # surfaces this fixture supports (min 1)
    expected_screen:            # optional per-surface screen marker
      ios: iphone-session-page
    required_markers:           # optional per-surface marker list
      ios: [session-exercise-list]
mocks:
  storekit-pro:                 # opaque id referenced by preconditions.mocks
    surfaces: [ios]
```

`timeout_seconds` applies uniformly to each individual emitted wait (not a
total budget); keep marker lists short so stacked waits stay well inside the
120s XCUITest runner timeout.

### Derivation rules

For each journey surface, the compiler resolves a bootstrap plan:

- `required_markers` = sorted deduplicated union across the journey's fixtures.
- `expected_screen` is derived only when fixtures yield 0–1 distinct value for
  the surface; 2+ distinct values are a blocking `journey_bootstrap_ambiguous`
  error unless the journey overrides the screen.
- The optional journey override `preconditions.bootstrap` (`expected_screen`
  **replaces** the derived value and resolves ambiguity; `required_markers`
  **append** to the union, re-sorted).
- Wait emission order after `app.launch()` is deterministic: ready_marker →
  expected_screen → sorted required_markers, each via
  `waitForJourneyBootstrap(app, marker, timeout:)` failing with
  `XCTFail("JOURNEY_BOOTSTRAP_FAILURE: ...")`.
- A journey without fixtures and mocks needs no contract and compiles
  byte-identically (no waits, no helper).

### App-side responsibilities

- Expose the `ready_marker` accessibilityIdentifier only once the
  `UI_TEST_JOURNEY_FIXTURES` handler has fully completed seeding.
- Only declare `expected_screen` for fixtures that actually navigate; a
  seed-only fixture (no screen, no markers) yields a ready-marker-only plan.
- Expose every `required_markers` identifier on the seeded screen state.

### Staleness and recompilation

Any change to `fixtures.yaml` after compilation invalidates the compiled
artifacts: the manifest records `fixtures_contract_hash`, and
`livespec journey run` fails with `journey_compiled_stale` until
`livespec journey compile --force` regenerates them. Pre-contract manifests
(`journeys-v2-2` and older) are rejected unconditionally with
`journey_compiler_stale`.

### Validation error codes (blocking, XCUITest-only in v1)

| Code | Meaning | Recovery |
|---|---|---|
| `journey_fixture_contract_missing` | Journey declares fixtures/mocks but no `fixtures.yaml` exists | Paste the YAML skeleton embedded in the error message, or run `livespec journey fixtures scaffold` |
| `journey_fixtures_contract_invalid` | Unreadable YAML, non-mapping root, or schema violation (e.g. `timeout_seconds` out of 1–60) | Fix the contract file |
| `journey_fixture_unknown` | A declared fixture/mock id is absent from the contract maps | Add the entry to `fixtures.yaml` |
| `journey_fixture_surface_unsupported` | The journey surface is not in the referenced entry's `surfaces` | Add the surface to the entry |
| `journey_bootstrap_ambiguous` | Fixtures derive 2+ distinct expected screens | Declare `preconditions.bootstrap.expected_screen` |

At runtime, a non-zero native exit whose output contains
`JOURNEY_BOOTSTRAP_FAILURE:` is reported as `journey_bootstrap_marker_missing`
(matched line first) instead of the generic `journey_native_run_failed`; no
`.xcresult` bundle is parsed. Playwright/Maestro enforcement is deferred — the
surface-agnostic maps keep the schema forward-compatible.

`livespec journey fixtures scaffold` writes a minimal valid contract from
existing journeys (ids enumerated, surfaces inferred from targets, no screens,
no markers, no bootstrap block) and never overwrites an existing file.

## Execution Rules

- Create/edit validates, compiles once, runs once, and records history.
- Run/test commands verify `compiled/manifest.json` source hash and fail with `journey_compiled_stale` if stale.
- Run/test commands also verify `compiled/manifest.json` compiler version and fail with `journey_compiler_stale`; migration-level compiler changes require explicit `livespec journey compile` regeneration before execution.
- Run/test commands also verify the recorded `fixtures_contract_hash` against the current `.specs/journeys/fixtures.yaml` and fail with `journey_compiled_stale` when the contract changed after compilation (see Fixture Bootstrap Contract).
- Native execution dispatch:
  - `playwright`: `npx playwright test <compiled .spec.ts>`
  - `xcuitest`: `xcodebuild test ... -only-testing:<UITestTarget>/<JourneyClass>`
  - `maestro`: `maestro test <compiled flow.yaml>`
  - `pytest`: `pytest <compiled test>`
  - `cargo`: `cargo test` for capability-supported non-UI journeys only.
- `manual` and `disabled` journeys are reported and never executed automatically.
- LLM visual checks require `privacy.llm_allowed: true`; native checks are deterministic and blocking by default.

## Migration Notes

- Projects that already created User Journeys v2 before compiler `journeys-v2-2` must re-run `livespec journey compile` or targeted `livespec journey compile --journey <id>` after migration.
- Existing XCUITest projects using XcodeGen must have `xcodegen` available during compilation; otherwise compile fails with `journey_xcodegen_missing` or `journey_xcodegen_failed`.
