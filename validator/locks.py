# @spec(AC-013)

"""File locks, atomic writes, and atomic NNN reservation.

Spec anchors (Chantier 3 / Feature 015 — see
``.specs/features/015-global-write-locks/spec.md``):

- @spec FR-001: Atomic NNN reservation via ``mkdir`` + ``.reserved`` marker.
- @spec FR-002: ``.specs/.LOCK`` filelock mechanism (fcntl on POSIX).
- @spec FR-003: Post-write re-read + SHA256 hash assertion.
- @spec FR-004: Atomic write pattern (temp file + ``os.rename``).
- @spec FR-009: Deterministic timeout/retry policy (10s / 1 retry).
- @spec FR-010: ``acquire_lock`` context manager + helper API.

This module is the single Python implementation point for all write-side
safety properties on shared ``.specs/`` files. The four concerns are kept
together because they compose:

1. ``acquire_lock(specs_root, timeout=10)`` — exclusive flock on
   ``<specs_root>/.LOCK`` for the duration of a critical section.
2. ``atomic_write(target, content)`` — write to a same-directory temp file,
   ``fsync``, then ``os.rename`` to target (atomic on POSIX).
3. ``write_with_hash_check(target, content)`` — wraps ``atomic_write`` with
   a post-write re-read + SHA256 comparison; raises on mismatch.
4. ``reserve_nnn(specs_root, name)`` — atomic feature-directory reservation
   via ``mkdir`` (returns the reserved slug or raises on collision).

Note on spec deviation: spec FR-010 calls for ``system/lock.py``. This module
is placed in ``validator/`` instead, where all other Python code lives. The
import path is ``validator.locks``; ``system/`` remains documentation-only.
"""

from __future__ import annotations

import errno
import fcntl
import hashlib
import os
import random
import re
import secrets
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import IO

# ─── Defaults (FR-009) ───────────────────────────────────────────────────────

DEFAULT_LOCK_TIMEOUT_SECONDS = 10
"""@spec FR-009: 10-second lock timeout — spec.md#fr-009"""

DEFAULT_LOCK_RETRY_INTERVAL_SECONDS = 0.05
"""Sleep between flock attempts during the timeout window."""

# 45s ≈ 4-5 parallel /spec-ship finalizations serialized behind one lock
# (Feature 058 AC-009); named constant so tests and docs share one source.
FINALIZE_RETRY_TOTAL_BUDGET_SECONDS: float = 45.0
"""@spec FR-007: ~45s opt-in retry budget
— .specs/features/058-deterministic-finalization/spec.md#fr-007"""

LOCK_FILENAME = ".LOCK"
RESERVED_MARKER = ".reserved"
TEMPFILE_PREFIX = ".tmp."

# ─── Errors ──────────────────────────────────────────────────────────────────


class LockAcquisitionError(TimeoutError):
    """Raised when ``acquire_lock`` cannot acquire the flock within ``timeout``.

    The canonical halt line emitted by callers should follow the BLOCKED
    format from ``system/anti-drift-block.md`` §2 with subtype ``policy_blocked``.
    """


class WriteHashMismatchError(IOError):
    """Raised when post-write re-read produces a SHA256 different from the expected one.

    Indicates filesystem corruption, partial write, or a race outside the
    flock perimeter. Callers should rollback (or restore from backup) and
    halt.
    """


class NnnCollisionError(FileExistsError):
    """Raised when ``reserve_nnn`` finds a directory already exists at the target NNN.

    Distinct from "directory exists with .reserved marker" — that case
    triggers the idempotent-resume path, not this error.
    """


# ─── Opt-in retry policy (Feature 058 FR-007) ────────────────────────────────


@dataclass(frozen=True)
class LockRetryPolicy:
    """Opt-in exponential backoff + jitter policy for :func:`acquire_lock`.

    @spec FR-007: Opt-in retry mode on acquire_lock
    — .specs/features/058-deterministic-finalization/spec.md#fr-007

    Attributes:
        base_delay: First backoff delay in seconds.
        multiplier: Exponential growth factor applied after each attempt.
        jitter: Maximum random seconds added to each delay (de-synchronizes
            parallel ``/spec-ship`` pipelines).
        total_budget: Wall-clock budget before giving up (AC-009).
    """

    base_delay: float = 0.5
    multiplier: float = 2.0
    jitter: float = 0.25
    total_budget: float = FINALIZE_RETRY_TOTAL_BUDGET_SECONDS


# ─── Dataclass for reservation result ────────────────────────────────────────


