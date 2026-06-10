# Pipeline — 058-deterministic-finalization

**Started:** 2026-06-10 10:06
**Flags:** none
**Feature Description:** Deterministic finalization CLI: new livespec finalize apply command writes all end-of-command registry updates (feature changelog entry, global .specs/changelog.md entry, README feature row + Recent Activity, status frontmatter) atomically and idempotently under locks.acquire_lock with write_with_hash_check, using marker finalize:<cmd>:<date>:<hash8> for idempotence; companion livespec finalize verify (read-only) re-checks registry coherence by reusing coherence rules r1/r4/r6 scoped to the feature and emits a JSON receipt (sha256 of touched files, same shape as the visual receipt); new goal evidence family finalize.registry in goal_contracts.py requiring finalize_receipt_path validated by verify_finalize_receipt() (clone of verify_visual_receipt pattern) so DONE is structurally impossible without real finalization; plus opt-in retry with backoff+jitter on locks.acquire_lock (~45s total) for parallel /spec-ship safety. Implemented as validator/finalize.py + validator/cli_commands/finalize_cmd.py following the existing typer registration pattern.

| Phase | Status | Completed At |
|-------|--------|--------------|
| Specify | Done | 2026-06-10 10:22 |
| Spec Review | Done | 2026-06-10 10:27 |
| Plan | Done | 2026-06-10 10:44 |
| Plan Review | Done | 2026-06-10 10:44 |
| Preflight | Done | 2026-06-10 10:49 |
| Implement | Done | 2026-06-10 11:38 |
| Test | Done | 2026-06-10 11:52 |
