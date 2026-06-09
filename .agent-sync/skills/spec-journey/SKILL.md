---
name: spec-journey
description: LiveSpec command for creating, editing, bootstrapping, impacting, and running User Journeys v2
---
<!-- LiveSpec traceability anchors -->
<!-- @spec(FR-013) -->
<!-- @spec(FR-014) -->
<!-- @spec(FR-015) -->
<!-- @spec(FR-016) -->
<!-- @spec(FR-041) -->


# $spec-journey

> **Read** [`system/anti-drift-block.md`](../../../system/anti-drift-block.md) before starting — runtime goal contract (§5), 6-field step shape (§1), ERROR/BLOCKED format (§2), finalization gate.

Use when the user wants to create, edit, bootstrap, inspect, impact-check, compile, or run cross-feature user journeys, including journeys for old or implemented features.

## Commands

- `$spec-journey create`: collect a free-form journey intent, infer features/AC/FR via `livespec journey impact/list/inspect` evidence, show confidence, allow correction, then write `.specs/journeys/<journey-id>/journey.yaml`.
- `$spec-journey edit <journey-id>`: require classification `regression`, `intentional_update`, `obsolete`, `selector_fix`, or `coverage_expansion`; write decision, changelog, validate, compile once, run once.
- `$spec-journey bootstrap --from-existing`: scan implemented features, specs, Gherkin, implementation maps, tests, routes, mockups, Penflow, and logs; propose candidates only; accepted candidates compile once and run once.
- `$spec-journey impact`: run `livespec journey impact --changed-file <path> --json` and require explicit classification for blocking impacts.
- `$spec-journey run`: run `livespec journey run`; compiled-only native execution, no recompilation.
- `$spec-journey list` / `$spec-journey inspect <journey-id>`: inspect global journey coverage and feature backlinks.

## Rules

- Works for implemented features; do not require `$spec-refine` just to add journey coverage.
- Journey IDs are global; feature ownership is inferred and stored as qualified `covers` refs.
- Always show inferred features, AC/FR refs, evidence, confidence, and ambiguity before writing.
- Compile once on create/edit through `livespec journey compile`; later `livespec journey run` executes native artifacts and does not compile.
- For XCUITest projects with `project.yml`/`project.yaml`, compile must run `xcodegen generate` so generated Swift journeys are included in the Xcode project.
- If `journey run` reports `journey_compiler_stale` after a LiveSpec migration, re-run `livespec journey compile` before retrying; old compiler manifests are intentionally blocked.
- Editing old journeys requires decision/changelog/run evidence before passing validation.
- Visible text selectors require `product_contract: true`; prefer semantic IDs, test IDs, i18n keys, roles, and accessibility labels.