@dataclass(frozen=True)
class NnnReservation:
    """Outcome of a successful or resumed NNN reservation."""

    slug: str
    directory: Path
    resumed: bool
    """True when an existing ``.reserved`` marker was detected and reused."""


# ─── flock-based lock (FR-002, FR-009) ───────────────────────────────────────


@contextmanager
def acquire_lock(
    specs_root: Path,
    timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    poll_interval: float = DEFAULT_LOCK_RETRY_INTERVAL_SECONDS,
    retry_policy: LockRetryPolicy | None = None,
    _sleep: Callable[[float], None] = time.sleep,
    _clock: Callable[[], float] = time.monotonic,
) -> Generator[Path, None, None]:
    """Acquire an exclusive flock on ``<specs_root>/.LOCK`` for the with-block duration.

    Args:
        specs_root: Root of ``.specs/`` (the lock file lives directly inside it).
        timeout: Maximum seconds to wait for the lock (default, non-retry path).
        poll_interval: Seconds to sleep between non-blocking acquisition attempts.
        retry_policy: Opt-in backoff+jitter retry (Feature 058 FR-007). When
            ``None`` (default), the existing single-window contract applies
            unchanged (AC-010).
        _sleep: Module-private injectable sleep used by the retry loop for
            deterministic tests. The default path always uses ``time.sleep``.
        _clock: Module-private injectable monotonic clock paired with
            ``_sleep`` for deterministic retry-budget tests.

    Yields:
        The path to the lock file (mostly informational; the caller does not
        need to interact with it).

    Raises:
        LockAcquisitionError: Lock could not be acquired within ``timeout``
            (default path) or within ``retry_policy.total_budget`` (retry path).

    Example:
        >>> with acquire_lock(Path(".specs")):
        ...     # README.md / changelog.md / roadmap.md writes are safe here
        ...     pass
    """
    if not specs_root.exists():
        specs_root.mkdir(parents=True, exist_ok=True)
    lock_path = specs_root / LOCK_FILENAME
    deadline = time.monotonic() + timeout

    fd: IO[bytes] = lock_path.open("a+b")
    try:
        if retry_policy is None:
            # AC-010: this branch is the pre-existing single-window contract —
            # do not alter it when extending the retry path.
            while True:
                try:
                    fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise LockAcquisitionError(
                            f"could not acquire {lock_path} within {timeout}s"
                        ) from None
                    time.sleep(poll_interval)
        else:
            _acquire_with_retry(fd, lock_path, retry_policy, _sleep, _clock)
        try:
            yield lock_path
        finally:
            with suppress(OSError):
                fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
    finally:
        fd.close()


def _acquire_with_retry(
    fd: IO[bytes],
    lock_path: Path,
    policy: LockRetryPolicy,
    sleep_fn: Callable[[float], None],
    clock_fn: Callable[[], float],
) -> None:
    """Retry non-blocking flock attempts with exponential backoff + jitter.

    @spec FR-007: backoff+jitter retry within ~45s budget
    — .specs/features/058-deterministic-finalization/spec.md#fr-007
    """
    retry_deadline = clock_fn() + policy.total_budget
    delay = policy.base_delay
    while True:
        try:
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            now = clock_fn()
            if now >= retry_deadline:
                raise LockAcquisitionError(
                    f"could not acquire {lock_path} within {policy.total_budget}s retry budget"
                ) from None
            # Jitter de-synchronizes parallel /spec-ship finalizers; the sleep
            # is capped at the remaining budget so total wait stays ~45s ±jitter.
            remaining = retry_deadline - now
            sleep_fn(min(delay + random.uniform(0.0, policy.jitter), remaining))
            delay *= policy.multiplier


# ─── Atomic write (FR-004) ───────────────────────────────────────────────────


def atomic_write(target: Path, content: str, encoding: str = "utf-8") -> None:
    """Write ``content`` to ``target`` atomically.

    Implementation: write to a same-directory temp file with a unique suffix,
    ``fsync``, then ``os.rename`` to the target. ``os.rename`` is atomic on
    POSIX filesystems (and on Windows when both paths are on the same volume,
    starting with Python 3.3+).

    The temp file is named ``.tmp.<basename>.<8-hex>`` to keep it on the
    same filesystem as the target (rename across filesystems is not atomic).

    Args:
        target: Destination path; parent directory must exist.
        content: Text to write.
        encoding: Encoding used for both write and re-read paths.

    Raises:
        OSError: If the temp file cannot be created or the rename fails.
            On error the temp file is best-effort unlinked.
    """
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    suffix = secrets.token_hex(4)
    tmp_path = parent / f"{TEMPFILE_PREFIX}{target.name}.{suffix}"

    try:
        with tmp_path.open("w", encoding=encoding) as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, target)
    except OSError:
        # Best-effort cleanup of the temp file
        with suppress(OSError):
            tmp_path.unlink()
        raise


