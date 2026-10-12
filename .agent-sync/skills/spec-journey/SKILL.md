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
<!-- @spec(FR-037) -->
<!-- @spec(FR-038) -->
<!-- @spec(FR-039) -->


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
- `$spec-journey visual`: after `journey run`, evaluate every compiled LLM visual contract yourself (see below), then run `livespec journey visual-verify [--journey <id>] --json`; it exits 1 while any receipt is missing, invalid, stale, disabled or a blocking check failed.

## LLM visual contracts

`livespec journey compile` writes one contract per `llm` / `native_then_llm` check to `.specs/journeys/<id>/compiled/visual-contracts/<check>.json`. You are the evaluator; the CLI never calls a model.

1. Run `livespec journey visual-verify --json` to list contracts and their expected `receipt_path`.
2. Skip evaluation when the contract has `privacy.llm_allowed: false`. When `privacy.local_only: true`, evaluate only with a local model and record `"locality": "local"`; otherwise do not evaluate and report BLOCKED.
3. Use the screenshot produced by the native run for the contract target; if the run did not keep one, capture that screen with the project runner and save it inside the project (for example `.specs/journeys/<id>/runs/visual/<check>.png`). Ignore regions listed in `privacy.masking`.
4. Examine only the screenshot against `instructions` and `assertion`; never navigate or operate the UI to decide.
5. Write the receipt as strict JSON with exactly these keys: `schema_version` (1), `journey_id`, `check_id`, `contract_sha256` (SHA-256 of the contract file), `capture_path` (project-relative), `capture_sha256`, `verdict` (`pass`/`fail`), `confidence` (0–1), `criteria_passed`, `criteria_failed` (non-empty iff `fail`), `explanation` (≤ 500 chars), `bounding_boxes` (`x`, `y`, `width`, `height`, optional `label`; when possible), `evaluator` (`name`, `locality`), `evaluated_at` (ISO-8601).
6. With `privacy.retention: none` delete the capture after writing the receipt; otherwise keep it so its hash can be re-verified.
7. Re-run `livespec journey visual-verify`. A failed non-blocking check is advisory (`ADVISORY_FAIL`); a failed `blocking: true` check fails the command.

## Rules

- Works for implemented features; do not require `$spec-refine` just to add journey coverage.
- Journey IDs are global; feature ownership is inferred and stored as qualified `covers` refs.
- Always show inferred features, AC/FR refs, evidence, confidence, and ambiguity before writing.
- Compile once on create/edit through `livespec journey compile`; later `livespec journey run` executes native artifacts and does not compile.
- For XCUITest projects with `project.yml`/`project.yaml`, compile must run `xcodegen generate` so generated Swift journeys are included in the Xcode project.
- If `journey run` reports `journey_compiler_stale` after a LiveSpec migration, re-run `livespec journey compile` before retrying; old compiler manifests are intentionally blocked.
- Editing old journeys requires decision/changelog/run evidence before passing validation.
- Visible text selectors require `product_contract: true`; prefer semantic IDs, test IDs, i18n keys, roles, and accessibility labels.
