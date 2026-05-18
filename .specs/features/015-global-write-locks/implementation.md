---
type: implementation
title: Global Write Locks & Atomic NNN Reservation
feature: 015-global-write-locks
spec_ref: spec.md
plan_ref: plan.md
created: 2026-05-06
updated: 2026-05-06
---

# Implementation: Global Write Locks & Atomic NNN Reservation

> Reverse-engineered after-the-fact (PR #23 merged before `/spec.implement` was run on this feature). The mapping below was reconstructed by `/spec.fix` from `@spec FR-NNN` anchors discovered across the repository.

## Files Changed

| File | Action | Description |
|---|---|---|
| `validator/locks.py` | Created | 312 LOC — `acquire_lock`, `atomic_write`, `write_with_hash_check`, `reserve_nnn`, `release_reservation` |
| `system/locks.md` | Created | Reference doc (full primitives API + usage skeleton) |
| `commands/spec-specify.md` | Modified | Step 7.5/7.6 wrapped in `acquire_lock(specs_root)` block |
| `commands/spec-refine.md` | Modified | Lock acquisition around README/changelog updates |
| `commands/spec-fix.md` | Modified | Step 8 lock around all global writes |
| `agents/livespec-documenter.md` | Modified | Finalize mode (Steps 2–5) wrapped in lock |
| `tests/test_locks.py` | Created | 253 LOC — 6 test classes (AcquireLock, AcquireLockCrossProcess, AtomicWrite, WriteWithHashCheck, ReserveNnn, Composition) |

## Spec Anchor Mappings

| Source | Anchor | Location |
|---|---|---|
| @spec FR-001 | `spec.md#fr-001` | `validator/locks.py:246` — `reserve_nnn()` (mkdir + `.reserved` marker, EEXIST collision detection) |
| @spec FR-002 | `spec.md#fr-002` | `validator/locks.py:103` — `acquire_lock()` using `fcntl.flock` (POSIX) |
| @spec FR-003 | `spec.md#fr-003` | `validator/locks.py:201` — `write_with_hash_check()` post-write SHA256 assertion |
| @spec FR-004 | `spec.md#fr-004` | `validator/locks.py:156` — `atomic_write()` (temp file + `os.rename`) |
| @spec FR-005 | `spec.md#fr-005` | `commands/spec-specify.md:644` — Steps 7.5/7.6 lock acquire/release |
| @spec FR-006 | `spec.md#fr-006` | `commands/spec-refine.md:508` — README/changelog update lock |
| @spec FR-007 | `spec.md#fr-007` | `commands/spec-fix.md:249` — Step 8 lock around global writes |
| @spec FR-008 | `spec.md#fr-008` | `agents/livespec-documenter.md:59` — Finalize mode lock around Steps 2–5 |
| @spec FR-009 | `spec.md#fr-009` | `validator/locks.py:49` — 10-second timeout constant; 1 retry policy |
| @spec FR-010 | `spec.md#fr-010` | `validator/locks.py` — `acquire_lock` context manager + `release_reservation`; `tests/test_locks.py` covers acquire/release, timeout, stale lock recovery |

## AC Coverage

| AC | Status | Test |
|---|---|---|
| AC-001 | Covered | `tests/test_locks.py::TestReserveNnn` (mkdir reservation before spec.md generation) |
| AC-002 | Covered | `tests/test_locks.py::TestReserveNnn` (collision without `.reserved` marker → BLOCKED) |
| AC-003 | Covered | `tests/test_locks.py::TestReserveNnn` (idempotent resume when `.reserved` present) |
| AC-004 | Covered | `tests/test_locks.py::TestAcquireLockCrossProcess` (exclusive flock on `.specs/.LOCK`) |
| AC-005 | Covered | `tests/test_locks.py::TestAcquireLock` (10s timeout → BLOCKED) |
| AC-006 | Covered | `tests/test_locks.py::TestAtomicWrite` (temp + `os.rename`) |
| AC-007 | Covered | `tests/test_locks.py::TestWriteWithHashCheck` (post-write SHA256 mismatch → BLOCKED + rollback) |
| AC-008 | Covered | `commands/spec-specify.md:644` (Step 7.5/7.6 lock block); `tests/test_locks.py::TestComposition` |
| AC-009 | Covered | `commands/spec-refine.md:508`; `commands/spec-fix.md:249` |
| AC-010 | Covered | `agents/livespec-documenter.md:59`; `tests/test_locks.py::TestAcquireLockCrossProcess` (multi-process serialization) |