# ─── Hash-verified write (FR-003) ────────────────────────────────────────────


def _sha256_text(text: str, encoding: str = "utf-8") -> str:
    return hashlib.sha256(text.encode(encoding)).hexdigest()


def write_with_hash_check(target: Path, content: str, encoding: str = "utf-8") -> str:
    """Atomically write ``content`` to ``target`` and verify the on-disk SHA256.

    Returns:
        The expected SHA256 hex digest of ``content``. Useful for callers
        that want to log or persist the verification value.

    Raises:
        WriteHashMismatchError: If re-reading ``target`` produces a hash
            different from ``_sha256_text(content)``.
        OSError: If the underlying ``atomic_write`` fails.
    """
    expected = _sha256_text(content, encoding=encoding)
    atomic_write(target, content, encoding=encoding)
    on_disk = target.read_text(encoding=encoding)
    actual = _sha256_text(on_disk, encoding=encoding)
    if actual != expected:
        raise WriteHashMismatchError(
            f"post-write hash mismatch for {target}: "
            f"expected={expected[:16]}... actual={actual[:16]}..."
        )
    return expected


# ─── NNN reservation (FR-001) ────────────────────────────────────────────────

# Match the leading 3-digit NNN; the optional .M sub-feature suffix (e.g. 005.1)
# is intentionally not captured because sub-features share their parent's NNN
# slot when computing the next top-level reservation.
_NNN_REGEX = re.compile(r"^(\d{3})")


def _scan_max_nnn(features_dir: Path) -> int:
    if not features_dir.is_dir():
        return 0
    max_n = 0
    for entry in features_dir.iterdir():
        if not entry.is_dir():
            continue
        match = _NNN_REGEX.match(entry.name)
        if match:
            max_n = max(max_n, int(match.group(1)))
    return max_n


def reserve_nnn(specs_root: Path, name: str) -> NnnReservation:
    """Atomically reserve the next NNN-slug feature directory for ``name``.

    The slug ``name`` is taken as-is (caller is responsible for slugification —
    typically via :func:`validator.identity.resolve_feature_slug`).

    Reservation algorithm:

    1. Scan ``specs_root/features/`` for the highest existing NNN.
    2. Compose the candidate slug ``f"{nnn+1:03d}-{name}"`` and the candidate path.
    3. Attempt ``mkdir(candidate_path)``.
    4. If ``mkdir`` succeeds → write a ``.reserved`` marker, return the new reservation.
    5. If ``mkdir`` fails with ``EEXIST``:
       - If the existing directory contains a ``.reserved`` marker → idempotent
         resume path: return the existing slug with ``resumed=True``.
       - Otherwise → raise :class:`NnnCollisionError` (the directory was
         created by something else and has no reservation marker).

    Args:
        specs_root: Root of ``.specs/``.
        name: kebab-case slug name (without the NNN- prefix).

    Returns:
        :class:`NnnReservation` carrying the resolved slug, the directory path,
        and a ``resumed`` flag indicating whether an existing reservation was
        reused.

    Raises:
        NnnCollisionError: Target NNN directory exists without a ``.reserved``
            marker (likely a manual creation or a foreign tool).
        OSError: Other filesystem errors.
    """
    if not name:
        raise ValueError("name must be a non-empty kebab-case slug")

    features_dir = specs_root / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    nnn = _scan_max_nnn(features_dir) + 1
    slug = f"{nnn:03d}-{name}"
    target = features_dir / slug
    marker = target / RESERVED_MARKER

    try:
        target.mkdir(parents=False, exist_ok=False)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
        if marker.is_file():
            return NnnReservation(slug=slug, directory=target, resumed=True)
        raise NnnCollisionError(
            f"directory {target} already exists with no .reserved marker"
        ) from exc

    marker.write_text(f"NNN={nnn:03d}\n", encoding="utf-8")
    return NnnReservation(slug=slug, directory=target, resumed=False)


def release_reservation(reservation: NnnReservation) -> None:
    """Remove the ``.reserved`` marker from a successful reservation.

    Call this once the feature is fully specified (spec.md committed). The
    marker is a fail-safe for crash recovery; once spec.md exists, the
    marker is no longer needed and removing it cleans up the audit trail.
    """
    marker = reservation.directory / RESERVED_MARKER
    if marker.is_file():
        marker.unlink()
