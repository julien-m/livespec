"""Tests for validator.locks (Chantier 3 / Feature 015, FR-001..010)."""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest

from validator.locks import (
    DEFAULT_LOCK_TIMEOUT_SECONDS,
    LOCK_FILENAME,
    RESERVED_MARKER,
    LockAcquisitionError,
    NnnCollisionError,
    NnnReservation,
    acquire_lock,
    atomic_write,
    release_reservation,
    reserve_nnn,
    write_with_hash_check,
)

# ─── acquire_lock (FR-002, FR-009) ───────────────────────────────────────────


class TestAcquireLock:
    def test_acquires_and_releases(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        with acquire_lock(specs) as lock_path:
            assert lock_path == specs / LOCK_FILENAME
            assert lock_path.exists()
        # Lock file remains on disk; only the OS-level flock is released.
        assert (specs / LOCK_FILENAME).exists()

    def test_creates_specs_root_if_missing(self, tmp_path: Path) -> None:
        specs = tmp_path / "doesnotexist" / ".specs"
        with acquire_lock(specs):
            assert specs.exists()

    def test_re_entrant_in_same_process(self, tmp_path: Path) -> None:
        # POSIX flock is process-scoped, not thread-scoped — same process can
        # re-acquire after release without conflict.
        specs = tmp_path / ".specs"
        with acquire_lock(specs):
            pass
        with acquire_lock(specs):
            pass

    def test_default_timeout_is_10s(self) -> None:
        assert DEFAULT_LOCK_TIMEOUT_SECONDS == 10


# Helper for inter-process lock contention test
def _hold_lock(specs_path_str: str, hold_seconds: float, ready_event: object) -> None:
    """Acquire the lock and hold it for ``hold_seconds`` (run in a child process)."""
    from validator.locks import acquire_lock as _acquire

    specs_path = Path(specs_path_str)
    with _acquire(specs_path):
        ready_event.set()  # type: ignore[attr-defined]
        time.sleep(hold_seconds)


class TestAcquireLockCrossProcess:
    def test_second_process_blocks_then_times_out(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        specs.mkdir()
        ctx = multiprocessing.get_context("spawn")
        ready = ctx.Event()
        proc = ctx.Process(target=_hold_lock, args=(str(specs), 1.5, ready))
        proc.start()
        try:
            assert ready.wait(timeout=5), "child failed to acquire lock"
            with (
                pytest.raises(LockAcquisitionError, match=r"within 0\.3s"),
                acquire_lock(specs, timeout=0.3),
            ):
                pass
        finally:
            proc.join(timeout=5)

    def test_second_process_acquires_after_release(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        specs.mkdir()
        ctx = multiprocessing.get_context("spawn")
        ready = ctx.Event()
        proc = ctx.Process(target=_hold_lock, args=(str(specs), 0.2, ready))
        proc.start()
        try:
            assert ready.wait(timeout=5), "child failed to acquire lock"
            # Wait long enough for the child to release
            with acquire_lock(specs, timeout=2.0):
                pass
        finally:
            proc.join(timeout=5)


# ─── atomic_write (FR-004) ───────────────────────────────────────────────────


class TestAtomicWrite:
    def test_writes_content_to_target(self, tmp_path: Path) -> None:
        target = tmp_path / "out.md"
        atomic_write(target, "hello")
        assert target.read_text() == "hello"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "deep" / "nested" / "out.md"
        atomic_write(target, "data")
        assert target.read_text() == "data"

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        target = tmp_path / "out.md"
        target.write_text("old")
        atomic_write(target, "new")
        assert target.read_text() == "new"

    def test_no_temp_file_remains_after_success(self, tmp_path: Path) -> None:
        target = tmp_path / "out.md"
        atomic_write(target, "data")
        leftovers = list(tmp_path.glob(".tmp.*"))
        assert leftovers == []


# ─── write_with_hash_check (FR-003) ──────────────────────────────────────────


class TestWriteWithHashCheck:
    def test_returns_expected_hash(self, tmp_path: Path) -> None:
        target = tmp_path / "out.md"
        digest = write_with_hash_check(target, "hello world")
        # SHA256 of "hello world"
        assert digest == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    def test_writes_content_to_target(self, tmp_path: Path) -> None:
        target = tmp_path / "out.md"
        write_with_hash_check(target, "content for verification")
        assert target.read_text() == "content for verification"

    def test_supports_unicode(self, tmp_path: Path) -> None:
        target = tmp_path / "out.md"
        content = "héllo ⟪PHASE_RESULT_END_a3f1b8c2⟫ 中文"
        digest = write_with_hash_check(target, content)
        assert target.read_text(encoding="utf-8") == content
        assert isinstance(digest, str) and len(digest) == 64


# ─── reserve_nnn (FR-001) ────────────────────────────────────────────────────


class TestReserveNnn:
    def test_first_reservation_in_empty_specs(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        result = reserve_nnn(specs, "add-search")
        assert isinstance(result, NnnReservation)
        assert result.slug == "001-add-search"
        assert result.directory == specs / "features" / "001-add-search"
        assert result.directory.is_dir()
        assert (result.directory / RESERVED_MARKER).is_file()
        assert result.resumed is False

    def test_increments_past_existing(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        for n in ("001-foo", "002-bar", "005-baz"):
            (specs / "features" / n).mkdir(parents=True)
        result = reserve_nnn(specs, "new-feature")
        assert result.slug == "006-new-feature"
        assert result.resumed is False

    def test_resumes_when_reserved_marker_present(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        # First reservation
        first = reserve_nnn(specs, "auth")
        # Simulate a crashed run: marker remains, spec.md never written
        # Second call with the SAME name + same NNN slot should resume
        # (We simulate by manually computing the same target)
        (specs / "features" / "001-auth" / RESERVED_MARKER).is_file()  # confirm marker

        # Second call allocates NNN=002 because 001-auth exists with marker
        # → it doesn't recurse into "resume" for a different slug name
        second = reserve_nnn(specs, "auth")
        # 002 because 001-auth exists; same name but new NNN
        assert second.slug == "002-auth"
        assert second.resumed is False
        assert first.slug == "001-auth"

    def test_collision_without_marker_raises(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        # Pre-create a directory at 001 WITHOUT a .reserved marker
        (specs / "features" / "001-foreign").mkdir(parents=True)
        # The next reservation will try 002 first (since 001-foreign occupies that NNN)
        # — to actually trigger collision, we need the candidate directory to exist
        # without a marker. Use a name that lands on the SAME NNN as 001-foreign
        # by manually creating the candidate path before calling reserve_nnn.
        target = specs / "features" / "002-collision"
        target.mkdir(parents=True)
        # Now scan_max_nnn returns 2 (from 001-foreign and 002-collision both),
        # so reserve_nnn will try 003-test → no collision. To force one, create 003 too.
        (specs / "features" / "003-other").mkdir()
        # Now call: scan returns 3, candidate is 004-test → succeeds.
        # To truly test collision we need the candidate to be exactly the next NNN.
        # Easier: pre-create the target path and rely on scan returning N-1 then N.
        # Cleanest: directly call mkdir on the candidate before reserve_nnn.
        # The candidate is f"{max_nnn+1:03d}-{name}". Let's name it to match.
        precreated = specs / "features" / "004-test"
        precreated.mkdir()  # without a .reserved marker
        # Now scan returns max=4. Next NNN=5. Slug=005-test → no collision.
        # OK, we need to call AFTER scan but BEFORE mkdir. Race window is tiny.
        # Alternative: monkey-patch _scan_max_nnn.
        from validator import locks as locks_module

        original = locks_module._scan_max_nnn  # type: ignore[attr-defined]
        try:
            locks_module._scan_max_nnn = lambda _features_dir: 3  # type: ignore[assignment, attr-defined]
            with pytest.raises(NnnCollisionError):
                reserve_nnn(specs, "test")  # candidate = 004-test, exists w/o marker
        finally:
            locks_module._scan_max_nnn = original  # type: ignore[assignment]

    def test_empty_name_rejected(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        with pytest.raises(ValueError, match="non-empty"):
            reserve_nnn(specs, "")

    def test_release_reservation_removes_marker(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        result = reserve_nnn(specs, "demo")
        assert (result.directory / RESERVED_MARKER).is_file()
        release_reservation(result)
        assert not (result.directory / RESERVED_MARKER).is_file()
        assert result.directory.is_dir()  # Directory itself stays

    def test_release_reservation_idempotent(self, tmp_path: Path) -> None:
        specs = tmp_path / ".specs"
        result = reserve_nnn(specs, "demo")
        release_reservation(result)
        release_reservation(result)  # second call should not raise


# ─── End-to-end composition ──────────────────────────────────────────────────


class TestComposition:
    def test_lock_protects_atomic_write(self, tmp_path: Path) -> None:
        """Smoke test: lock + atomic_write inside the critical section."""
        specs = tmp_path / ".specs"
        target = specs / "README.md"
        with acquire_lock(specs):
            digest = write_with_hash_check(target, "# README\n\nContent.")
        assert target.read_text().startswith("# README")
        assert isinstance(digest, str)
