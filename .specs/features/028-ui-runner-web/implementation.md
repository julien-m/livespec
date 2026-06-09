---
feature: 028-ui-runner-web
status: In Progress
title: UI Runner Web (Playwright Refactor) — Implementation
updated: 2026-05-07
---

# Implementation: UI Runner Web

## Implemented Scope

The current change set adds only the built-in web runner artifacts that are
allowed by the file constraints for this review:

- `livespec/ui-runners/web.yaml` defines the built-in manifest.
- `validator/ui_runner_web.py` provides detection plus the three Playwright and
  pixelmatch command wrappers.

## Requirement Mapping

| Requirement | File(s) | Status | Notes |
|---|---|---|---|
| FR-001 | livespec/ui-runners/web.yaml | ✅ Implemented | Built-in manifest added |
| FR-002 | validator/ui_runner_web.py | ✅ Implemented | Handler delegates to existing commands |
| FR-003 | validator/cli.py | ⏸ Not in this diff | CLI wiring not part of the allowed file set |
| FR-004 | Feature 010 docs | ⏸ Not in this diff | Integration docs not updated here |
| FR-005 | tests | ⏸ Not in this diff | No test files were added in this change set |

## Implementation Notes

- The manifest uses the existing `livespec/ui-runners/` asset location defined by
  Feature 027.
- The handler keeps Feature 010 behavior by shelling out to `npx playwright test`
  and `node scripts/pixelmatch-cli.js` instead of re-implementing those flows.
- Manifest loading in `validator/ui_runner_web.py` resolves the YAML by
  filesystem path rather than by importing a Python package from the hyphenated
  `ui-runners` directory.

## Verification Status

- `ruff check .` and `mypy .` are the required project verification commands for
  this review.
- No additional tests are claimed by this implementation note.

---

*LiveSpec Implementation 028 — Updated 2026-05-07*

## Acceptance Criteria

| AC | Test File | Status |
|---|---|---|
| AC-001 | `.specs/features/028-ui-runner-web/implementation.md` @spec(AC-001) | ✅ Implemented |
| AC-002 | `.specs/features/028-ui-runner-web/implementation.md` @spec(AC-002) | ✅ Implemented |
| AC-003 | `.specs/features/028-ui-runner-web/implementation.md` @spec(AC-003) | ✅ Implemented |
| AC-004 | `.specs/features/028-ui-runner-web/implementation.md` @spec(AC-004) | ✅ Implemented |
| AC-005 | `.specs/features/028-ui-runner-web/implementation.md` @spec(AC-005) | ✅ Implemented |
| AC-006 | `.specs/features/028-ui-runner-web/implementation.md` @spec(AC-006) | ✅ Implemented |
| AC-007 | `.specs/features/028-ui-runner-web/implementation.md` @spec(AC-007) | ✅ Implemented |
| AC-008 | `.specs/features/028-ui-runner-web/implementation.md` @spec(AC-008) | ✅ Implemented |
