---
created_at: '2026-05-07'
current_state: InProgress
feature_slug: '-'
owner_command: spec.ship
schema_version: 1
updated_at: '2026-05-07'
---

# Ship Session

**Started:** 2026-05-07
**Scope:** custom selection [014, 030, 031] — supervisor contracts + iOS/watchOS runner + Android runner
**Flags:** `--auto` (manual feature list), spawned agents per feature
**Base branch:** main
**Status:** In Progress

## Rationale

Previous batch ship/ui-runners-027-034 falsely marked 030 (iOS/watchOS) and 031 (Android) as Done — actual artefacts shipped were plan-only / pipeline-only stubs (no Swift/XCUITest code, no Maestro flows, no surfaces handler). This batch fixes that by:

1. **Feature 014 first** — Supervisor↔Subagent Return Contracts. Implementing this prevents future false-ship by enforcing typed `SHIP_RESULT` parsing + branch/slug validation gate before merge/roadmap-tick.
2. **Feature 030** — Real iOS/watchOS XCUITest runner with simctl orchestration + surfaces.yaml schema for `runner: xcuitest`.
3. **Feature 031** — Real Android Maestro runner with AVD orchestration + surfaces.yaml schema for `runner: maestro`.

| # | Feature                          | Status      | Branch                              | Started    | Completed |
|---|----------------------------------|-------------|-------------------------------------|------------|-----------|
| 1 | 014-supervisor-contracts         | Pending     | —                                   | —          | —         |
| 2 | 030-ui-runner-ios-watchos        | Pending     | —                                   | —          | —         |
| 3 | 031-ui-runner-android            | Pending     | —                                   | —          | —         |

## Notes

- Roadmap entries 030 and 031 were reset from `[x]` to `[ ]` before starting (ship-027-034 incorrectly marked them shipped).
- Old `ship.md` archived as `.specs/ship-027-034-archive.md` for history.
- 030 already has spec + plan (Plan: Done 2026-05-07). Agent should resume from Implement phase.
- 031 has only spec.md (no plan). Agent must run Plan phase first then Implement.
- 014 has only spec.md. Agent must run Plan + Implement.
