---
created_at: '2026-05-07'
current_state: Done
feature_slug: 025-mutation-testing-on-demand
owner_command: spec-feature
schema_version: 1
updated_at: '2026-05-07'
---

# Pipeline — 025-mutation-testing-on-demand

**Started:** 2026-05-07 04:33
**Flags:** `--auto --branch`
**Feature Description:** Mutation testing exposed as on-demand audit (livespec spec.test --mutation). Invokes mutation capability from the active driver, parses results, lists surviving mutants with file:line, and saves a historical report to .specs/testing/mutation-report.md. NOT in per-PR CI. Builds on 017 (mutmut), 018 (Stryker), 021 (cargo-mutants), 022 (pitest).

| Phase | Status | Completed At |
|-------|--------|--------------|
| Specify | Done | 2026-05-07 04:34 |
| Spec Review | Done | 2026-05-07 04:34 |
| Plan | Done | 2026-05-07 04:35 |
| Plan Review | Done | 2026-05-07 04:35 |
| Preflight | Done | 2026-05-07 04:35 |
| Implement | Done | 2026-05-07 04:41 |
| Test | Done | 2026-05-07 04:41 |
