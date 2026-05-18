---
created_at: '2026-05-07'
current_state: Done
feature_slug: 032-test-hooks-pre-commit-pre-push
owner_command: spec-feature
schema_version: 1
updated_at: '2026-05-07'
---

# Pipeline — 032-test-hooks-pre-commit-pre-push

**Started:** 2026-05-07 10:52
**Flags:** `--auto --branch`
**Feature Description:** Extend the existing `livespec install-hook` command (currently installs a pre-commit hook running validate Layer 1+2) to also support pre-push hooks that orchestrate driver capabilities (016-026) and UI runners (027-031). Local-first alternative to GitHub Actions: pre-commit runs fast checks (validate + smart-selected unit tests), pre-push runs the full test suite (coverage + snapshots + visual). Configurable per project via .specs/hooks-config.yaml.

| Phase | Status | Completed At |
|-------|--------|--------------|
| Specify | Done | 2026-05-07 10:53 |
| Spec Review | Pending | — |
| Plan | Done | 2026-05-07 10:55 |
| Plan Review | Pending | — |
| Preflight | Done | 2026-05-07 10:55 |
| Implement | Done | 2026-05-07 10:55 |
| Test | Done | 2026-05-07 10:56 |
