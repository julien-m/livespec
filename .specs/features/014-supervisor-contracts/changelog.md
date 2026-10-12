## 2026-06-08 — [Spec Update]: Normalize changelog format

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec.doctor

---

# Changelog — Feature 014: Supervisor↔Subagent Return Contracts

### 2026-05-06 — Fix: implementation.md created (post-merge bookkeeping)

- **Type:** Bug Fix
- **Spec modified:** No
- **Code modified:** None — only `implementation.md` produced from existing `@spec` anchors
- **Gaps closed:** Missing FR→file mapping document. Code shipped via PR #22 without running `/spec.implement`.
- **Remaining:** None
- **Author:** spec.fix

### 2026-05-03 — Spec: Feature specification created

- **Type:** Spec Update
- **Spec modified:** Yes (created — all sections)
- **Code modified:** None
- **AC impacted:** AC-001 through AC-010 (all defined)
- **Author:** /spec.specify --auto (Chantier 2 from AUDIT.md)

## 2026-10-12 — [Refactor]: Constant, pydantic-only and duplicate round-trip tests removed

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_contracts.py, implementation.md
- **AC impacted:** None (AC-005 stays covered by TestSuperpowersReturnParser)
- **Author:** Claude Code (test-suite cleanup, lot 1)
- Removed the `ANCHOR_WINDOW_LINES == 30` constant check (behavior kept by the 30-line window test), two direct pydantic model checks duplicated through the parser, a duplicate unknown-key test and two round-trips superseded by the run_artifact round-trips.
