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

## Execution Rules

- Create/edit validates, compiles once, runs once, and records history.
- Run/test commands verify `compiled/manifest.json` source hash and fail with `journey_compiled_stale` if stale.
- Run/test commands also verify `compiled/manifest.json` compiler version and fail with `journey_compiler_stale`; migration-level compiler changes require explicit `livespec journey compile` regeneration before execution.
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
