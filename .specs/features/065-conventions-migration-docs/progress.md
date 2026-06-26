# Progress — Conventions Migration Docs

## Status

| Step | Status | Evidence |
|---|---|---|
| Specify feature behavior | Complete | `spec.md` defines AC-001..AC-014 and FR-001..FR-006 |
| Plan implementation approach | Complete | `plan.md` records migration and documentation strategy |
| Add RED tests for migration v22 and conventions enforcement docs | Complete | `tests/test_conventions_migration_docs.py` covers required artifacts |
| Implement migration v22 manifest and scripts | Complete | `migrations/22/migrate.md` and `scripts/migrate-conventions-*.sh` exist |
| Implement conventions enforcement reference doc | Complete | `system/conventions-enforcement.md` documents engines, schemas, operations, locks, and CLI |
| Update README, spec-system, CLAUDE/AGENTS guidance | Complete | Project docs surface conventions enforcement |
| Update implementation mapping | Complete | `implementation.md` maps FR and AC coverage |
| Run full verification | Complete | Changelog records implementation and bugfix verification |
| Cycle 2: move SET_VERSION after RUN steps, make wrappers advisory, and remove invalid verify flag | Complete | Migration v22 wrapper behavior updated |
