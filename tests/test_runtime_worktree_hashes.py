"""Worktree comparisons ignore Git churn without losing protected content checks."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tests.runtime_support import tree_hashes, write
from tests.test_runtime_docs import _working_tree_hashes


def test_worktree_hashes_never_read_excluded_git_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Git object disappearing during a read cannot break a worktree-only comparison."""
    volatile = write(tmp_path / ".git/objects/ab/volatile", "git internal")
    source = write(tmp_path / "source.py", "protected content")
    write(tmp_path / ".github/workflows/ci.yml", "protected workflow")
    write(tmp_path / "nested/.git/owned", "protected nested content")
    (tmp_path / "source-link").symlink_to("source.py")
    read_bytes = Path.read_bytes

    def read_with_git_churn(path: Path) -> bytes:
        if path == volatile:
            volatile.unlink()
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_with_git_churn)
    before = _working_tree_hashes(tmp_path)
    assert before == {
        "source.py": hashlib.sha256(b"protected content").hexdigest(),
        "source-link": "link:source.py",
        ".github/workflows/ci.yml": hashlib.sha256(b"protected workflow").hexdigest(),
        "nested/.git/owned": hashlib.sha256(b"protected nested content").hexdigest(),
    }
    assert volatile.exists()
    source.write_text("changed content")
    assert _working_tree_hashes(tmp_path) != before


def test_worktree_hashes_still_surface_missing_protected_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ignoring Git internals must not hide read failures for protected source files."""
    source = write(tmp_path / "source.py", "protected content")
    read_bytes = Path.read_bytes

    def read_missing_source(path: Path) -> bytes:
        if path == source:
            source.unlink()
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_missing_source)
    with pytest.raises(FileNotFoundError):
        _working_tree_hashes(tmp_path)


def test_default_tree_hashes_still_include_git_internals(tmp_path: Path) -> None:
    """Generic immutable-tree comparisons retain their original complete scope."""
    write(tmp_path / ".git/objects/ab/stable", "git internal")
    assert tree_hashes(tmp_path) == {
        ".git/objects/ab/stable": hashlib.sha256(b"git internal").hexdigest()
    }
