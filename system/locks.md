# Global Write Locks & Atomic Writes

> File-system safety primitives for shared `.specs/` files.
> Implementation: [`validator/locks.py`](../validator/locks.py).
>
> **@spec FR-001..010 (Chantier 3 / Feature 015):** [`.specs/features/015-global-write-locks/spec.md`](../.specs/features/015-global-write-locks/spec.md)

---

## What this exists for

Three classes of bug pre-Chantier 3:

1. **Lost updates on global files.** Two features running in parallel both
   appended a row to `.specs/changelog.md`; the second writer overwrote the
   first because there was no coordination.
2. **Partial writes.** A crash mid-write left `.specs/README.md` truncated
   or with mixed-version content; downstream commands then read garbage.
3. **NNN collisions.** Two concurrent `/spec-specify` invocations both
   computed the same next NNN, then both ran `mkdir`. Whichever ran second
   silently overwrote the first reservation.

This module provides the four primitives that fix all three.

## API

### `acquire_lock(specs_root, timeout=10)` — exclusive flock

Context manager that acquires a POSIX `fcntl.flock` on `<specs_root>/.LOCK`
for the duration of the with-block.

```python
from pathlib import Path
from validator.locks import acquire_lock

with acquire_lock(Path(".specs")):
    # All writes to .specs/changelog.md, README.md, roadmap.md go here.
    ...
```

- **Process-scoped** (POSIX flock semantics): two processes can't both hold it.
- **Timeout** defaults to 10s; raises `LockAcquisitionError` on expiry.
- **Lock file** (`.LOCK`) is gitignored — only the OS-level flock matters,
  not the file's content.

### `atomic_write(target, content)` — temp file + rename

Write `content` to `target` via a same-directory temp file, `fsync`, then
`os.replace`. Atomic on POSIX (and Windows when both paths are on the
same volume). On error, the temp file is best-effort unlinked and the
target is left untouched.

### `write_with_hash_check(target, content)` — atomic + verified

Wraps `atomic_write` with a post-write re-read + SHA256 comparison.
Raises `WriteHashMismatchError` if the on-disk content's hash differs
from the expected one. This catches:

- Filesystem-level corruption (rare but real).
- Accidental concurrent modification by code outside the lock perimeter.
- Race conditions between flock release and the next reader.

Returns the expected SHA256 hex digest for callers that want to log it.

### `reserve_nnn(specs_root, name)` — atomic feature-dir reservation

Replaces the racy "scan + increment + mkdir" pattern with an atomic
reservation:

```python
from validator.locks import reserve_nnn, release_reservation

reservation = reserve_nnn(Path(".specs"), "add-search")
print(reservation.slug)  # → "001-add-search" (or next free NNN)
print(reservation.directory.is_dir())  # True
print((reservation.directory / ".reserved").is_file())  # True

# ... write spec.md, plan.md, etc ...

release_reservation(reservation)  # Removes .reserved marker after success
```

Crash recovery: if a previous run created the directory + marker but
crashed before completing, calling `reserve_nnn` again with the same name
DOES NOT recover the same NNN (it allocates a new one). True
crash-recovery for the same NNN requires a higher-level helper that knows
the slug from the user's intent — this is left for a future iteration.

The collision case (existing directory without marker) raises
`NnnCollisionError` — caller should surface as `BLOCKED`.

## Failure protocol

| Helper | Failure | Canonical line emitted by caller |
|--------|---------|----------------------------------|
| `acquire_lock` | timeout | `BLOCKED at step <N> - policy_blocked - .specs/.LOCK timeout (10s)` |
| `write_with_hash_check` | hash mismatch | `BLOCKED at step <N> - state_invalid - hash mismatch on <path>` |
| `reserve_nnn` | collision (no marker) | `BLOCKED at step <N> - state_invalid - NNN collision on <slug>` |

See [`system/anti-drift-block.md`](anti-drift-block.md) §2 for the canonical BLOCKED format.

## Where this is used

- `.agent-sync/skills/spec-specify/SKILL.md` Steps 7.5/7.6 — README + changelog updates
- `.agent-sync/skills/spec-refine/SKILL.md` — README + feature changelog updates
- `.agent-sync/skills/spec-fix/SKILL.md` Step 8 — artifacts updates
- `.agent-sync/agents/livespec-documenter/prompt.md` Finalize mode — writes to README + changelog + roadmap

All of these wrap their write sequence in `with acquire_lock(specs_root):`
and use `write_with_hash_check` for the actual write.

## Performance note

Lock contention is rare in practice (a typical `/spec-specify` run holds
the lock for milliseconds). The 10-second timeout is a safety net for
runaway holders, not an expected wait time. If contention becomes a
problem, the per-operation lock granularity can be replaced with
per-file locks (one `.specs/changelog.md.lock`, one `.specs/README.md.lock`,
etc.) — but the current single-lock design is simpler and sufficient for
the project's scale.
